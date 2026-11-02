"""Reading characters' looks from the book, and drawing their avatars."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from analyzer.appearance import book_world, describe
from analyzer.models import BookAnalysis, Chapter, Character, Mention, Sentence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import avatars  # noqa: E402


def tiny_book(lines: list[tuple[int, int, str]], characters: list[Character]) -> BookAnalysis:
    """lines: (chapter, character id or -1, text). Each line mentions that one character."""
    sentences, mentions = [], []
    for i, (chapter, who, text) in enumerate(lines):
        sentences.append(Sentence(i, text, 0, 0, chapter, sentiment=0.1))
        if who >= 0:
            word = text.split()[0]
            mentions.append(Mention(who, i, 0, 0, word, "coref" if word.lower() in ("he", "she") else "name"))
    chapters = [Chapter(i, f"Chapter {i + 1}", 0) for i in range(4)]
    for c in characters:
        c.mentions = sum(m.character_id == c.id for m in mentions)
    return BookAnalysis(chapters=chapters, sentences=sentences, characters=characters, mentions=mentions,
                        entities=[], relationships=[], chapter_sentiment=[0.0] * 4,
                        mentions_by_chapter=[[0] * 4 for _ in characters],
                        sentiment_by_chapter=[[0.2, None, None, None] for _ in characters])


def great_expectations_in_miniature() -> BookAnalysis:
    people = [Character(0, "Joe", ["Joe", "Mrs. Joe", "Joe Gargery"]),
              Character(1, "Miss Havisham", ["Miss Havisham", "Havisham"]),
              Character(2, "Herbert", ["Herbert"])]
    lines = [
        # Joe: a blacksmith across three chapters, but "Mrs. Joe" (his sister) is mixed into his
        # names and her "she" into his pronouns, like in the real analysis
        (0, 0, "Joe worked at the forge as the village blacksmith."),
        (1, 0, "Joe the blacksmith hammered all day."),
        (2, 0, "Joe went back to his forge."),
        (0, 0, "She scolded everyone, as usual."),
        (1, 0, "She was cross again."),
        (0, 0, "Joe had fair hair and blue eyes."),
        (2, 0, "Joe pushed back his fair hair."),
        # Miss Havisham: a bride with grey hair
        (0, 1, "Miss Havisham sat in her bridal dress."),
        (1, 1, "Miss Havisham wore her veil as always."),
        (1, 1, "Miss Havisham touched her grey hair."),
        (2, 1, "Miss Havisham, with grey hair loose, stared at the clock."),
        # Herbert: nothing at all
        (3, 2, "Herbert laughed."),
        (3, -1, "It rained on the marshes."),
        # scenes where soldiers appear around several people at once don't make anyone a soldier
        (3, -1, "The soldiers came to the forge."),
    ]
    return tiny_book(lines, people)


def test_the_book_describes_its_characters():
    looks = describe(great_expectations_in_miniature())
    joe, havisham, herbert = looks[0], looks[1], looks[2]
    assert (joe.role, joe.hair, joe.gender) == ("blacksmith", "fair", "m"), "his job decides, not 'Mrs. Joe'"
    assert havisham.features == {"bride"} and havisham.hair == "grey" and havisham.age == "old"
    assert havisham.gender == "f"
    assert herbert.evidence == [] and herbert.role is None, "nothing in the book: the drawing improvises"
    assert any("blacksmith" in e for e in joe.evidence) and any("bride" in e for e in havisham.evidence)


def test_a_job_mentioned_in_one_chapter_only_doesnt_count():
    people = [Character(0, "Mr. Wopsle", ["Mr. Wopsle"])]
    lines = [(1, 0, "Mr. Wopsle played the king."), (1, 0, "Mr. Wopsle, as the king, bowed."),
             (0, 0, "Mr. Wopsle read aloud.")]
    look = describe(tiny_book(lines, people))[0]
    assert look.role is None and look.gender == "m"


def test_the_books_world_sets_the_clothes():
    people = [Character(0, "Frodo", ["Frodo"])]
    fantasy = [(0, 0, "Frodo the hobbit met the elves and a wizard near the dwarf halls.")] * 3
    assert book_world(tiny_book(fantasy, people)) == "fantasy"
    assert book_world(great_expectations_in_miniature()) == "period"


def test_avatars_are_valid_pictures_and_always_the_same():
    book = great_expectations_in_miniature()
    looks = describe(book)
    svg = avatars.avatar_svg("Joe", looks[0], "#2a78d6")
    ET.fromstring(svg)  # well-formed SVG
    assert svg == avatars.avatar_svg("Joe", looks[0], "#2a78d6"), "the same character always looks the same"
    # what the book doesn't say (skin, hair, coat, hat) varies with the name, so a cast looks varied
    unknown = looks[2]
    drawn = {avatars.avatar_svg(f"Character {i}", unknown, "#2a78d6") for i in range(20)}
    assert len(drawn) >= 10, f"only {len(drawn)} different looks for 20 characters"
    assert 'stroke="#2a78d6"' in svg, "the ring is the character's colour"
    assert "opacity=\".55\"" in avatars.avatar_svg("Miss Havisham", looks[1], "#eb6834"), "the bride wears a veil"
    assert avatars.avatar_uri("Joe", looks[0], "#2a78d6").startswith("data:image/svg+xml;base64,")
    assert avatars.look_in_words(looks[0]) == "Blacksmith · fair hair"
    assert avatars.look_in_words(looks[2]) == "Period figure", "nothing in the book (not even his gender): the assumed look"
