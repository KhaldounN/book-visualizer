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
