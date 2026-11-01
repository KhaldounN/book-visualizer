"""Link pronouns and descriptions ("she", "her sister") to characters.

fastcoref groups words that refer to the same thing ("Elizabeth ... she ...
her"). We run it on chunks of the book; when a group contains names of a
character found in step 2, every other word in that group becomes a mention
of that character too.
"""

import logging
from bisect import bisect_right
from collections import Counter
from typing import Callable

import spacy

from .models import Character, Mention, Sentence

CHUNK_WORDS = 1500  # how much story the model resolves at once
CONTEXT_WORDS = 250  # extra text before each chunk, read but not recorded
MIN_SHARE = 0.6  # a group belongs to a character only if this share of its names agree

# Words never linked to a single character:
# - "I", "you" and forms of address change meaning with every speaker in
#   dialogue, and the model often gets them wrong
# - plural and "it" words refer to groups or things
SKIP_WORDS = {
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself",
    "yourselves", "we", "us", "our", "ours", "ourselves",
    "sir", "madam", "ma'am", "my dear", "my love", "my dear sir", "my dear madam",
    "they", "them", "their", "theirs", "themselves", "it", "its", "itself",
}
MALE = {"he", "him", "his", "himself"}
FEMALE = {"she", "her", "hers", "herself"}
MALE_TITLES = {"Mr.", "Sir", "Lord", "Colonel", "Captain", "Uncle", "Rev."}
FEMALE_TITLES = {"Mrs.", "Miss", "Ms.", "Lady", "Aunt"}

ProgressCallback = Callable[[int, int], None]  # (done, total)


def load_model():
    import datasets
    from fastcoref import FCoref

    # fastcoref logs every download and batch; keep the console readable
    for name in ("fastcoref", "transformers", "datasets", "httpx"):
        logging.getLogger(name).setLevel(logging.WARNING)
    datasets.disable_progress_bars()
    # fastcoref only needs spaCy to split words, so a blank English tokenizer
    # is enough and saves loading a second full spaCy model
    return FCoref(device="cpu", nlp=spacy.blank("en"), enable_progress_bar=False)


def _words(sentence: Sentence) -> int:
    return len(sentence.text.split())


def _chunks(sentences: list[Sentence]) -> list[tuple[int, int, int]]:
    """Split the book into (context_start, own_start, own_end) sentence index
    ranges. Chunks never cross chapters, and context never comes from the
    previous chapter."""
    chunks = []
    start = 0
    while start < len(sentences):
        end, words = start, 0
        chapter = sentences[start].chapter
        while end < len(sentences) and sentences[end].chapter == chapter and words < CHUNK_WORDS:
            words += _words(sentences[end])
            end += 1
        context, words = start, 0
        while context > 0 and sentences[context - 1].chapter == chapter and words < CONTEXT_WORDS:
            context -= 1
            words += _words(sentences[context])
        chunks.append((context, start, end))
        start = end
    return chunks


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def resolve(
    text: str,
    sentences: list[Sentence],
    characters: list[Character],
    name_mentions: list[Mention],
    model,
    progress: ProgressCallback | None = None,
) -> list[Mention]:
    """Return new mentions ("she", "her", "the young lady") of known characters."""
    chunks = _chunks(sentences)
    sentence_starts = [s.start for s in sentences]
    names = sorted(name_mentions, key=lambda m: m.start)
    name_starts = [m.start for m in names]

    def names_in(span: tuple[int, int]) -> list[Mention]:
        """Names that the span is about. "Mr. Darcy's sister" contains Darcy's
        name but is about his sister, so a possessive name inside a longer
        span does not count."""
        i = bisect_right(name_starts, span[1])  # spans are short, so look nearby
        return [
            m for m in names[max(0, i - 5):i]
            if _overlaps(span, (m.start, m.end))
            and not (text.startswith("'", m.end) and span[1] > m.end + 2)
        ]

    found: list[Mention] = []
    for done, (context, own_start, own_end) in enumerate(chunks, start=1):
        offset = sentences[context].start
        chunk_text = text[offset:sentences[own_end - 1].end]
        own_from = sentences[own_start].start
        result = model.predict(texts=[chunk_text])[0]

        for cluster in result.get_clusters(as_strings=False):
            spans = [(offset + s, offset + e) for s, e in cluster]
            votes = Counter(m.character_id for span in spans for m in names_in(span))
            if not votes:
                continue  # a group about something else ("the letter ... it")
            character_id, count = votes.most_common(1)[0]
            if count < MIN_SHARE * sum(votes.values()):
                continue  # names of different characters got mixed together

            for span in spans:
                if span[0] < own_from or names_in(span):
                    continue  # in the context part, or already counted as a name
                if text[span[0]:span[1]].lower() in SKIP_WORDS:
                    continue
                found.append(
                    Mention(
                        character_id=character_id,
                        sentence_index=bisect_right(sentence_starts, span[0]) - 1,
                        start=span[0],
                        end=span[1],
                        text=text[span[0]:span[1]],
                        source="coref",
                    )
                )
        if progress:
            progress(done, len(chunks))
    return _drop_wrong_gender(found, characters)


def _title_gender(character: Character) -> set[str] | None:
    """The pronouns that can NOT refer to this character, judged by the titles
    in their names ("Miss Lizzy" -> not "he"). None if the titles don't say."""
    titles = {alias.split()[0] for alias in character.aliases}
    if titles & MALE_TITLES and not titles & FEMALE_TITLES:
        return FEMALE
    if titles & FEMALE_TITLES and not titles & MALE_TITLES:
        return MALE
    return None


def _drop_wrong_gender(mentions: list[Mention], characters: list[Character]) -> list[Mention]:
    """Drop pronouns of the wrong gender (model mistakes). Gender comes from
    the character's titles, or else from all their pronouns in the book."""
    male, female = Counter(), Counter()
    for m in mentions:
        word = m.text.lower()
        male[m.character_id] += word in MALE
        female[m.character_id] += word in FEMALE
    wrong = {}
    for c in characters:
        wrong[c.id] = _title_gender(c)
        # otherwise only decide when the pronouns clearly agree (3 to 1)
        if wrong[c.id] is None and male[c.id] + female[c.id] > 0:
            if male[c.id] >= 3 * female[c.id]:
                wrong[c.id] = FEMALE
            elif female[c.id] >= 3 * male[c.id]:
                wrong[c.id] = MALE
    return [m for m in mentions if m.text.lower() not in (wrong.get(m.character_id) or ())]
