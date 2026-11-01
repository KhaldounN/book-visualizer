"""The website renders every tab, using a small hand-made analysis."""

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from analyzer.models import BookAnalysis, Chapter, Character, EntityCount, Mention, Sentence
from analyzer.progression import (
    chapter_emotions,
    chapter_sentiment,
    emotions_by_character,
    key_moments,
    mentions_by_chapter,
    rolling_sentiment,
    sentiment_by_chapter,
)
from analyzer.relationships import find_relationships

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"
sys.path.insert(0, str(APP.parent))  # so "import charts" works here too

import charts  # noqa: E402


def small_analysis() -> BookAnalysis:
    names = ["Anna", "Tom", "Eve", "Lizzy", "Max", "Ben"]
    chapters = [Chapter(i, f"Chapter {i + 1}", 0) for i in range(4)]
    sentences, mentions = [], []
    for i in range(80):
        chapter = i // 20
        tone = 0.5 if chapter % 2 else -0.4
        mood = {"joy": 0.6, "neutral": 0.4} if tone > 0 else {"anger": 0.3, "fear": 0.2, "neutral": 0.5}
        sentences.append(Sentence(i, f"s{i}", 0, 0, chapter, sentiment=tone,
                                  emotions={e: mood.get(e, 0.0) for e in charts.EMOTION_LABELS}))
        for c in {0, i % 3, (i + 1) % len(names)}:
            mentions.append(Mention(c, i, 0, 0, "x", "name" if i % 2 else "coref"))
    characters = [Character(i, n, [n], sum(m.character_id == i for m in mentions)) for i, n in enumerate(names)]
    return BookAnalysis(
        chapters=chapters, sentences=sentences, characters=characters, mentions=mentions,
        entities=[EntityCount("London", "GPE", 5, "place", [2, 0, 1, 2]),
                  EntityCount("Regiment", "ORG", 3, "organization", [0, 3, 0, 0])],
        relationships=find_relationships(sentences, mentions, len(chapters)),
        chapter_sentiment=chapter_sentiment(sentences, len(chapters)),
        mentions_by_chapter=mentions_by_chapter(mentions, sentences, len(characters), len(chapters)),
        sentiment_by_chapter=sentiment_by_chapter(mentions, sentences, len(characters), len(chapters)),
        timings={"Reading sentences": 1.0},
        title="Test Book", author="Ann Example",
        chapter_emotions=chapter_emotions(sentences, len(chapters)),
        character_emotions=emotions_by_character(mentions, sentences, len(characters)),
    )


@pytest.fixture
def app():
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["analyses"] = {"book": {"title": "Test Book", "analysis": small_analysis(), "merges": []}}
    at.session_state["current"] = "book"
    return at.run()


def test_every_tab_renders(app):
    assert not app.exception
    assert [t.label for t in app.tabs] == ["Overview", "Mentions", "Story sentiment", "Emotions", "Timeline",
                                           "Relationships", "Places & entities"]
    assert [m.value for m in app.metric][:3] == ["4", "80", "6"]
    assert not app.info, "every tab has data to show (no 'nothing found' messages)"


def test_editing_the_title(app):
    app.text_input[0].set_value("My Better Title").run()
    assert app.session_state["analyses"]["book"]["title"] == "My Better Title"
    assert app.subheader[0].value == "My Better Title"


def test_book_without_emotions_still_renders(app):
    analysis = app.session_state["analyses"]["book"]["analysis"]
    analysis.chapter_emotions = [{} for _ in analysis.chapters]
    app.run()
    assert not app.exception
    assert any("not detected" in i.value for i in app.info)


def test_merging_characters_from_the_sidebar(app):
    app.sidebar.selectbox[0].select("Lizzy").run()
    app.sidebar.selectbox[1].select("Anna").run()
    app.sidebar.button[0].click().run()
    assert not app.exception
    assert app.session_state["analyses"]["book"]["merges"] == [("Lizzy", "Anna")]
    assert app.metric[2].value == "5"  # one character fewer


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_charts_build_in_both_themes(mode):
    theme, analysis = charts.THEMES[mode], small_analysis()
    pair = analysis.relationships[0]
    for figure in (
        charts.mentions_bars(analysis, theme),
        charts.story_sentiment(analysis, theme, [0, 1], smooth=3),
        charts.timeline_heatmap(analysis, theme),
        charts.relationship_network(analysis, theme, top=6, min_count=3),
        charts.pair_tone(analysis, theme, pair, smooth=1),
        charts.pair_moments(analysis, theme, pair),
        charts.pair_emotions(theme, pair),
        charts.mood_arc(analysis, theme, rolling_sentiment(analysis.sentences, 5),
                        key_moments(analysis.sentences, window=5)),
        charts.emotion_bars(theme, analysis.chapter_emotions[0]),
        charts.emotion_bars(theme, analysis.character_emotions[0], analysis.chapter_emotions[1], name="Anna"),
        charts.emotion_journey(analysis, theme, smooth=3),
        charts.places_heatmap(analysis, theme),
        charts.entity_bars(analysis.entities, theme),
    ):
        assert figure.data, "every chart has something to draw"


def test_emotion_shares_leave_out_neutral():
    shares = charts.without_neutral({"joy": 0.3, "anger": 0.1, "neutral": 0.6})
    assert shares["joy"] == pytest.approx(0.75) and shares["anger"] == pytest.approx(0.25)
    assert sum(shares.values()) == pytest.approx(1.0)
    assert charts.without_neutral({"neutral": 1.0}) == {}


def test_line_end_labels_never_overlap():
    fig = charts.go.Figure()
    ends = [(10, 0.15, "Elizabeth"), (10, 0.14, "Whole book"), (10, 0.25, "Mr. Darcy")]
    charts._end_labels(fig, charts.THEMES["light"], ends, (-0.5, 0.5))
    ys = sorted(a.y for a in fig.layout.annotations)
    assert all(b - a >= 0.06 - 1e-9 for a, b in zip(ys, ys[1:]))


def test_character_colours_follow_the_character_not_the_selection():
    theme, analysis = charts.THEMES["light"], small_analysis()
    colors = charts.character_colors(analysis, theme)
    assert colors[0] == theme["series"][0]  # most mentioned character gets slot 1
    # choosing a different set of lines never repaints anyone
    first = charts.story_sentiment(analysis, theme, [0, 2], 1)
    second = charts.story_sentiment(analysis, theme, [2], 1)
    color_of = lambda fig, name: next(t.line.color for t in fig.data if t.name == name)  # noqa: E731
    assert color_of(first, "Eve") == color_of(second, "Eve") == colors[2]
