"""Search the book: where a word or phrase appears, chapter by chapter (instant, no model)."""

import re
from collections import Counter

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


def place_journey(entities: list, num_chapters: int, characters: list | None = None,
                  sentences: list[Sentence] | None = None, stretches: int = 6) -> list[tuple[str, int, int]]:
    """The story's route: the book cut into `stretches` equal parts, each named by its most
    characteristic place (mentioned there often, and mostly there rather than everywhere).
    Neighbouring parts with the same place are joined. [(place, first chapter, last chapter)]
    A "place" that shares a word with a character's names is left out: "the Scarecrow" and
    Herbert Pocket are people the name finder took for places."""
    person_words = {w.strip(".,").lower() for c in characters or [] for a in c.aliases for w in a.split()}
    # a one-word "place" the book also writes in lowercase is an ordinary word (the Lion, the Times)
    lowercase = Counter(w for s in sentences or [] for w in re.findall(r"\b[a-z]+\b", s.text))
    places = [e for e in entities if e.kind == "place" and e.chapter_counts and e.count >= 3
              and not {w.strip(".,").lower() for w in e.name.split()} & person_words
              and not (" " not in e.name and lowercase[e.name.lower()] >= 2)]
    # places don't speak: "said the Scarecrow", "the Lion said" make it a person
    text = " ".join(s.text for s in sentences or [])
    places = [e for e in places if len(re.findall(rf"\bsaid (?:the )?{re.escape(e.name)}\b|\b{re.escape(e.name)} said\b",
                                                  text)) < 2]
    if not places or num_chapters < stretches:
        return []
    route: list[tuple[str, int, int]] = []
    for k in range(stretches):
        a, b = k * num_chapters // stretches, (k + 1) * num_chapters // stretches
        scored = [(sum(e.chapter_counts[a:b]) ** 2 / e.count, e.name) for e in places if sum(e.chapter_counts[a:b]) >= 2]
        if not scored:
            continue
        name = max(scored)[1]
        if route and route[-1][0] == name:
            route[-1] = (name, route[-1][1], b - 1)
        else:
            route.append((name, a, b - 1))
    return route
