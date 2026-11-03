"""Who talks, and to whom: the book's dialogue and its speakers.

Dialogue is the text between quotation marks. Each paragraph of dialogue is one speaker's
turn (the convention of printed novels), and the speaker is found in three ways, from most
to least certain:

1. "said": a speech verb next to a character's name in the narration around the quote
   ('"Yes," said Elizabeth' / 'Elizabeth replied, "Yes."'). The most reliable.
   "pronoun": the same with a pronoun ('"Yes," said she'), using the character the pronoun
   step linked it to. Less reliable: that step tends to give "she" to the heroine.
2. "before": the paragraph's narration before the first quote names exactly one character
   ('Elizabeth smiled. "Yes."').
3. "turn": two people talking take turns, so an unattributed paragraph in a back-and-forth
   goes to the person who spoke two paragraphs earlier (A, B, A, B, ...).

The listener of a turn is the other speaker it answers (or who answers it) in the same
conversation. Everything runs on the saved sentences and mentions: instant, no model, and
it works for books analysed before this module existed.
"""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .models import Mention, Sentence

SPEECH_VERBS = (
    "said says say saying replied replies answered answers asked asks cried cries exclaimed exclaims "
    "continued continues added adds returned observed remarked whispered whispers shouted shouts muttered "
    "mutters called began begins interrupted rejoined repeated resumed retorted inquired enquired murmured "
    "sobbed protested urged insisted declared demanded growled roared screamed stammered explained "
    "admitted agreed persisted pleaded begged groaned gasped laughed sighed spoke speaks told tells "
    "suggested responded concluded proceeded observed cried replied answered ventured faltered"
).split()
_VERB = re.compile(r"\b(?:" + "|".join(sorted(set(SPEECH_VERBS), key=len, reverse=True)) + r")\b", re.I)
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
NEAR = 30  # characters: how close a name must be to the speech verb
MAX_BREAK = 2  # a narration paragraph longer than this many sentences ends a conversation


@dataclass
class Line:
    """One quote: the words between a pair of quotation marks."""

    start: int  # offsets of the quoted words in the cleaned text (marks left out)
    end: int
    text: str
    chapter: int
    paragraph: int
    first: int  # sentence indexes the quote spans
    last: int
    speaker: int | None = None  # character id, or None when the speaker is unknown
    listener: int | None = None
    how: str = ""  # "said", "pronoun", "before", "turn" or "" (see the module docstring)

    @property
    def words(self) -> int:
        return len(_WORD.findall(self.text))


def paragraphs(sentences: list[Sentence]) -> list[list[int]]:
    """Sentence indexes grouped by paragraph. Sentences inside a paragraph are one space
    apart in the cleaned text; paragraphs are separated by a blank line (2+ characters)."""
    groups: list[list[int]] = []
    for i, s in enumerate(sentences):
        prev = sentences[i - 1] if i else None
        if prev is None or s.chapter != prev.chapter or s.start - prev.end >= 2:
            groups.append([])
        groups[-1].append(i)
    return groups


def _paragraph_text(sentences: list[Sentence], ids: list[int]) -> tuple[int, str]:
    """(offset, text) of a paragraph rebuilt from its sentences at their real offsets."""
    offset = sentences[ids[0]].start
    chars = [" "] * (sentences[ids[-1]].end - offset)
    for i in ids:
        s = sentences[i]
        chars[s.start - offset:s.end - offset] = s.text
    return offset, "".join(chars)


def _quote_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of each quote's words. Straight quotes toggle; curly quotes open and
    close. An unclosed quote runs to the end of the paragraph (a speech that continues in
    the next paragraph leaves its closing mark off)."""
    spans, opened = [], None
    for i, ch in enumerate(text):
        if ch == "“" or (ch == '"' and opened is None):
            opened = i + 1
        elif (ch == "”" or ch == '"') and opened is not None:
            if text[opened:i].strip():
                spans.append((opened, i))
            opened = None
    if opened is not None and text[opened:].strip():
        spans.append((opened, len(text)))
    return spans


def _possessive(text: str, start: int, end: int) -> bool:
    """A pronoun owning the next word ("his", "their", "her father"), so not the speaker."""
    word = text[start:end].lower()
    return word in ("his", "their", "its") or (word == "her" and bool(re.match(r" [a-z]", text[end:end + 2])))


def _said_by(narration: tuple[int, int], text: str, offset: int,
             found: list[tuple[int, int, int, str]]) -> tuple[int, str] | None:
    """(character, "said" or "pronoun") next to a speech verb in one stretch of narration, if any."""
    a, b = narration
    best = None
    for verb in _VERB.finditer(text, a, b):
        for start, end, cid, source in found:
            if _possessive(text, start - offset, end - offset):
                continue  # '"...," said her father': "her" is not the speaker
            if a <= start - offset and end - offset <= b:
                gap = max(verb.start() - (end - offset), (start - offset) - verb.end())
                if gap <= NEAR and (best is None or gap < best[0]):
                    best = (gap, (cid, "said" if source == "name" else "pronoun"))
        if best:
            return best[1]
    return None


def find_lines(sentences: list[Sentence], mentions: list[Mention]) -> list[Line]:
    """Every quote in the book, with its speaker and listener where they can be told."""
    by_sentence: dict[int, list[tuple[int, int, int, str]]] = defaultdict(list)
    for m in mentions:
        by_sentence[m.sentence_index].append((m.start, m.end, m.character_id, m.source))

    lines: list[Line] = []
    # per paragraph: (chapter, its lines) or None (a long narration paragraph, which ends a conversation)
    turns: list[tuple[int, list[Line]] | None] = []
    for p, ids in enumerate(paragraphs(sentences)):
        offset, text = _paragraph_text(sentences, ids)
        spans = _quote_spans(text)
        if not spans:
            turns.append(None if len(ids) > MAX_BREAK else (sentences[ids[0]].chapter, []))
            continue
        found = [m for i in ids for m in by_sentence[i]]
        # narration stretches: before the first quote, between quotes, after the last one
        cuts = [0] + [x for span in spans for x in (span[0] - 1, span[1] + 1)] + [len(text)]
        narration = [(cuts[k], cuts[k + 1]) for k in range(0, len(cuts), 2)]
        speaker, how = None, ""
        for stretch in narration[1:] + narration[:1]:  # after a quote first, then the opening words
            said = _said_by(stretch, text, offset, found)
            if said is not None:
                speaker, how = said
                break
        if speaker is None:
            before = {cid for start, _, cid, _ in found if start - offset < narration[0][1]}
            if len(before) == 1:
                speaker, how = before.pop(), "before"
        own = []
        for a, b in spans:
            inside = [i for i in ids if sentences[i].end > offset + a and sentences[i].start < offset + b]
            own.append(Line(offset + a, offset + b, text[a:b].strip(), sentences[ids[0]].chapter, p,
                            inside[0], inside[-1], speaker, None, how))
        lines.extend(own)
        turns.append((sentences[ids[0]].chapter, own))
    _take_turns(turns)
    return lines


def _conversations(turns: list[tuple[int, list[Line]] | None]) -> list[list[list[Line]]]:
    """Runs of dialogue paragraphs in one chapter, not broken by a long stretch of narration."""
    runs: list[list[list[Line]]] = [[]]
    chapter = None
    for turn in turns:
        if turn is None or turn[0] != chapter:
            runs.append([])
        if turn is not None:
            chapter = turn[0]
            if turn[1]:
                runs[-1].append(turn[1])
    return [r for r in runs if r]


def _take_turns(turns: list[tuple[int, list[Line]] | None]) -> None:
    """Fill unknown speakers by turn-taking, then set every line's listener."""
    for run in _conversations(turns):
        who = [t[0].speaker for t in run]
        for k in range(2, len(run)):
            # only straight back-and-forth: three dialogue paragraphs in a row, no narration between
            in_a_row = run[k][0].paragraph - run[k - 2][0].paragraph == 2
            if in_a_row and who[k] is None and None not in (who[k - 2], who[k - 1]) and who[k - 2] != who[k - 1]:
                who[k] = who[k - 2]
                for line in run[k]:
                    line.speaker, line.how = who[k], "turn"
        for k, turn in enumerate(run):
            if who[k] is None:
                continue
            answered = next((w for w in reversed(who[:k]) if w is not None and w != who[k]), None)
            answer = next((w for w in who[k + 1:] if w is not None and w != who[k]), None)
            # the person this turn answers, else the person who answers it (who must speak right before or after)
            near = [w for w in who[max(0, k - 1):k + 2] if w is not None and w != who[k]]
            listener = answered if answered in near else answer if answer in near else None
            for line in turn:
                line.listener = listener


# --- Summaries --------------------------------------------------------------------------------

def words_spoken(lines: list[Line], num_characters: int) -> list[int]:
    """[character] -> how many words they say."""
    totals = [0] * num_characters
    for line in lines:
        if line.speaker is not None:
            totals[line.speaker] += line.words
    return totals


def who_talks_to_whom(lines: list[Line], num_characters: int) -> list[list[int]]:
    """[speaker][listener] -> how many quotes the speaker addresses to the listener."""
    counts = [[0] * num_characters for _ in range(num_characters)]
    for line in lines:
        if line.speaker is not None and line.listener is not None:
            counts[line.speaker][line.listener] += 1
    return counts


def chapter_dialogue_share(lines: list[Line], sentences: list[Sentence], num_chapters: int) -> list[float]:
    """[chapter] -> share of its words that are spoken (inside quotes)."""
    spoken, total = [0] * num_chapters, [0] * num_chapters
    for line in lines:
        spoken[line.chapter] += line.words
    for s in sentences:
        total[s.chapter] += len(_WORD.findall(s.text))
    return [min(a / b, 1.0) if b else 0.0 for a, b in zip(spoken, total)]


def line_tone(line: Line, sentences: list[Sentence]) -> float:
    """The tone of a quote: the average sentiment of the sentences it spans."""
    spanned = sentences[line.first:line.last + 1]
    return sum(s.sentiment for s in spanned) / len(spanned)


def whole_turns(lines: list[Line]) -> list[Line]:
    """Quotes split by their speaker ('"Well," said Jane, "I hope so."') joined back into
    one Line per paragraph."""
    joined: dict[int, Line] = {}
    for line in lines:
        if line.paragraph in joined:
            first = joined[line.paragraph]
            joined[line.paragraph] = Line(first.start, line.end, f"{first.text} {line.text}", first.chapter,
                                          first.paragraph, first.first, line.last, first.speaker, first.listener,
                                          first.how)
        else:
            joined[line.paragraph] = line
    return list(joined.values())


def strongest_lines(lines: list[Line], sentences: list[Sentence], speaker: int, n: int = 2,
                    min_words: int = 6) -> tuple[list[tuple[Line, float]], list[tuple[Line, float]]]:
    """A speaker's n brightest and n darkest turns (with their tone). Only turns where the
    speaker is named next to a speech verb, the surest way of telling who speaks."""
    own = [(line, line_tone(line, sentences)) for line in whole_turns(lines)
           if line.speaker == speaker and line.how == "said" and line.words >= min_words]
    ranked = sorted(own, key=lambda lt: lt[1])
    darkest = [lt for lt in ranked[:n] if lt[1] < 0]
    brightest = [lt for lt in ranked[::-1][:n] if lt[1] > 0]
    return brightest, darkest


def signature_words(lines: list[Line], speaker: int, n: int = 10, min_count: int = 3,
                    stop_words: frozenset[str] = frozenset()) -> list[str]:
    """The words a character says more than everyone else, compared with the rest of the
    dialogue. Uses the "weighted log-odds" of Monroe et al. (2008): a word's lead over the
    others divided by how uncertain that lead is, so a word said twice can't beat one said
    forty times by luck."""
    mine, theirs = Counter(), Counter()
    for line in lines:
        words = [w.lower() for w in _WORD.findall(line.text)]
        (mine if line.speaker == speaker else theirs).update(w for w in words if w not in stop_words and len(w) > 2)
    if not mine:
        return []
    every = mine + theirs
    prior_total = sum(every.values())
    n_mine, n_theirs = sum(mine.values()), sum(theirs.values())
    smoothing = min(500, prior_total)  # pretend words, shared out like the whole dialogue
    scores = {}
    for word, count in mine.items():
        if count < min_count:
            continue
        prior = every[word] / prior_total * smoothing
        a = (count + prior) / (n_mine + smoothing - count - prior)
        b = (theirs[word] + prior) / (n_theirs + smoothing - theirs[word] - prior)
        scores[word] = (math.log(a) - math.log(b)) / math.sqrt(1 / (count + prior) + 1 / (theirs[word] + prior))
    return [w for w, z in sorted(scores.items(), key=lambda kv: -kv[1])[:n] if z > 1.5]
