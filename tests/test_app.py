"""The website renders every section, using a small hand-made analysis."""

import json
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from analyzer.models import BookAnalysis, Chapter, ChapterEvent, Character, EntityCount, Mention, Sentence
from analyzer.progression import (
    chapter_emotions,
    chapter_sentiment,
    emotions_by_character,
    key_moments,
    mentions_by_chapter,
    rolling_sentiment,
    sentiment_by_chapter,
)
from analyzer.merge import merge_characters
from analyzer.relationships import find_relationships

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"
sys.path.insert(0, str(APP.parent))  # so "import charts" works here too

import charts  # noqa: E402
import design  # noqa: E402
import explore3d  # noqa: E402


def small_analysis() -> BookAnalysis:
    names = ["Anna", "Tom", "Eve", "Lizzy", "Max", "Ben"]
    chapters = [Chapter(i, f"Chapter {i + 1}", 0) for i in range(4)]
    sentences, mentions = [], []
    for i in range(80):
        chapter = i // 20
        tone = 0.5 if chapter % 2 else -0.4
        mood = {"joy": 0.6, "neutral": 0.4} if tone > 0 else {"anger": 0.3, "fear": 0.2, "neutral": 0.5}
        fine = {"amusement": 0.6} if tone > 0 else {"frustration": 0.3, "nervousness": 0.2}
        if i % 3 == 0:  # the sentences that mention Anna and Tom's neighbour-free lines
            fine["guilt"] = 0.5
        sentences.append(Sentence(i, f"s{i}", 0, 0, chapter, sentiment=tone,
                                  emotions={e: mood.get(e, 0.0) for e in charts.EMOTION_LABELS}, fine=fine))
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
        chapter_fine=chapter_emotions(sentences, len(chapters), "fine"),
        character_fine=emotions_by_character(mentions, sentences, len(characters), "fine"),
        chapter_events=[ChapterEvent(theme, 1.5 + i, f"Something happens in chapter {i + 1}.", ["word", "other"])
                        for i, theme in enumerate(["Ball", "Letter", "Journey", "Wedding"])],
    )


@pytest.fixture
def app():
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["analyses"] = {"book": {"title": "Test Book", "analysis": small_analysis(), "merges": []}}
    at.session_state["current"] = "book"
    return at.run()


def test_the_dashboard_shows_every_section_in_order(app):
    assert not app.exception
    assert not app.tabs, "one scrolling page, no tabs"
    assert [h.value for h in app.header] == ["Explore in 3D", "The story", "Mood", "Emotions", "Characters",
                                             "Relationships", "Places", "About"]
    assert any("passion project" in h.proto.body for h in app.get("html")), "the About card is shown"
    assert any("The shape of the story" in h.proto.body for h in app.get("html")), "the story shape badge is shown"
    weak = design.story_shape_card("A Book", [0, 1, 0], [("Icarus", 0.1), ("Tragedy", 0.05)])
    assert "follows its own path" in weak and "is loosely" not in weak, "no shape is claimed for a weak fit"
    assert "is clearly an <b>Icarus</b> story" in design.story_shape_card("A Book", [0, 1, 0], [("Icarus", 0.8), ("Tragedy", 0)])
    assert not app.info, "every section has data to show (no 'nothing found' messages)"


def kpi_values(analysis, mode="light"):
    cards = design.kpis(analysis, explore3d.events_of(analysis), charts.THEMES[mode])
    return {c["label"]: c["value"] for c in cards}


def test_kpis_come_first(app):
    page = app.get("html")
    assert "ba-hero" in page[0].proto.body and "ba-kpis" in page[1].proto.body, "hero, then KPI cards, on top"
    values = kpi_values(small_analysis())
    assert [values[k] for k in ("Chapters", "Sentences", "Characters")] == ["4", "80", "6"]
    assert values["Main character"] == "Anna"
    assert values["Closest pair"].startswith("Anna &amp; ")
    assert values["Darkest chapter"].startswith("Chapter 1 ")  # chapters 1 and 3 are dark, 1 comes first
    assert {"Overall mood", "Strongest emotion", "Brightest chapter", "Mentions"} <= set(values)


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_kpi_cards_and_hero_build(mode):
    analysis, theme = small_analysis(), charts.THEMES[mode]
    page = design.kpi_html(design.kpis(analysis, explore3d.events_of(analysis), theme))
    assert len(re.findall(r'class="ba-kpi[ "]', page)) == 10
    assert page.count("<svg") >= 3, "the cards carry small pictures"
    hero = design.hero(analysis, "Test <Book>", explore3d.events_of(analysis), theme)
    assert hero.count("<i style=\"height:") == 4, "one barcode stripe per chapter"
    assert "Test &lt;Book&gt;" in hero, "the title is escaped"
    assert "</style>" in design.page_css(theme, mode)


def test_a_character_keeps_one_colour_everywhere():
    theme, analysis = charts.THEMES["light"], small_analysis()
    anna = charts.character_colors(analysis, theme)[0]
    mentions = charts.mentions_bars(analysis, theme)
    assert mentions.data[0].marker.color[-1] == anna  # Anna is the biggest bar (last = top)
    assert anna in charts.timeline_heatmap(analysis, theme).layout.yaxis.ticktext[0]
    assert anna in design.cast_legend(analysis, theme)
    data = explore3d.scene_data(analysis)
    assert data["characters"][0]["color"] == charts.character_colors(analysis, charts.THEMES["dark"])[0]
    # charts about things that are not one character never borrow a character's colour
    for figure in (charts.pair_moments(analysis, theme, analysis.relationships[0]),
                   charts.entity_bars(analysis.entities, theme)):
        assert figure.data[0].marker.color not in theme["series"]


def test_every_visualization_has_an_explanation(app):
    titles = [m.value for m in app.markdown if m.value.startswith("#### ")]
    # 3 3D views + chapter cards + 3 mood + 4 emotion + 2 character + 2 relationship + 2 places
    assert len(titles) == 3 + 1 + 3 + 4 + 2 + 2 + 2


def test_editing_the_title(app):
    app.sidebar.text_input[0].set_value("My Better Title").run()
    assert app.session_state["analyses"]["book"]["title"] == "My Better Title"
    assert "My Better Title" in app.get("html")[0].proto.body  # the hero banner


def test_fine_emotions_show_what_stands_out(app):
    # Anna is in every sentence, so nothing about her is above the book: no line
    assert not [m for m in app.markdown if m.value.startswith("**Stands out for")]
    # Max is only in every 6th sentence, all of which carry guilt (3x the book)
    app.selectbox(key="emotion_character").select(next(c for c in app.session_state["analyses"]["book"]["analysis"]
                                                        .characters if c.name == "Max")).run()
    lines = [m.value for m in app.markdown if m.value.startswith("**Stands out for")]
    assert lines and lines[0].startswith("**Stands out for Max:** guilt")
    data = explore3d.scene_data(small_analysis())
    assert data["warm"] == ["love", "joy", "surprise"]
    assert len(data["chapterStandOut"]) == 4 and all(isinstance(x, list) for x in data["chapterStandOut"])
    assert all(len(shares) == len(charts.EMOTION_ORDER) for shares in data["chapterEmotions"])


def test_book_without_emotions_still_renders(app):
    analysis = app.session_state["analyses"]["book"]["analysis"]
    analysis.chapter_emotions = [{} for _ in analysis.chapters]
    app.run()
    assert not app.exception
    assert any("not detected" in i.value for i in app.info)


def test_merging_characters_from_the_sidebar(app):
    app.sidebar.selectbox[0].select("Lizzy").run()
    app.sidebar.selectbox[1].select("Anna").run()
    next(b for b in app.sidebar.button if b.label == "Merge").click().run()
    assert not app.exception
    assert app.session_state["analyses"]["book"]["merges"] == [("Lizzy", "Anna")]
    merged = app.session_state["analyses"]["book"]
    assert kpi_values(merge_characters(merged["analysis"], merged["merges"]))["Characters"] == "5"


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
        charts.fine_bars(theme, {"guilt": 0.2, "calmness": 0.1, "grief": 0.05}),
        charts.places_heatmap(analysis, theme),
        charts.entity_bars(analysis.entities, theme),
    ):
        assert figure.data, "every chart has something to draw"


@pytest.mark.parametrize("scene", list(explore3d.SCENES))
def test_every_3d_scene_page_is_built(scene):
    html = explore3d.scene_html(small_analysis(), scene)
    assert "__DATA__" not in html and "__SCENE__" not in html
    assert f'const SCENE = "{scene}";' in html
    data = json.loads(re.search(r"const data = (.*);\nconst SCENE", html).group(1))
    assert len(data["chapterTitles"]) == data["chapters"] == 4
    assert all(0 <= link["a"] < len(data["characters"]) and 0 <= link["b"] < len(data["characters"])
               for link in data["links"])
    assert all(abs(sum(c["emotions"]) - 1) < 0.01 for c in data["characters"])


def test_story_road_gets_the_story_arc():
    data = explore3d.scene_data(small_analysis())
    assert len(data["arc"]) == 4
    assert data["acts"][0][0] == 0 and data["acts"][-1][1] == 3, "the acts cover the whole book"
    assert all(p["kind"] in ("high", "low") for p in data["turning"])
    assert "road" in explore3d.SCENES and "road" not in explore3d.EMOTION_SCENES  # it works without emotions
    assert all(len(c["presence"]) == 4 for c in data["characters"]), "every walker has a presence per chapter"


def test_presence_is_a_smoothed_share_of_each_chapter():
    # A is in every chapter, B only in chapter 3 (of 4)
    shares = explore3d.presence([[5, 5, 5, 5], [0, 0, 5, 0]], smooth=0)
    assert shares == [[1, 1, 0.5, 1], [0, 0, 0.5, 0]]
    smoothed = explore3d.presence([[5, 5, 5, 5], [0, 0, 5, 0]], smooth=1)
    # B fades in and out; the last chapter has one neighbour, so it averages two chapters
    assert (smoothed[1][0], smoothed[1][1], smoothed[1][3]) == (0, round(0.5 / 3, 3), 0.25)
    assert explore3d.presence([]) == []


def test_the_raccoon_has_a_line_for_every_analysis_step():
    from analyzer.pipeline import STEPS
    assert set(STEPS) <= set(design.MASCOT_LINES), "a new pipeline step needs a raccoon line"
    card = design.working_card("Linking pronouns")
    assert card.count('src="data:image/svg+xml;base64,') == 1 and card.count("animation-delay") == len(design.MASCOT_TIPS)
    assert "Harder than it sounds" in card, "the card says what the raccoon is doing now"
    import xml.etree.ElementTree as ET
    import raccoon
    assert set(STEPS) <= set(raccoon.SCENES), "a new pipeline step needs its own raccoon scene"
    for step in [*STEPS, "anything else"]:
        svg = raccoon.scene_svg(step)
        ET.fromstring(svg)  # a valid picture
        assert "@keyframes" in svg and "prefers-reduced-motion" in svg
    assert len({raccoon.scene_svg(s) for s in STEPS}) == len(STEPS), "every step looks different"
    assert "data:image/png;base64," in design.sidebar_title()
    assert "raccoon" in design.landing()


def test_start_page_shows_the_mascot():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception
    assert any("Turn a novel into pictures" in h.proto.body and "data:image/jpeg" in h.proto.body
               for h in at.get("html"))


def test_every_chapter_theme_has_an_icon():
    from analyzer.chapter_events import THEMES
    assert set(THEMES) == set(explore3d.THEME_ICONS), "a new theme needs an icon (and an old one loses it)"
    assert len(set(explore3d.THEME_ICONS.values())) == len(THEMES), "every theme gets its own picture"
    data = explore3d.scene_data(small_analysis())
    assert [e["icon"] for e in data["chapterEvents"]] == ["💃", "📜", "🐎", "💒"]  # Ball, Letter, Journey, Wedding
    analysis = small_analysis()
    analysis.chapter_events = None  # keyword themes from an old analysis: a book icon, and no theme badges
    data = explore3d.scene_data(analysis)
    assert {e["icon"] for e in data["chapterEvents"]} == {explore3d.NO_ICON} and data["keyThemes"] == []


def test_themes_are_objects_and_feelings_are_faces():
    from analyzer.emotions import FAMILIES
    assert set(explore3d.EMOTION_ICONS) == set(FAMILIES)
    assert not set(explore3d.THEME_ICONS.values()) & set(explore3d.EMOTION_ICONS.values())


def test_only_key_chapters_get_pictures_spaced_apart():
    data = explore3d.scene_data(small_analysis())
    # the clearest theme first (Wedding, ch 4), then Ball (ch 1): 3 chapters apart
    assert data["keyThemes"] == [0, 3]
    feelings = data["keyFeelings"]
    assert 0 < len(feelings) <= explore3d.KEY_FEELINGS
    spots = [f["i"] for f in feelings]
    assert all(b - a >= explore3d.MIN_GAP for a, b in zip(spots, spots[1:]))
    # dark chapters (1, 3) stand out for anger or fear, bright ones (2, 4) for joy
    assert all(f["emotion"] in ({"anger", "fear"} if f["i"] % 2 == 0 else {"joy"}) for f in feelings)


def test_3d_page_cannot_be_broken_by_a_name():
    analysis = small_analysis()
    analysis.characters[0].name = "</script><b>Anna"
    html = explore3d.scene_html(analysis, "constellation")
    assert "</script><b>" not in html  # the name can't end the script tag early


def test_old_analysis_without_themes_falls_back_to_keywords(app):
    app.session_state["analyses"]["book"]["analysis"].chapter_events = None
    app.run()
    assert not app.exception
    assert any("before chapter themes existed" in i.value for i in app.info)


def test_chapter_details_name_people_and_places():
    details = charts.chapter_details(small_analysis())
    assert len(details) == 4
    assert details[0]["place"] == "London" and details[1]["place"] is None  # London isn't in chapter 2
    assert all(1 <= len(d["people"]) <= 2 for d in details)


def test_unknown_3d_scene_is_refused():
    with pytest.raises(ValueError):
        explore3d.scene_html(small_analysis(), "hologram")


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


def test_fun_look_adds_the_raccoon_buddy():
    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["analyses"] = {"book": {"title": "Test Book", "analysis": small_analysis(), "merges": []}}
    at.session_state["current"] = "book"
    at.query_params["look"] = "fun"
    at.run()
    assert not at.exception
    bodies = [h.proto.body for h in at.get("html")]
    assert any('id="ba-buddy"' in b for b in bodies) and any("Fredoka" in b for b in bodies)
    # the start page has the buddy too
    start = AppTest.from_file(str(APP), default_timeout=30)
    start.query_params["look"] = "fun"
    start.run()
    assert not start.exception and any('id="ba-buddy"' in h.proto.body for h in start.get("html"))


def test_the_plain_looks_have_no_buddy(app):
    assert not any('id="ba-buddy"' in h.proto.body for h in app.get("html"))
    assert app.query_params["book"] == "book", "the open book is kept in the address"


def test_book_facts_and_buddy_drawing():
    import xml.etree.ElementTree as ET
    import fun
    import raccoon
    facts = fun.book_facts(small_analysis(), "Icarus")
    assert any("an Icarus story" in f for f in facts) and any("darkest chapter" in f for f in facts)
    svg = raccoon.buddy_svg()
    ET.fromstring(svg)
    assert all(f"act-{a}" in svg for a in raccoon.BUDDY_ACTS) and 'id="ba-pupils"' in svg
    assert "ba-pupils" in fun.buddy_script(["a fact"]), "the script draws the raccoon in"
    assert '"Dark"' in fun.switch_script("dark") and '"Light"' in fun.switch_script("light")


def test_a_reload_reopens_the_book_from_its_saved_analysis():
    import pickle
    from analyzer.pipeline import ANALYSIS_VERSION
    key = "ab" * 32
    saved = APP.parent.parent / "results" / f"v{ANALYSIS_VERSION}-{key}.pkl"
    saved.parent.mkdir(exist_ok=True)
    saved.write_bytes(pickle.dumps(small_analysis()))
    try:
        at = AppTest.from_file(str(APP), default_timeout=30)
        at.query_params["book"] = key
        at.run()
        assert not at.exception and at.session_state["current"] == key
    finally:
        saved.unlink()


def test_picking_dark_remembers_it_in_the_address(app):
    app.segmented_control(key="look_light").set_value("dark").run()
    assert not app.exception
    assert app.query_params["look"] == "dark", "the reload after the switch keeps the choice"
