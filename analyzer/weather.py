"""The weather in each chapter: rain, storm, snow, fog, wind, sunshine, or nothing said.

Read from weather words ("it was raining", "a thick fog", "the thunder"), the same way
analyzer/landscape.py reads the setting. Weather changes quickly, so unlike the landscape
it is never carried over: a chapter that says nothing about the weather gets none.
Instant and fully local: no model.
"""

from collections import Counter

from analyzer.landscape import chapter_clues, word_lookup
from analyzer.models import Sentence

# weather -> clue words (lower case; "-s", "-ing", "-ed", "-y" forms also count)
WEATHERS: dict[str, list[str]] = {
    "storm": ["storm", "thunder", "lightning", "tempest", "gale", "hurricane", "thunderstorm"],
    "rain": ["rain", "drizzle", "downpour", "shower", "umbrella", "puddle", "drench", "raindrop", "wet"],
    "snow": ["snow", "snowflake", "sleet", "blizzard", "snowfall", "snowstorm"],
    "fog": ["fog", "mist", "haze", "misty", "foggy"],
    "wind": ["wind", "breeze", "gust", "windy", "blustery"],
    "sun": ["sunshine", "sunlight", "sunny", "sunbeam", "sunshiny", "sunburnt", "cloudless"],
}
LABELS = {"storm": "Storm", "rain": "Rain", "snow": "Snow", "fog": "Fog", "wind": "Wind", "sun": "Sunshine"}
MIN_CLUES = 2  # a chapter needs at least this many weather words...
MIN_DENSITY = 0.4  # ...and this many per 1,000 words (one passing "wind" is not weather)
STORM_FIRST = 2  # thunder and lightning win over plain rain once there are this many storm words

_LOOKUP = word_lookup(WEATHERS, endings=("s", "es", "ing", "ed", "y"))


def chapter_weather(sentences: list[Sentence], chapters: int) -> list[dict | None]:
    """[chapter] -> {"kind": weather, "clues": [up to 3 clue words], "strength": 0..1} or None."""
    if chapters <= 0:
        return []
    clues, words = chapter_clues(sentences, chapters, _LOOKUP)
    out: list[dict | None] = []
    for ch in range(chapters):
        totals = Counter()
        for (kind, _), n in clues[ch].items():
            totals[kind] += n
        if totals["storm"] >= STORM_FIRST:  # a storm usually brings rain words too
            totals["storm"] += totals.pop("rain", 0)
        best = totals.most_common(1)
        density = best[0][1] * 1000 / max(words[ch], 1) if best else 0
        if not best or best[0][1] < MIN_CLUES or density < MIN_DENSITY:
            out.append(None)
            continue
        kind = best[0][0]
        own = [w for (k, w), _ in sorted(clues[ch].items(), key=lambda kv: -kv[1])
               if k == kind or (kind == "storm" and k == "rain")][:3]
        # how heavy it looks: 0.3 for the minimum, 1.0 from about four times the minimum density
        strength = round(min(1.0, 0.3 + 0.7 * (density - MIN_DENSITY) / (3 * MIN_DENSITY)), 2)
        out.append({"kind": kind, "clues": own, "strength": strength})
    return out
