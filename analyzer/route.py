"""The shape of the road through each chapter: straight, winding, or steep (switchbacks).

Read from the words describing how people travel ("a long straight avenue", "the winding
path", "we climbed the steep slope"), the same way analyzer/landscape.py reads the setting.
The road's height already shows the mood, so these clues only bend it sideways: a straight
road, a winding one, or the zigzag of a mountain road for climbing. Chapters without
clear clues get the usual gentle bends. Instant and fully local: no model.
"""

from collections import Counter

from analyzer.landscape import chapter_clues, word_lookup
from analyzer.models import Sentence

# road shape -> clue words (lower case; -s, -ing, -ed, -er, -est forms also count)
ROUTES: dict[str, list[str]] = {
    "straight": ["avenue", "highway", "highroad", "high-road", "causeway", "railway", "railroad", "turnpike",
                 "boulevard", "canal"],
    "winding": ["winding", "twisting", "meander", "zigzag", "labyrinth", "maze", "crooked", "serpentine",
                "wander", "wandered", "detour", "roundabout", "circuitous", "rambling"],
    "steep": ["climb", "ascent", "ascend", "uphill", "downhill", "steep", "upward", "scramble", "clamber",
              "descent", "precipitous"],
}
LABELS = {"straight": "Straight road", "winding": "Winding road", "steep": "Steep climb"}
MIN_CLUES = 2  # a chapter needs at least this many route words...
MIN_DENSITY = 0.5  # ...and this many per 1,000 words

_LOOKUP = word_lookup(ROUTES, endings=("s", "es", "ing", "ed", "er", "est"))


def chapter_routes(sentences: list[Sentence], chapters: int) -> list[dict | None]:
    """[chapter] -> {"kind": road shape, "clues": [up to 3 clue words]}, or None (the usual bends)."""
    if chapters <= 0:
        return []
    clues, words = chapter_clues(sentences, chapters, _LOOKUP)
    out: list[dict | None] = []
    for ch in range(chapters):
        totals = Counter()
        for (kind, _), n in clues[ch].items():
            totals[kind] += n
        best = totals.most_common(1)
        if not best or best[0][1] < MIN_CLUES or best[0][1] * 1000 / max(words[ch], 1) < MIN_DENSITY:
            out.append(None)
            continue
        kind = best[0][0]
        own = [w for (k, w), _ in sorted(clues[ch].items(), key=lambda kv: -kv[1]) if k == kind][:3]
        out.append({"kind": kind, "clues": own})
    return out
