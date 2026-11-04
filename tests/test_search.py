"""Searching the book for a word or phrase."""

from analyzer.models import Sentence
from analyzer.search import by_chapter, find


def test_whole_words_and_phrases_are_found_per_chapter():
    sentences = [Sentence(0, "A letter came.", 0, 0, 0, sentiment=0.2), Sentence(1, "Two letters!", 0, 0, 0, sentiment=0.4),
                 Sentence(2, "She lettered the sign.", 0, 0, 1), Sentence(3, "The LETTER'S seal broke.", 0, 0, 1, sentiment=-0.5),
                 Sentence(4, "Pride and  prejudice.", 0, 0, 1)]
    found = find(sentences, "letter")
    assert [s.index for s in found] == [0, 1, 3]  # letters and letter's, not lettered
    counts, tones = by_chapter(found, 2)
    assert counts == [2, 1] and round(tones[0], 2) == 0.3 and tones[1] == -0.5
    assert [s.index for s in find(sentences, "pride and prejudice")] == [4]
    assert find(sentences, "   ") == []
