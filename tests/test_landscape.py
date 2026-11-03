from analyzer.landscape import LABELS, LANDSCAPES, chapter_landscapes
from analyzer.models import Sentence


def book(*chapters):
    """One sentence per chapter text (plus filler so the clue density is realistic)."""
    filler = " ".join(["word"] * 40)
    return [Sentence(i, f"{text} {filler}", 0, 0, i) for i, text in enumerate(chapters)]


def test_every_landscape_has_a_label():
    assert set(LABELS) == set(LANDSCAPES)


def test_clue_words_choose_the_landscape():
    land = chapter_landscapes(book(
        "They walked under the oak trees deep into the forest, through the woods.",
        "A dusty street in the town, past the shops and the market square.",
        "The waves broke on the shore as the ship left the harbour for the open sea.",
    ), 3, smooth=0)
    assert [l["kind"] for l in land] == ["forest", "town", "water"]
    assert land[0]["sure"] and set(land[0]["clues"]) <= {"oak", "tree", "forest", "woods"}


def test_plurals_count():
    land = chapter_landscapes(book("Mountains and peaks and cliffs all around."), 1)
    assert land[0]["kind"] == "mountains" and set(land[0]["clues"]) == {"mountain", "peak", "cliff"}


def test_a_chapter_without_clues_keeps_the_landscape_before_it():
    land = chapter_landscapes(book(
        "Snow and ice and frost on the frozen glacier.",
        "She said nothing for a long time.",
        "He answered her at last.",
    ), 3, smooth=0)
    assert [l["kind"] for l in land] == ["snow", "snow", "snow"]
    assert [l["sure"] for l in land] == [True, False, False]


def test_the_first_chapters_take_the_first_landscape_found():
    land = chapter_landscapes(book("Nothing here.", "The desert sand and the dunes, a camel."), 2, smooth=0)
    assert [l["kind"] for l in land] == ["desert", "desert"]


def test_a_book_without_clues_is_countryside():
    land = chapter_landscapes(book("Nothing.", "Still nothing."), 2)
    assert {l["kind"] for l in land} == {"countryside"}
    assert chapter_landscapes([], 0) == []


def test_one_stray_word_is_not_enough():
    land = chapter_landscapes(book("The sea.", "The town and the street and the shop and the market."), 2, smooth=0)
    assert land[0]["kind"] == "town" and not land[0]["sure"]  # one clue only: it takes the next chapter's
