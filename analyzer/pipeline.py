"""Run every analysis step in order and collect the results.

The AI models are loaded one at a time and released after use, so the
whole analysis fits in about 2 GB of memory.
"""

import gc
import time
from typing import Callable

from . import chapter_events, coref, emotions, sentiment
from .characters import find_characters
from .loaders import book_info, load_text
from .models import BookAnalysis
from .progression import (
    chapter_emotions,
    chapter_sentiment,
    emotions_by_character,
    mentions_by_chapter,
    sentiment_by_chapter,
)
from .relationships import find_relationships
from .segment import split_sentences

SPACY_MODEL = "en_core_web_lg"

# Bump this whenever BookAnalysis changes shape or the analysis changes, so
# results saved by an older version are re-analyzed instead of loaded
ANALYSIS_VERSION = 5  # 5: EmoLit's 38 fine emotions in 8 families

# (step name, share of the total time) measured on Great Expectations
# (~12 min); used to turn each step's own progress into one overall progress bar
STEPS = {
    "Reading sentences": 0.04,  # ~29 s
    "Finding characters": 0.01,  # <1 s
    "Linking pronouns": 0.26,  # ~184 s
    "Scoring sentiment": 0.34,  # ~249 s
    "Detecting emotions": 0.33,  # ~245 s
    "Naming chapters": 0.01,  # ~4 s
    "Finding relationships": 0.01,  # <1 s
}

ProgressCallback = Callable[[str, float], None]  # (step name, overall 0..1)


def load_spacy():
    import spacy

    return spacy.load(SPACY_MODEL)


class _Progress:
    def __init__(self, callback: ProgressCallback | None):
        self.callback = callback
        self.done = 0.0  # share of the work finished in earlier steps
        # Adding decimal shares gives tiny rounding errors (0.98999997 vs 0.99),
        # so never report less than before: a progress bar must not go backwards
        self.highest = 0.0

    def step(self, name: str) -> Callable[[int, int], None]:
        """Start a step; returns a (done, total) callback for that step."""
        start, share = self.done, STEPS[name]
        self.done += share

        def report(done: int, total: int) -> None:
            self.highest = max(self.highest, min(start + share * done / max(total, 1), 1.0))
            if self.callback:
                self.callback(name, self.highest)

        report(0, 1)
        return report


def analyze(
    data: bytes,
    progress: ProgressCallback | None = None,
    use_coref: bool = True,
    filename: str | None = None,
    use_emotions: bool = True,
    use_themes: bool = True,
) -> BookAnalysis:
    """Analyze an uploaded book file. Takes a few minutes for a full novel.
    The filename is only used as the title when the book doesn't name itself."""
    tracker = _Progress(progress)
    timings: dict[str, float] = {}

    def timed(name: str, started: float) -> None:
        timings[name] = round(time.time() - started, 1)

    started = time.time()
    report = tracker.step("Reading sentences")
    text = load_text(data)
    nlp = load_spacy()
    sentences, chapters = split_sentences(text, nlp, report)
    del nlp  # free the memory before the next model loads
    gc.collect()
    if not sentences:
        raise ValueError("No story text found in this file.")
    timed("Reading sentences", started)

    started = time.time()
    tracker.step("Finding characters")
    characters, mentions, entities = find_characters(sentences, text)
    timed("Finding characters", started)

    started = time.time()
    report = tracker.step("Linking pronouns")
    if use_coref and characters:
        model = coref.load_model()
        mentions += coref.resolve(text, sentences, characters, mentions, model, report)
        del model
        gc.collect()
    timed("Linking pronouns", started)
    for c in characters:
        c.mentions = 0
    for m in mentions:
        characters[m.character_id].mentions += 1

    started = time.time()
    report = tracker.step("Scoring sentiment")
    classify = sentiment.load_model()
    sentiment.score_sentences(sentences, classify, report)
    del classify
    gc.collect()
    timed("Scoring sentiment", started)

    started = time.time()
    report = tracker.step("Detecting emotions")
    if use_emotions:
        classify = emotions.load_model()
        emotions.detect_emotions(sentences, classify, report)
        del classify
        gc.collect()
    timed("Detecting emotions", started)

    started = time.time()
    report = tracker.step("Naming chapters")
    embed = chapter_events.load_model() if use_themes else None
    events = chapter_events.name_chapters(sentences, characters, len(chapters), embed, report)
    del embed
    gc.collect()
    timed("Naming chapters", started)

    started = time.time()
    tracker.step("Finding relationships")
    n_chars, n_chapters = len(characters), len(chapters)
    relationships = find_relationships(sentences, mentions, n_chapters)
    analysis = BookAnalysis(
        chapters=chapters,
        sentences=sentences,
        characters=characters,
        mentions=mentions,
        entities=entities,
        relationships=relationships,
        chapter_sentiment=chapter_sentiment(sentences, n_chapters),
        mentions_by_chapter=mentions_by_chapter(mentions, sentences, n_chars, n_chapters),
        sentiment_by_chapter=sentiment_by_chapter(mentions, sentences, n_chars, n_chapters),
        timings=timings,
        chapter_emotions=chapter_emotions(sentences, n_chapters),
        character_emotions=emotions_by_character(mentions, sentences, n_chars),
        chapter_fine=chapter_emotions(sentences, n_chapters, "fine"),
        character_fine=emotions_by_character(mentions, sentences, n_chars, "fine"),
        chapter_events=events,
    )
    analysis.title, analysis.author = book_info(data, filename)
    timed("Finding relationships", started)
    if progress:
        progress("Done", 1.0)
    return analysis
