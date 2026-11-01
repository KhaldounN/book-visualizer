"""Run every analysis step in order and collect the results.

The AI models are loaded one at a time and released after use, so the
whole analysis fits in about 2 GB of memory.
"""

import gc
import time
from typing import Callable

from . import coref, sentiment
from .characters import find_characters
from .loaders import book_info, load_text
from .models import BookAnalysis
from .progression import chapter_sentiment, mentions_by_chapter, sentiment_by_chapter
from .relationships import find_relationships
from .segment import split_sentences

SPACY_MODEL = "en_core_web_lg"

# Bump this whenever BookAnalysis changes shape or the analysis changes, so
# results saved by an older version are re-analyzed instead of loaded
ANALYSIS_VERSION = 2

# (step name, share of the total time) measured on Pride and Prejudice;
# used to turn each step's own progress into one overall progress bar
STEPS = {
    "Reading sentences": 0.05,
    "Finding characters": 0.01,
    "Linking pronouns": 0.30,
    "Scoring sentiment": 0.62,
    "Finding relationships": 0.02,
}

ProgressCallback = Callable[[str, float], None]  # (step name, overall 0..1)


def load_spacy():
    import spacy

    return spacy.load(SPACY_MODEL)


class _Progress:
    def __init__(self, callback: ProgressCallback | None):
        self.callback = callback
        self.done = 0.0  # share of the work finished in earlier steps

    def step(self, name: str) -> Callable[[int, int], None]:
        """Start a step; returns a (done, total) callback for that step."""
        start, share = self.done, STEPS[name]
        self.done += share

        def report(done: int, total: int) -> None:
            if self.callback:
                self.callback(name, start + share * done / max(total, 1))

        report(0, 1)
        return report


def analyze(
    data: bytes,
    progress: ProgressCallback | None = None,
    use_coref: bool = True,
    filename: str | None = None,
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
    )
    analysis.title, analysis.author = book_info(data, filename)
    timed("Finding relationships", started)
    if progress:
        progress("Done", 1.0)
    return analysis
