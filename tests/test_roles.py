"""The part each character plays, read from the analysis."""

from analyzer.models import BookAnalysis, Character, Relationship
from analyzer.roles import story_roles, surname


def test_roles_come_from_the_numbers():
    people = [Character(0, "Elizabeth", ["Elizabeth", "Elizabeth Bennet"], 900),
              Character(1, "Mr. Darcy", ["Mr. Darcy", "Darcy"], 600),
              Character(2, "Jane", ["Jane", "Jane Bennet"], 400),
              Character(3, "Wickham", ["Wickham"], 300)]
    links = [Relationship(0, 1, 400, 0.05), Relationship(0, 2, 200, 0.10), Relationship(0, 3, 150, -0.20)]
    book = BookAnalysis(chapters=[], sentences=[], characters=people, mentions=[], entities=[], relationships=links,
                        chapter_sentiment=[], mentions_by_chapter=[],
                        sentiment_by_chapter=[[0.0] * 6, [-0.2, -0.2, 0, 0, 0.2, 0.2], [0.1] * 6, [0.0] * 6])
    roles = story_roles(book)
    assert roles[0] == ["Main character", "Bennet family"]
    assert roles[1] == ["Closest to Elizabeth", "Ends happier"]
    assert roles[2] == ["Bennet family"]
    assert roles[3] == ["Darker scenes with Elizabeth"]
    assert surname(people[1]) == "Darcy" and surname(people[3]) is None
