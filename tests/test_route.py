from analyzer.models import Sentence
from analyzer.route import LABELS, ROUTES, chapter_routes


def book(*chapters):
    filler = " ".join(["word"] * 40)
    return [Sentence(i, f"{text} {filler}", 0, 0, i) for i, text in enumerate(chapters)]


def test_every_road_shape_has_a_label():
    assert set(LABELS) == set(ROUTES)


def test_travel_words_choose_the_road_shape():
    road = chapter_routes(book(
        "They drove down the long avenue to the highway.",
        "A winding path, twisting between the rocks, then a maze of lanes.",
        "We climbed the steep slope; the climbing took hours.",
        "They talked by the fire.",
    ), 4)
    assert [r and r["kind"] for r in road] == ["straight", "winding", "steep", None]
    assert set(road[2]["clues"]) == {"climb", "steep"}  # "climbed", "climbing" count as "climb"


def test_one_passing_word_is_not_enough():
    assert chapter_routes(book("Her thoughts would wander."), 1) == [None]
    assert chapter_routes([], 0) == []
