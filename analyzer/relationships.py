"""Which characters appear together, and what the tone is when they do.

Two characters "appear together" when both are mentioned in the same
sentence or in neighbouring sentences of the same chapter. This measures
the mood of the scenes they share, not exactly how they feel about each
other: a happy sentence about a ball counts as positive for everyone in it.
"""

from collections import defaultdict
from itertools import combinations

from .models import Mention, Relationship, Sentence

WINDOW = 2  # sentences: this one and the next
MIN_TOGETHER = 3  # fewer shared moments than this is likely chance


def characters_per_sentence(sentences: list[Sentence], mentions: list[Mention]) -> list[set[int]]:
    present: list[set[int]] = [set() for _ in sentences]
    for m in mentions:
        present[m.sentence_index].add(m.character_id)
    return present


def find_relationships(
    sentences: list[Sentence], mentions: list[Mention], num_chapters: int
) -> list[Relationship]:
    """Relationships between characters, strongest first."""
    present = characters_per_sentence(sentences, mentions)
    # pair -> [chapter] -> number of shared moments / sum of their tone
    count: dict[tuple[int, int], list[int]] = defaultdict(lambda: [0] * num_chapters)
    tone: dict[tuple[int, int], list[float]] = defaultdict(lambda: [0.0] * num_chapters)

    for i, sentence in enumerate(sentences):
        if not present[i]:
            continue
        window = [
            j for j in range(i, min(i + WINDOW, len(sentences)))
            if sentences[j].chapter == sentence.chapter
        ]
        together = set().union(*(present[j] for j in window))
        mood = sum(sentences[j].sentiment for j in window) / len(window)
        for pair in combinations(sorted(together), 2):
            # Count each pair only at the first sentence of their shared
            # moment, so a pair in one sentence is not counted twice
            if pair[0] in present[i] or pair[1] in present[i]:
                count[pair][sentence.chapter] += 1
                tone[pair][sentence.chapter] += mood

    relationships = []
    for (a, b), counts in count.items():
        total = sum(counts)
        if total < MIN_TOGETHER:
            continue
        relationships.append(
            Relationship(
                source=a,
                target=b,
                count=total,
                sentiment=sum(tone[(a, b)]) / total,
                chapter_counts=counts,
                chapter_sentiment=[t / n if n else None for t, n in zip(tone[(a, b)], counts)],
            )
        )
    return sorted(relationships, key=lambda r: -r.count)
