"""Pace and difficulty: how a book reads, chapter by chapter.

Simple counts, no model, computed at render time from the saved sentences:
- reading time (words at an average adult reading speed),
- sentence length (words per sentence),
- reading level: the Flesch-Kincaid grade, the US school year a reader needs
  (from sentence length and syllables per word),
- vocabulary richness: the share of different words in every stretch of 100 words
  (the "moving-average type-token ratio"; a plain ratio would fall as chapters get longer),
- dialogue: the share of the words spoken inside quotes (from analyzer/dialogue.py),
- action vs. description: verbs against adjectives, from the word types spaCy tagged while
  reading the book (`Sentence.tags`; missing for books analysed before it was stored).
"""

import re
from functools import lru_cache
from dataclasses import dataclass

from .models import Sentence

WORDS_PER_MINUTE = 230  # an average adult reading fiction silently
WINDOW = 100  # words per stretch for vocabulary richness
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


@dataclass
class Pace:
    words: int
    minutes: float
    sentence_length: float  # average words per sentence
    grade: float  # Flesch-Kincaid grade level
    richness: float  # 0..1, share of different words per 100
    dialogue: float  # 0..1, share of words inside quotes
    action: float | None  # 0..1, verbs / (verbs + adjectives); None without word types


_VOWELS = re.compile(r"[aeiouy]+")


def syllables(word: str) -> int:
    """Syllables in a word, estimated from its groups of vowels ("reading" 2, "made" 1)."""
    return _syllables(word.lower())


@lru_cache(maxsize=200_000)  # a novel uses the same few thousand words over and over: count each once
def _syllables(word: str) -> int:
    count = len(_VOWELS.findall(word))
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1  # a silent final e
    return max(count, 1)


def richness(words: list[str], window: int = WINDOW) -> float:
    """Average share of different words in every stretch of `window` words."""
    if len(words) <= window:
        return len(set(words)) / len(words) if words else 0.0
    # slide the window one word at a time, keeping word counts up to date
    counts: dict[str, int] = {}
    for w in words[:window]:
        counts[w] = counts.get(w, 0) + 1
    total = len(counts)
    for i in range(window, len(words)):
        old, new = words[i - window], words[i]
        counts[old] -= 1
        if not counts[old]:
            del counts[old]
        counts[new] = counts.get(new, 0) + 1
        total += len(counts)
    return total / (len(words) - window + 1) / window


def measure(sentences: list[Sentence], dialogue: float = 0.0) -> Pace:
    """The pace of a run of sentences (a chapter, or the whole book)."""
    words = [w.lower() for s in sentences for w in _WORD.findall(s.text)]
    n = max(len(words), 1)
    per_sentence = n / max(len(sentences), 1)
    per_word = sum(syllables(w) for w in words) / n
    tagged = [s.tags for s in sentences if getattr(s, "tags", None) is not None]
    verbs = sum(t.get("VERB", 0) for t in tagged)
    adjectives = sum(t.get("ADJ", 0) for t in tagged)
    return Pace(
        words=len(words),
        minutes=len(words) / WORDS_PER_MINUTE,
        sentence_length=per_sentence,
        grade=0.39 * per_sentence + 11.8 * per_word - 15.59,
        richness=richness(words),
        dialogue=dialogue,
        action=verbs / (verbs + adjectives) if tagged and verbs + adjectives else None,
    )


def chapter_pace(sentences: list[Sentence], num_chapters: int, dialogue: list[float] | None = None) -> list[Pace]:
    """[chapter] -> its Pace. `dialogue` is each chapter's share of spoken words."""
    by_chapter: list[list[Sentence]] = [[] for _ in range(num_chapters)]
    for s in sentences:
        by_chapter[s.chapter].append(s)
    return [measure(group, dialogue[i] if dialogue else 0.0) for i, group in enumerate(by_chapter)]


def grade_label(grade: float) -> str:
    """Plain words for a Flesch-Kincaid grade."""
    for limit, label in ((6, "very easy"), (8, "easy"), (10, "average"), (12, "fairly hard"), (15, "hard")):
        if grade < limit:
            return label
    return "very hard"


def _z(values: list[float]) -> list[float]:
    mean = sum(values) / len(values)
    spread = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
    return [(v - mean) / spread if spread > 1e-9 else 0.0 for v in values]


def pace_scores(chapters: list[Pace]) -> list[float]:
    """[chapter] -> how fast it reads compared with the rest of the book (0 = the book's usual
    pace, above 0 faster). Fast = short sentences, more dialogue, more verbs than adjectives;
    each counts equally after standardizing. Very short chapters (under 50 words) score 0."""
    real = [i for i, p in enumerate(chapters) if p.words >= 50]
    if len(real) < 2:
        return [0.0] * len(chapters)
    parts = [_z([-chapters[i].sentence_length for i in real]), _z([chapters[i].dialogue for i in real])]
    if all(chapters[i].action is not None for i in real):
        parts.append(_z([chapters[i].action for i in real]))
    scores = [0.0] * len(chapters)
    for k, i in enumerate(real):
        scores[i] = sum(part[k] for part in parts) / len(parts)
    return scores
