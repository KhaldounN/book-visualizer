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


def test_the_route_names_each_stretch_by_its_place_and_skips_people():
    from analyzer.models import Character, EntityCount
    from analyzer.search import place_journey
    places = [EntityCount("Netherfield", "GPE", 12, "place", [3, 3, 3, 0, 0, 0]),
              EntityCount("Pemberley", "GPE", 12, "place", [0, 0, 0, 4, 4, 4]),
              EntityCount("Lion", "ORG", 30, "place", [5] * 6),  # "said the Lion": a person
              EntityCount("Darcy", "GPE", 30, "place", [5] * 6)]  # a character's name
    talk = [Sentence(i, "said the Lion loudly.", 0, 0, 0) for i in range(3)]
    route = place_journey(places, 6, [Character(0, "Mr. Darcy", ["Mr. Darcy"])], talk, stretches=2)
    assert route == [("Netherfield", 0, 2), ("Pemberley", 3, 5)]
