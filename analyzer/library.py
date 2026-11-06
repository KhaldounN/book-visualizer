"""The few numbers used to compare a book with the famous books: its mood curve, story shape and pace.

Each famous book's summary is saved next to its analysis (results/v<N>-<sha>.summary.json), by
scripts/analyze_library.py when it analyzes the book, or by the website the first time it needs it.
No AI models here (the website imports this module).
"""

import json
import pickle
from pathlib import Path

from . import dialogue
from .pace import measure
from .progression import WEAK_FIT, story_shape
from .version import ANALYSIS_VERSION


def book_pace(analysis, lines: list):
    """The whole book's pace, with its share of spoken words."""
    pace = measure(analysis.sentences)
    pace.dialogue = min(sum(line.words for line in lines) / max(pace.words, 1), 1.0)
    return pace


def summary(analysis) -> dict:
    """The few numbers used to compare books: mood curve, story shape and pace."""
    curve, fits = story_shape(analysis.sentences)
    pace = book_pace(analysis, dialogue.find_lines(analysis.sentences, analysis.mentions))
    return {"curve": [float(v) for v in curve], "shape": fits[0][0] if fits and fits[0][1] >= WEAK_FIT else None,
            "hours": pace.minutes / 60, "grade": pace.grade, "sentence_length": pace.sentence_length,
            "dialogue": pace.dialogue, "richness": pace.richness}


def saved_summary(results: Path, key: str) -> dict:
    """A famous book's summary: read from its file, or worked out from its saved analysis and saved."""
    analysis_file = results / f"v{ANALYSIS_VERSION}-{key}.pkl"
    summary_file = results / f"v{ANALYSIS_VERSION}-{key}.summary.json"
    if summary_file.exists() and summary_file.stat().st_mtime >= analysis_file.stat().st_mtime:
        try:
            return json.loads(summary_file.read_text(encoding="utf-8"))
        except ValueError:
            pass  # a damaged file: work it out again
    found = summary(pickle.loads(analysis_file.read_bytes()))
    summary_file.write_text(json.dumps(found, default=float), encoding="utf-8")
    return found
