import pytest

from analyzer.models import Sentence
from analyzer.progression import key_moments, rolling_sentiment, story_arc


def book(*tones, chapters=None):
    return [Sentence(i, f"s{i}", 0, 0, chapters[i] if chapters else 0, sentiment=t) for i, t in enumerate(tones)]


def test_rolling_sentiment_averages_the_neighbours():
    sentences = book(0.0, 0.0, 0.9, 0.0, 0.0)
    assert rolling_sentiment(sentences, 1) == pytest.approx([0, 0, 0.9, 0, 0])
    # window 3: each sentence with one neighbour on each side (fewer at the ends)
    assert rolling_sentiment(sentences, 3) == pytest.approx([0, 0.3, 0.3, 0.3, 0])


def test_key_moments_find_the_darkest_and_brightest_passages():
    tones = [0.0] * 30
    tones[5:8] = [-0.9, -0.8, -0.9]  # dark passage
    tones[20:23] = [0.8, 0.9, 0.7]  # bright passage
    dark, bright = key_moments(book(*tones), window=3, n=1)
    assert (dark[0].first, dark[0].last) == (5, 7)
    assert dark[0].score == pytest.approx(-0.8667, abs=1e-3)
    assert (bright[0].first, bright[0].last) == (20, 22)


def test_key_moments_never_overlap():
    tones = [0.0] * 40
    tones[10:16] = [-0.9] * 6  # one long dark stretch, room for two passages
    dark, _ = key_moments(book(*tones), window=3, n=3)
    for a in dark:
        for b in dark:
            assert a is b or a.last < b.first or a.first > b.last
    assert {(m.first, m.last) for m in dark[:2]} == {(10, 12), (13, 15)}


def test_key_moments_stay_inside_one_chapter():
    # the darkest 3 sentences in a row would cross the chapter break
    sentences = book(0, 0, -0.9, -0.9, -0.9, 0, chapters=[0, 0, 0, 1, 1, 1])
    dark, _ = key_moments(sentences, window=3, n=1)
    assert dark[0].chapter == 1 and (dark[0].first, dark[0].last) == (3, 5)


def test_story_arc_finds_the_peak_and_the_dip_and_splits_acts_at_the_dip():
    # rises to a high around chapter 5, falls to a low around chapter 15, recovers
    tones = [0.0, 0.1, 0.2, 0.3, 0.4, 0.3, 0.2, 0.1, 0.0, -0.1, -0.2, -0.3, -0.4, -0.5, -0.6,
             -0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2]
    arc, turning, acts = story_arc(tones, smooth=0, points=2)
    assert arc == tones  # no smoothing
    assert turning == [(4, "high"), (14, "low")]
    assert acts == [(0, 13), (14, 22)]  # every chapter belongs to exactly one act


def test_story_arc_smoothing_and_flat_books():
    arc, turning, acts = story_arc([0.2] * 10, smooth=2)
    assert arc == pytest.approx([0.2] * 10)
    assert acts == [(0, 9)]  # nothing turns: one act


def test_book_shorter_than_the_window_has_no_key_moments():
    assert key_moments(book(0.1, 0.2), window=20) == ([], [])


def test_story_shape_recognizes_each_shape():
    from analyzer.progression import STORY_SHAPES, shape_curve, story_shape
    for name in STORY_SHAPES:
        # a book whose mood follows the shape (stretched to 1,000 sentences, with a mood from -0.5 to +0.5)
        template = shape_curve(name, 1000)
        curve, fits = story_shape(book(*[t - 0.5 for t in template]))
        assert fits[0][0] == name, (name, fits[:2])
        assert fits[0][1] > 0.9 and len(fits) == len(STORY_SHAPES) and len(curve) == 50


def test_story_shape_ignores_level_and_strength_but_not_direction():
    from analyzer.progression import story_shape
    rising = [i / 500 for i in range(500)]
    assert story_shape(book(*[0.3 + t / 10 for t in rising]))[1][0][0] == "Rags to riches"  # a mild, bright book
    assert story_shape(book(*[-t for t in rising]))[1][0][0] == "Tragedy"


def test_story_shape_has_no_answer_for_short_or_flat_books():
    from analyzer.progression import story_shape
    assert story_shape(book(0.1, 0.2)) == ([], [])
    curve, fits = story_shape(book(*[0.2] * 200))
    assert fits == [] and len(curve) == 50


def test_curve_match_compares_shapes_only():
    from analyzer.progression import curve_match
    rising = [0, 1, 2, 3]
    assert abs(curve_match(rising, [10, 20, 30, 40]) - 1) < 1e-9
    assert abs(curve_match(rising, [3, 2, 1, 0]) + 1) < 1e-9
    assert curve_match(rising, [1, 1, 1, 1]) == 0.0 and curve_match(rising, [1, 2]) == 0.0


def test_a_characters_journey_follows_them_stage_by_stage():
    from analyzer.models import Mention
    from analyzer.progression import character_journey, journey_turns

    # 40 sentences in 4 chapters; the book darkens then brightens
    tones = [0.2] * 10 + [-0.6] * 10 + [0.0] * 10 + [0.7] * 10
    sentences = book(*tones, chapters=[i // 10 for i in range(40)])
    for s in sentences:
        s.emotions = {"joy": 0.8, "neutral": 0.2} if s.sentiment > 0 else {"sadness": 0.7, "neutral": 0.3}
    # character 0 is in every sentence except the third chapter; character 1 only twice
    mentions = [Mention(0, i, 0, 0, "x") for i in range(40) if not 20 <= i < 30]
    mentions += [Mention(1, 3, 0, 0, "y"), Mention(1, 35, 0, 0, "y")]
    journey = character_journey(mentions, sentences, 0, stages=4, min_sentences=5)
    assert [(s["first_chapter"], s["last_chapter"]) for s in journey] == [(0, 0), (1, 1), (2, 2), (3, 3)]
    assert [s["count"] for s in journey] == [10, 10, 0, 10]
    assert journey[1]["mood"] == pytest.approx(-0.6) and journey[2]["mood"] is None, "absent: left empty, not guessed"
    assert journey[2]["book_mood"] == pytest.approx(0.0), "the whole book's line goes on without them"
    assert journey[1]["emotions"]["sadness"] == pytest.approx(0.7) and journey[2]["emotions"] == {}
    assert sentences[journey[3]["brightest"]].sentiment == 0.7
    assert journey_turns(journey) == {"start": 0, "end": 3, "low": 1, "high": 3}
    # too few sentences about character 1 anywhere: no journey to tell
    assert journey_turns(character_journey(mentions, sentences, 1, stages=4)) is None
