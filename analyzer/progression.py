"""How the story changes from chapter to chapter."""

from .emotions import average_emotions
from .models import KeyMoment, Mention, Sentence
from .relationships import characters_per_sentence


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def chapter_sentiment(sentences: list[Sentence], num_chapters: int) -> list[float]:
    """Average sentiment of all sentences in each chapter."""
    by_chapter: list[list[float]] = [[] for _ in range(num_chapters)]
    for s in sentences:
        by_chapter[s.chapter].append(s.sentiment)
    return [_average(values) or 0.0 for values in by_chapter]


def _running_totals(sentences: list[Sentence]) -> list[float]:
    """totals[i] = sum of the first i sentiments, so any stretch's sum is one
    subtraction: sum(a..b) = totals[b + 1] - totals[a]."""
    totals = [0.0]
    for s in sentences:
        totals.append(totals[-1] + s.sentiment)
    return totals


def rolling_sentiment(sentences: list[Sentence], window: int) -> list[float]:
    """The mood around each sentence: the average of the `window` sentences
    centred on it (fewer at the start and end of the book)."""
    totals = _running_totals(sentences)
    half = window // 2
    rolled = []
    for i in range(len(sentences)):
        a, b = max(0, i - half), min(len(sentences) - 1, i + window - half - 1)
        rolled.append((totals[b + 1] - totals[a]) / (b - a + 1))
    return rolled


def key_moments(sentences: list[Sentence], window: int = 20, n: int = 3) -> tuple[list[KeyMoment], list[KeyMoment]]:
    """The n darkest and n brightest passages of `window` sentences.
    A passage stays inside one chapter, and the passages never overlap."""
    totals = _running_totals(sentences)
    candidates = [
        KeyMoment(i, i + window - 1, sentences[i].chapter, (totals[i + window] - totals[i]) / window)
        for i in range(len(sentences) - window + 1)
        if sentences[i].chapter == sentences[i + window - 1].chapter
    ]

    def pick(ranked: list[KeyMoment]) -> list[KeyMoment]:
        chosen: list[KeyMoment] = []
        for moment in ranked:
            if all(moment.last < c.first or moment.first > c.last for c in chosen):
                chosen.append(moment)
                if len(chosen) == n:
                    break
        return chosen

    ranked = sorted(candidates, key=lambda m: m.score)
    return pick(ranked), pick(ranked[::-1])


MIN_SWING = 0.005  # a turning point must move the smoothed tone at least this much


def story_arc(chapter_tone: list[float], smooth: int = 4, points: int = 6
              ) -> tuple[list[float], list[tuple[int, str]], list[tuple[int, int]]]:
    """The book's overall shape: (arc, turning points, acts).

    arc: each chapter's tone averaged with `smooth` chapters either side.
    turning points: (chapter, "high" or "low") for the `points` biggest peaks
    and dips of the arc. acts: (first, last) chapter of each act; a new act
    starts at every low point.
    """
    n = len(chapter_tone)
    arc = [sum(chapter_tone[max(0, i - smooth):i + smooth + 1]) / len(chapter_tone[max(0, i - smooth):i + smooth + 1])
           for i in range(n)]
    candidates = []
    for i in range(2, n - 2):
        near = arc[i - 2:i + 3]
        swing = abs(arc[i] - (arc[i - 2] + arc[i + 2]) / 2)
        # a flat stretch is "highest" and "lowest" at once but turns nowhere
        if arc[i] in (max(near), min(near)) and swing >= MIN_SWING:
            candidates.append((swing, i, "high" if arc[i] == max(near) else "low"))
    turning = sorted((i, kind) for _, i, kind in sorted(candidates, reverse=True)[:points])
    cuts = [0] + [i for i, kind in turning if kind == "low"] + [n]
    acts = [(a, b - 1) for a, b in zip(cuts, cuts[1:]) if b > a]
    return arc, turning, acts


def chapter_emotions(sentences: list[Sentence], num_chapters: int, kind: str = "emotions") -> list[dict[str, float]]:
    """Average emotion mix of each chapter (kind="fine" for the fine emotions)."""
    by_chapter: list[list[dict[str, float]]] = [[] for _ in range(num_chapters)]
    for s in sentences:
        by_chapter[s.chapter].append(getattr(s, kind))
    return [average_emotions(mixes) for mixes in by_chapter]


def emotions_by_character(mentions: list[Mention], sentences: list[Sentence],
                          num_characters: int, kind: str = "emotions") -> list[dict[str, float]]:
    """[character] -> average emotion mix of the sentences that mention them
    (each sentence once, however often the character is named in it)."""
    mixes: list[list[dict[str, float]]] = [[] for _ in range(num_characters)]
    for sentence, present in zip(sentences, characters_per_sentence(sentences, mentions)):
        for character_id in present:
            mixes[character_id].append(getattr(sentence, kind))
    return [average_emotions(m) for m in mixes]


def mentions_by_chapter(mentions: list[Mention], sentences: list[Sentence],
                        num_characters: int, num_chapters: int) -> list[list[int]]:
    """[character][chapter] -> how often the character is mentioned there."""
    counts = [[0] * num_chapters for _ in range(num_characters)]
    for m in mentions:
        counts[m.character_id][sentences[m.sentence_index].chapter] += 1
    return counts


def sentiment_by_chapter(mentions: list[Mention], sentences: list[Sentence],
                         num_characters: int, num_chapters: int) -> list[list[float | None]]:
    """[character][chapter] -> average sentiment of the sentences that mention
    the character (each sentence once), or None if they are not in it."""
    scores: list[list[list[float]]] = [[[] for _ in range(num_chapters)] for _ in range(num_characters)]
    for sentence, present in zip(sentences, characters_per_sentence(sentences, mentions)):
        for character_id in present:
            scores[character_id][sentence.chapter].append(sentence.sentiment)
    return [[_average(values) for values in row] for row in scores]


# --- The shape of the story --------------------------------------------------------------------
# Reagan et al. (2016) ran sentiment over ~1,700 Project Gutenberg books and found that most
# follow one of six emotional shapes. Each shape here is a few (position, height) points joined
# by straight lines; position 0 is the first page and 1 the last.

STORY_SHAPES = {
    "Rags to riches": ([(0, 0), (1, 1)], "Things keep getting better."),
    "Tragedy": ([(0, 1), (1, 0)], "Things keep getting worse."),
    "Man in a hole": ([(0, 1), (.5, 0), (1, 1)], "A fall, then a climb back up."),
    "Icarus": ([(0, 0), (.5, 1), (1, 0)], "A rise, then a fall."),
    "Cinderella": ([(0, 0), (.3, .6), (.6, .1), (1, 1)], "A rise, a fall, then a happy ending."),
    "Oedipus": ([(0, 1), (.3, .4), (.6, .9), (1, 0)], "A fall, a rise, then a final fall."),
}
SHAPE_SAMPLES = 50  # every curve is compared at this many evenly spaced points
WEAK_FIT = 0.2  # below this, the book follows none of the shapes


def shape_curve(name: str, samples: int = SHAPE_SAMPLES) -> list[float]:
    """The template of one story shape, as `samples` heights."""
    points = STORY_SHAPES[name][0]
    curve = []
    for j in range(samples):
        x = j / (samples - 1)
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if x <= x1:
                curve.append(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
                break
    return curve


def _resample(values: list[float], samples: int) -> list[float]:
    """`samples` evenly spaced values along `values` (straight lines in between)."""
    out = []
    for j in range(samples):
        p = j / (samples - 1) * (len(values) - 1)
        i = int(p)
        nxt = values[min(i + 1, len(values) - 1)]
        out.append(values[i] + (nxt - values[i]) * (p - i))
    return out


def _standardize(values: list[float]) -> list[float] | None:
    """Shift to average 0 and stretch to spread 1, so only the shape is left
    (not how positive the book is overall, nor how strong its swings are)."""
    mean = sum(values) / len(values)
    spread = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
    return [(v - mean) / spread for v in values] if spread > 1e-9 else None


def story_shape(sentences: list[Sentence], samples: int = SHAPE_SAMPLES
                ) -> tuple[list[float], list[tuple[str, float]]]:
    """The book's overall mood curve and how well each of the six shapes fits it.

    The curve is the sentence mood averaged over a window of a fifth of the book (a tenth on
    each side; only the big movements are left), then sampled at `samples` points. Each shape's fit is the correlation between the
    curve and the shape's template: 1 = the same shape, 0 = unrelated, below 0 = opposite.
    Returns (curve, [(shape, fit)] best first); no fits for a short or perfectly flat book.
    """
    if len(sentences) < samples:
        return [], []
    curve = _resample(rolling_sentiment(sentences, max(1, len(sentences) // 5)), samples)
    book = _standardize(curve)
    if book is None:
        return curve, []
    fits = []
    for name in STORY_SHAPES:
        template = _standardize(shape_curve(name, samples))
        fits.append((name, sum(a * b for a, b in zip(book, template)) / samples))
    return curve, sorted(fits, key=lambda f: -f[1])
