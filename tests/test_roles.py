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


def test_a_first_person_narrator_is_found_from_who_names_them():
    from analyzer.dialogue import Line
    from analyzer.models import Chapter, Mention, Sentence
    from analyzer.narration import narrator
    # narration in "I"; Pip is named only inside quotes, Joe also in the narration
    text, sentences, mentions, lines = "", [], [], []
    for i in range(30):
        quote = '"Well, Pip," said Joe.'
        narration = "I went home and Joe followed me."
        for chunk in (quote, narration):
            start = len(text)
            sentences.append(Sentence(len(sentences), chunk, start, start + len(chunk), i % 3))
            text += chunk + " "
        q = sentences[-2]
        lines.append(Line(q.start + 1, q.start + 11, "Well, Pip,", q.chapter, i, q.index, q.index))
        mentions += [Mention(0, q.index, q.start + 7, q.start + 10, "Pip"), Mention(1, q.index, q.start + 17, q.start + 20, "Joe"),
                     Mention(1, q.index + 1, sentences[-1].start + 17, sentences[-1].start + 20, "Joe")]
    book = BookAnalysis(chapters=[Chapter(i, f"Chapter {i + 1}", 0) for i in range(3)], sentences=sentences,
                        characters=[Character(0, "Pip", ["Pip"], 30), Character(1, "Joe", ["Joe"], 60)],
                        mentions=mentions, entities=[], relationships=[], chapter_sentiment=[0.0] * 3,
                        mentions_by_chapter=[], sentiment_by_chapter=[[0.0] * 3, [0.0] * 3])
    assert narrator(book, lines) == 0
    assert story_roles(book, narrator=0)[0][0] == "Narrator"
