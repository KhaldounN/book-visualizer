"""Split clean book text into chapters and sentences with spaCy."""

import re
from bisect import bisect_right
from typing import Callable

from spacy.language import Language

from .loaders import CHAPTER_HEADING
from .models import Chapter, Entity, Sentence

# Used when a book has no "Chapter ..." headings
FALLBACK_PARTS = 50
# Word types counted per sentence (spaCy's universal part-of-speech tags), for analyzer/pace.py
WORD_TYPES = ("VERB", "ADJ", "ADV", "NOUN")


def word_types(tokens) -> dict[str, int]:
    """How many verbs, adjectives, adverbs and nouns a run of spaCy tokens holds."""
    counts = dict.fromkeys(WORD_TYPES, 0)
    for token in tokens:
        if token.pos_ in counts:
            counts[token.pos_] += 1
    return counts

ProgressCallback = Callable[[int, int], None]  # (done, total)


# When a book has no "Chapter ..." headings, these are tried in turn (the first that looks like
# a real run of chapters wins): "STAVE I: MARLEY'S GHOST" (A Christmas Carol), a Roman numeral
# with an optional title ("I. THE RIVER BANK", "I The Old Sea-dog", a bare "IV"), and a plain
# number with an optional title ("1", "01 My Early Home"). A title must start with a capital
# and not end like dialogue, so a line such as "I took a step nearer." is never a heading.
_TITLE = r"""(?:[ \t]*[.:\u2014-]?[ \t]+[A-Z][^\n]{0,100}?)?[ \t]*\.?(?<![?!"'])"""
FALLBACK_HEADINGS = [
    re.compile(r"^[ \t]*stave[ \t]+(?P<n>[IVXLC]+|\d+|[a-z]+)\b[^\n]{0,100}$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^[ \t]*(?P<n>[IVXLC]{1,7})\.?" + _TITLE + "$", re.MULTILINE),
    re.compile(r"^[ \t]*(?P<n>\d{1,3})\.?" + _TITLE + "$", re.MULTILINE),
]
MIN_CHAPTER_WORDS = 40  # a "chapter" shorter than this is a contents-page entry, not a chapter
_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def _number(text: str) -> int | None:
    """The value of a heading's number: "12" -> 12, "XIV" -> 14 (None for words like "one")."""
    if text.isdigit():
        return int(text)
    if not all(c in _ROMAN for c in text.upper()):
        return None
    values = [_ROMAN[c] for c in text.upper()]
    return sum(-v if i + 1 < len(values) and v < values[i + 1] else v for i, v in enumerate(values))


def _counts_up(matches: list[re.Match]) -> bool:
    """True when most headings are numbered one more than the one before (1, 2, 3...; a new
    part may start again at 1). Real chapters do that; stray lines that happen to match don't."""
    numbers = [_number(m.group("n")) for m in matches]
    if None in numbers:
        return True  # number words ("STAVE ONE"): the keyword is proof enough
    steps = list(zip(numbers, numbers[1:]))
    return bool(steps) and sum(b == a + 1 or b == 1 for a, b in steps) >= 0.8 * len(steps)


def _drop_contents(text: str, matches: list[re.Match]) -> list[re.Match]:
    """Leave out headings with almost no text before the next one: a contents page's entries."""
    kept = []
    for m, nxt in zip(matches, matches[1:] + [None]):
        body = text[m.end():nxt.start() if nxt else len(text)]
        if len(body.split()) >= MIN_CHAPTER_WORDS:
            kept.append(m)
    return kept


def _heading_number(m: re.Match) -> int | None:
    """The number in a heading: "CHAPTER XLII." -> 42, "IV. THE CYLINDER" -> 4."""
    if "n" in m.re.groupindex:
        return _number(m.group("n"))
    words = m.group(0).split()
    return _number(words[1].rstrip(".:")) if len(words) > 1 else None


def _drop_contents_tail(matches: list[re.Match]) -> list[re.Match]:
    """A contents page's last entry can look like a chapter (text follows it: a preface, the
    epigraphs): "CHAPTER 135" just before "CHAPTER 1". Drop such leading headings, and any
    line naming two chapters at once (a contents line)."""
    matches = [m for m in matches if len(re.findall(r"\bchapter\b", m.group(0), re.IGNORECASE)) < 2]
    while len(matches) > 1:
        first, second = _heading_number(matches[0]), _heading_number(matches[1])
        if first is None or second is None or first <= second:
            break
        matches = matches[1:]
    return matches


def chapter_headings(text: str) -> list[re.Match]:
    """The chapter headings of a book: its "Chapter ..." lines, or else the first fallback style
    that gives at least 3 chapters counting up. Empty when there are none (see _equal_parts)."""
    found = _drop_contents_tail(_drop_contents(text, list(CHAPTER_HEADING.finditer(text))))
    if len(found) >= 3:
        return found
    for pattern in FALLBACK_HEADINGS:
        matches = _drop_contents_tail(_drop_contents(text, list(pattern.finditer(text))))
        if len(matches) >= 3 and _counts_up(matches):
            return matches
    # few or short chapters: keep every "Chapter ..." heading, however short its chapter
    return found if len(found) >= 3 else _drop_contents_tail(list(CHAPTER_HEADING.finditer(text)))


def find_chapters(text: str) -> list[Chapter]:
    return [Chapter(index=i, title=m.group(0).strip(), start=m.end()) for i, m in enumerate(chapter_headings(text))]


def _story_paragraphs(text: str, chapters: list[Chapter]) -> list[tuple[int, str]]:
    """(offset, paragraph) pairs, skipping chapter headings and any front matter
    (title page, preface, contents) before the first chapter."""
    heading_starts = {m.start() for m in chapter_headings(text)}
    first = chapters[0].start if chapters else 0
    return [
        (m.start(), m.group(0))
        for m in re.finditer(r"[^\n]+", text)
        if m.start() >= first and m.start() not in heading_starts
    ]


def split_sentences(
    text: str, nlp: Language, progress: ProgressCallback | None = None
) -> tuple[list[Sentence], list[Chapter]]:
    """Return every story sentence (with the entities spaCy found in it) and
    the chapters. Books without headings are cut into equal parts."""
    chapters = find_chapters(text)
    chapter_starts = [c.start for c in chapters]
    paragraphs = _story_paragraphs(text, chapters)

    sentences: list[Sentence] = []
    # nlp.pipe processes paragraphs in batches, which is much faster than one by one
    docs = nlp.pipe((p for _, p in paragraphs), batch_size=64)
    for done, ((offset, _), doc) in enumerate(zip(paragraphs, docs), start=1):
        chapter = max(bisect_right(chapter_starts, offset) - 1, 0)
        for sent in doc.sents:
            if not sent.text.strip():
                continue
            sentences.append(
                Sentence(
                    index=len(sentences),
                    text=sent.text,
                    start=offset + sent.start_char,
                    end=offset + sent.end_char,
                    chapter=chapter,
                    entities=[
                        Entity(e.text, e.label_, offset + e.start_char, offset + e.end_char)
                        for e in sent.ents
                    ],
                    tags=word_types(sent),
                )
            )
        if progress and done % 50 == 0:
            progress(done, len(paragraphs))

    if not chapters:
        chapters = _equal_parts(sentences)
    return sentences, chapters


def _equal_parts(sentences: list[Sentence]) -> list[Chapter]:
    """Assign sentences to FALLBACK_PARTS equal-sized parts."""
    if not sentences:
        return []
    parts = min(FALLBACK_PARTS, len(sentences))
    chapters = []
    for s in sentences:
        s.chapter = s.index * parts // len(sentences)
        if s.chapter == len(chapters):
            chapters.append(Chapter(index=s.chapter, title=f"Part {s.chapter + 1}", start=s.start))
    return chapters
