"""Where each chapter happens: forest, desert, mountains, town...

Read from the words that describe the surroundings ("the woods", "a dusty street",
"the sea"). Every landscape has a word list; a chapter's clues are those words, counted
per 1,000 words. Neighbouring chapters are averaged (a story stays in one place for a
while), and a chapter without clear clues keeps the landscape of the one before it.
Instant and fully local: no model, and every choice can be explained by its clue words.
"""

import re
from collections import Counter

from analyzer.models import Sentence

# landscape -> clue words (lower case; a plural "s"/"es" also counts)
LANDSCAPES: dict[str, list[str]] = {
    "town": ["town", "city", "street", "shop", "market", "pavement", "alley", "inn", "crowd",
             "square", "warehouse", "factory", "chimney", "lamp-post", "cab", "omnibus", "london", "paris"],
    "countryside": ["field", "meadow", "garden", "hedge", "hedgerow", "pasture", "farm", "orchard", "park",
                    "lawn", "village", "cottage", "cow", "sheep", "harvest", "grass", "hill", "meadows", "barn", "shrubbery"],
    "forest": ["forest", "woods", "grove", "thicket", "oak", "pine", "tree", "undergrowth", "copse", "glade",
               "fern", "timber", "woodland"],
    "mountains": ["mountain", "peak", "summit", "crag", "cliff", "precipice", "ravine", "gorge", "boulder",
                  "slope", "alps", "highland"],
    "desert": ["desert", "dune", "sand", "cactus", "oasis", "camel", "arid", "scorching", "drought", "caravan"],
    "water": ["sea", "ocean", "shore", "beach", "coast", "wave", "ship", "harbour", "harbor", "tide", "island",
              "boat", "sailor", "river", "lake", "stream", "pond"],
    "marsh": ["marsh", "swamp", "bog", "fen", "reed", "mire", "mud", "sluice", "dyke", "creek"],
    "snow": ["snow", "frost", "ice", "glacier", "blizzard", "frozen", "icy", "sledge", "sleigh", "iceberg"],
}
LABELS = {"town": "Town", "countryside": "Countryside", "forest": "Forest", "mountains": "Mountains",
          "desert": "Desert", "water": "Sea & water", "marsh": "Marshes", "snow": "Snow & ice"}
DEFAULT = "countryside"  # a book with no clues at all
MIN_CLUES = 2  # a chapter needs at least this many clue words (over its neighbourhood) to choose
MIN_DENSITY = 0.6  # ...and this many per 1,000 words

_WORD = re.compile(r"[a-z]+(?:-[a-z]+)?")


def word_lookup(lists: dict[str, list[str]], endings: tuple[str, ...] = ("s", "es")) -> dict[str, tuple[str, str]]:
    """Every form of every clue word ("tree", "trees") -> (its list's name, the clue word)."""
    lookup = {}
    for name, words in lists.items():
        for w in words:
            for form in (w, *(w + e for e in endings)):
                lookup.setdefault(form, (name, w))
    return lookup


_LOOKUP = word_lookup(LANDSCAPES)


def chapter_clues(sentences: list[Sentence], chapters: int, lookup: dict | None = None) -> tuple[list[Counter], list[int]]:
    """For each chapter: Counter[(kind, clue word)] and its number of words.
    `lookup` comes from word_lookup (the landscapes' by default)."""
    lookup = lookup or _LOOKUP
    clues = [Counter() for _ in range(chapters)]
    words = [0] * chapters
    for s in sentences:
        if not 0 <= s.chapter < chapters:
            continue
        tokens = _WORD.findall(s.text.lower())
        words[s.chapter] += len(tokens)
        for tok in tokens:
            hit = lookup.get(tok)
            if hit:
                clues[s.chapter][hit] += 1
    return clues, words


def chapter_landscapes(sentences: list[Sentence], chapters: int, smooth: int = 1) -> list[dict]:
    """[chapter] -> {"kind": landscape, "clues": [up to 3 clue words], "sure": bool}.
    `sure` is False when the chapter had no clear clues and kept its neighbour's landscape."""
    if chapters <= 0:
        return []
    clues, words = chapter_clues(sentences, chapters)
    picks: list[str | None] = []
    for ch in range(chapters):
        lo, hi = max(0, ch - smooth), min(chapters, ch + smooth + 1)
        totals = Counter()
        for k in range(lo, hi):  # the chapter itself counts twice as much as each neighbour
            for (kind, _), n in clues[k].items():
                totals[kind] += n * (2 if k == ch else 1)
        span = sum(words[lo:hi]) + words[ch]
        best = totals.most_common(1)
        if best and best[0][1] >= MIN_CLUES * 2 and best[0][1] * 1000 / max(span, 1) >= MIN_DENSITY:
            picks.append(best[0][0])
        else:
            picks.append(None)
    # chapters without clues keep the landscape before them (the first ones take the next one)
    known = [p for p in picks if p]
    fallback = Counter(known).most_common(1)[0][0] if known else DEFAULT
    filled, last = [], None
    for p in picks:
        last = p or last
        filled.append(last)
    first = next((p for p in filled if p), fallback)
    filled = [p or first for p in filled]
    out = []
    for ch, kind in enumerate(filled):
        own = [w for (k, w), _ in sorted(clues[ch].items(), key=lambda kv: -kv[1]) if k == kind][:3]
        out.append({"kind": kind, "clues": own, "sure": picks[ch] is not None})
    return out
