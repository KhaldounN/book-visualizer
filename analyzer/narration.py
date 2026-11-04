"""Who tells the story: first-person books and their narrator (no model, from saved data).

A first-person narrator says "I" in the narration, and the analysis doesn't count "I" as a mention
of anyone, so the narrator (Pip, Watson, Jane Eyre) looks like a minor character. They can still be
found: other people name them, in dialogue, while the narration almost never does ("Pip, old chap!"
but never "Pip went home").
"""

import bisect
import re
from collections import Counter

from .dialogue import Line
from .models import BookAnalysis

FIRST_PERSON = re.compile(r"\b(I|me|my|myself)\b")
FIRST_PERSON_SHARE = 0.3  # a book is first-person when this share of narration sentences says I/me/my
QUOTED_SHARE = 0.85  # the narrator is named inside quotes at least this often...
MIN_NAMED = 20  # ...at least this many times...
MIN_SPREAD = 0.3  # ...in at least this share of the chapters (a character of one embedded tale is not the narrator)


def _quoted(lines: list[Line]):
    spans = sorted((line.start, line.end) for line in lines)
    starts = [s for s, _ in spans]

    def inside(position: int) -> bool:
        i = bisect.bisect_right(starts, position) - 1
        return i >= 0 and spans[i][0] <= position < spans[i][1]
    return inside


def first_person_share(analysis: BookAnalysis, lines: list[Line]) -> float:
    """The share of narration sentences (outside quotes) that say I, me, my or myself."""
    inside = _quoted(lines)
    narration = [s for s in analysis.sentences if not inside(s.start)]
    return sum(bool(FIRST_PERSON.search(s.text)) for s in narration) / max(len(narration), 1)


def narrator(analysis: BookAnalysis, lines: list[Line]) -> int | None:
    """The id of the character who tells a first-person book, or None (third person, or no clear
    narrator: a book of letters and diaries like Dracula has several)."""
    if not analysis.chapters or first_person_share(analysis, lines) < FIRST_PERSON_SHARE:
        return None
    inside = _quoted(lines)
    named = [m for m in analysis.mentions if m.source == "name"]
    total = Counter(m.character_id for m in named)
    in_quotes = Counter(m.character_id for m in named if inside(m.start))
    chapters = {cid: {analysis.sentences[m.sentence_index].chapter for m in named if m.character_id == cid}
                for cid in total}
    candidates = [cid for cid in total if total[cid] >= MIN_NAMED and in_quotes[cid] / total[cid] >= QUOTED_SHARE
                  and len(chapters[cid]) / len(analysis.chapters) >= MIN_SPREAD]
    return max(candidates, key=lambda cid: total[cid]) if candidates else None
