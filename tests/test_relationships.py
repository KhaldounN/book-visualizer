import pytest

from analyzer.models import Mention, Sentence
from analyzer.progression import (
    chapter_emotions,
    chapter_sentiment,
    emotions_by_character,
    mentions_by_chapter,
    sentiment_by_chapter,
)
from analyzer.relationships import find_relationships

ANNA, TOM, EVE = 0, 1, 2


def story(*rows):
    """rows of (chapter, sentiment, [character ids mentioned])"""
    sentences = [Sentence(i, f"s{i}", 0, 0, chapter, sentiment=tone) for i, (chapter, tone, _) in enumerate(rows)]
    mentions = [Mention(c, i, 0, 0, "x") for i, (_, _, ids) in enumerate(rows) for c in ids]
    return sentences, mentions


def pairs(relationships):
    return {(r.source, r.target): r for r in relationships}


def test_same_or_neighbouring_sentences_count_once_each():
    sentences, mentions = story(
        (0, 0.5, [ANNA, TOM]),  # together in one sentence
        (0, 0.0, []),
        (0, 0.1, [ANNA]),       # neighbouring sentences
        (0, 0.3, [TOM]),
        (0, 0.0, []),
        (0, -0.4, [ANNA, TOM, TOM]),  # two mentions of Tom still count once
    )
    result = pairs(find_relationships(sentences, mentions, num_chapters=1))
    assert result[(ANNA, TOM)].count == 3


def test_tone_is_the_average_of_the_shared_moments():
    sentences, mentions = story(
        (0, 0.8, [ANNA, TOM]), (0, 0.0, []), (0, -0.2, [ANNA, TOM]), (0, 0.0, []), (0, 0.6, [ANNA, TOM]),
    )
    # each moment's tone averages the sentence and the next one (0.4, -0.1, 0.6)
    assert pairs(find_relationships(sentences, mentions, 1))[(ANNA, TOM)].sentiment == pytest.approx(0.3)


def test_chapter_break_separates_neighbours():
    # Anna and Tom in neighbouring sentences 3 times: together within a chapter...
    sentences, mentions = story(*[(0, 0, [ANNA]), (0, 0, [TOM]), (0, 0, [])] * 3)
    assert len(find_relationships(sentences, mentions, 1)) == 1
    # ...but not when each pair of sentences is split by a chapter break
    sentences, mentions = story(*[(c, 0, [ANNA] if c % 2 == 0 else [TOM]) for c in range(6)])
    assert find_relationships(sentences, mentions, 6) == []


def test_rare_pairs_are_dropped_and_strongest_come_first():
    sentences, mentions = story(
        *[(0, 0.0, [ANNA, TOM]), (0, 0.0, [])] * 4, (0, 0.0, [ANNA, EVE]), (0, 0, []),
        *[(0, 0.0, [TOM, EVE]), (0, 0.0, [])] * 3,
    )
    result = find_relationships(sentences, mentions, 1)
    assert [(r.source, r.target, r.count) for r in result] == [(ANNA, TOM, 4), (TOM, EVE, 3)]


def test_relationship_change_per_chapter():
    sentences, mentions = story(
        *[(0, -0.5, [ANNA, TOM]), (0, -0.5, [])] * 3,
        *[(1, 0.7, [ANNA, TOM]), (1, 0.7, [])] * 3,
    )
    r = pairs(find_relationships(sentences, mentions, 3))[(ANNA, TOM)]
    assert r.chapter_counts == [3, 3, 0]
    assert r.chapter_sentiment[0] == pytest.approx(-0.5)
    assert r.chapter_sentiment[1] == pytest.approx(0.7)
    assert r.chapter_sentiment[2] is None


def feel(sentences, *mixes):
    for s, mix in zip(sentences, mixes):
        s.emotions = mix
    return sentences


ANGRY = {"anger": 0.8, "joy": 0.0, "neutral": 0.2}
HAPPY = {"anger": 0.0, "joy": 0.9, "neutral": 0.1}


def test_relationship_emotions_show_the_arc_across_the_book():
    # chapters 0..2 = early, middle, late: angry early, happy late
    sentences, mentions = story(*[(c, 0, [ANNA, TOM]) for c in (0, 0, 0, 1, 2, 2, 2)])
    feel(sentences, ANGRY, ANGRY, ANGRY, {}, HAPPY, HAPPY, HAPPY)
    r = pairs(find_relationships(sentences, mentions, num_chapters=3))[(ANNA, TOM)]
    early, middle, late = r.emotions_by_part
    assert early["anger"] == pytest.approx(0.8) and late["joy"] == pytest.approx(0.9)
    assert middle == {}  # no emotions were detected there
    assert r.emotions["anger"] == pytest.approx(0.4)  # half angry, half happy overall


def test_emotions_per_chapter_and_character():
    sentences, mentions = story((0, 0, [ANNA]), (0, 0, [ANNA, TOM]), (1, 0, [TOM]))
    feel(sentences, ANGRY, HAPPY, HAPPY)
    assert chapter_emotions(sentences, 2)[1]["joy"] == pytest.approx(0.9)
    by_character = emotions_by_character(mentions, sentences, 3)
    assert by_character[ANNA]["anger"] == pytest.approx(0.4)
    assert by_character[TOM]["joy"] == pytest.approx(0.9)
    assert by_character[EVE] == {}  # never mentioned


def test_progression_per_chapter_and_character():
    sentences, mentions = story(
        (0, 0.4, [ANNA]), (0, -0.2, [ANNA, TOM]), (1, 0.6, [TOM, TOM]),
    )
    assert chapter_sentiment(sentences, 2) == pytest.approx([0.1, 0.6])
    assert mentions_by_chapter(mentions, sentences, 2, 2) == [[2, 0], [1, 2]]
    by_chapter = sentiment_by_chapter(mentions, sentences, 2, 2)
    assert by_chapter[ANNA] == [pytest.approx(0.1), None]
    assert by_chapter[TOM] == [pytest.approx(-0.2), pytest.approx(0.6)]
