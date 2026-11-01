from analyzer.merge import merge_characters
from analyzer.models import BookAnalysis, Chapter, Character, Mention, Sentence


def make_analysis():
    # Elizabeth (id 0), Darcy (id 1), Lizzy (id 2) - Lizzy is Elizabeth's nickname
    sentences = [Sentence(i, f"s{i}", 0, 0, 0, sentiment=0.5) for i in range(8)]
    who = [[0, 1], [], [2, 1], [], [2, 1], [], [0], [2]]
    mentions = [Mention(c, i, 0, 0, "x") for i, ids in enumerate(who) for c in ids]
    characters = [
        Character(0, "Elizabeth", ["Elizabeth"], 2),
        Character(1, "Mr. Darcy", ["Mr. Darcy", "Darcy"], 3),
        Character(2, "Lizzy", ["Lizzy"], 3),
    ]
    return BookAnalysis(
        chapters=[Chapter(0, "Chapter 1", 0)], sentences=sentences, characters=characters,
        mentions=mentions, entities=[], relationships=[], chapter_sentiment=[0.5],
        mentions_by_chapter=[], sentiment_by_chapter=[],
    )


def test_merge_combines_mentions_and_aliases():
    merged = merge_characters(make_analysis(), [("Lizzy", "Elizabeth")])
    assert [(c.id, c.name, c.mentions) for c in merged.characters] == [(0, "Elizabeth", 5), (1, "Mr. Darcy", 3)]
    assert merged.characters[0].aliases == ["Elizabeth", "Lizzy"]
    assert merged.mentions_by_chapter == [[5], [3]]


def test_merge_updates_relationships():
    # apart, neither Elizabeth nor Lizzy meets Darcy 3 times; together they do
    assert merge_characters(make_analysis(), []).relationships == []
    merged = merge_characters(make_analysis(), [("Lizzy", "Elizabeth")])
    assert [(r.source, r.target, r.count) for r in merged.relationships] == [(0, 1, 3)]


def test_ids_are_renumbered_by_mentions():
    merged = merge_characters(make_analysis(), [("Elizabeth", "Lizzy")])
    assert [(c.id, c.name) for c in merged.characters] == [(0, "Lizzy"), (1, "Mr. Darcy")]
    assert {m.character_id for m in merged.mentions} == {0, 1}


def test_chained_and_unknown_merges():
    analysis = make_analysis()
    merged = merge_characters(analysis, [("Lizzy", "Mr. Darcy"), ("Mr. Darcy", "Elizabeth"), ("Nobody", "Elizabeth")])
    assert [c.name for c in merged.characters] == ["Elizabeth"]
    assert merged.characters[0].mentions == len(analysis.mentions)
    assert analysis.characters[2].name == "Lizzy", "the original analysis is not changed"
