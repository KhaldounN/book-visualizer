"""How the story changes from chapter to chapter."""

from .models import Mention, Sentence
from .relationships import characters_per_sentence


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def chapter_sentiment(sentences: list[Sentence], num_chapters: int) -> list[float]:
    """Average sentiment of all sentences in each chapter."""
    by_chapter: list[list[float]] = [[] for _ in range(num_chapters)]
    for s in sentences:
        by_chapter[s.chapter].append(s.sentiment)
    return [_average(values) or 0.0 for values in by_chapter]


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
