"""Search the book: where a word or phrase appears, chapter by chapter (instant, no model)."""

import re

from .models import Sentence


def pattern(query: str) -> re.Pattern | None:
    """A whole-word, case-insensitive pattern for a word or phrase. "letter" also finds "letters" and
    "letter's" but not "lettered"; spaces in a phrase match any run of spaces. None for an empty query."""
    words = [re.escape(w) for w in query.split()]
    if not words:
        return None
    return re.compile(r"\b" + r"\s+".join(words) + r"(?:s|es|'s|’s)?\b", re.IGNORECASE)


def find(sentences: list[Sentence], query: str) -> list[Sentence]:
    """The sentences that contain the word or phrase, in book order."""
    found = pattern(query)
    return [s for s in sentences if found.search(s.text)] if found else []


def by_chapter(matches: list[Sentence], num_chapters: int) -> tuple[list[int], list[float | None]]:
    """([chapter] -> how many sentences contain it, [chapter] -> their average tone, or None)."""
    counts, tones = [0] * num_chapters, [[] for _ in range(num_chapters)]
    for s in matches:
        counts[s.chapter] += 1
        tones[s.chapter].append(s.sentiment)
    return counts, [sum(t) / len(t) if t else None for t in tones]
