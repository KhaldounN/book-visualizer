"""The website renders every section, using a small hand-made analysis."""

import json
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from analyzer.models import BookAnalysis, Chapter, ChapterEvent, Character, EntityCount, Mention, Sentence
from analyzer.progression import (
    character_journey,
    journey_turns,
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
    offset = 0
    for i in range(80):
        chapter = i // 20
        tone = 0.5 if chapter % 2 else -0.4
        mood = {"joy": 0.6, "neutral": 0.4} if tone > 0 else {"anger": 0.3, "fear": 0.2, "neutral": 0.5}
        fine = {"amusement": 0.6} if tone > 0 else {"frustration": 0.3, "nervousness": 0.2}
        if i % 3 == 0:  # the sentences that mention Anna and Tom's neighbour-free lines
            fine["guilt"] = 0.5
        # every sentence is its own paragraph: Anna and Tom take turns talking, naming the speaker
        # every other time (the speaker's name is the mention below with real offsets)
        speaker = names[i % 2]
        text = f'"Line {i} goes here, my dear friend, really!" said {speaker}.' if i % 4 < 2 else f'"Reply {i}."'
        sentences.append(Sentence(i, text, offset, offset + len(text), chapter, sentiment=tone,
                                  emotions={e: mood.get(e, 0.0) for e in charts.EMOTION_LABELS}, fine=fine,
                                  tags={"VERB": 2 + i % 3, "ADJ": 1, "ADV": 0, "NOUN": 3}))
        if i % 4 < 2:
            start = offset + text.index(speaker)
            mentions.append(Mention(i % 2, i, start, start + len(speaker), speaker, "name"))
        offset += len(text) + 2
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
    # one continuous page (the owner's choice, replacing tabs): every part in reading order,
    # under a sticky table of contents that links to each of them
    assert not app.tabs
    assert [h.value for h in app.header] == ["Explore in 3D", "The story", "Pace", "Mood", "Emotions", "Characters",
                                             "Relationships", "Dialogue", "Places", "How it works", "About"]
    toc = next(h.proto.body for h in app.get("html") if "ba-toc" in h.proto.body)
    assert all(f'href="#{h.anchor}"' in toc for h in app.header), "the contents bar links to every part"
    assert any("Not a chatbot" in h.proto.body and h.proto.body.count("<li>") == len(design.WORKFLOW)
               for h in app.get("html")), "the How it works part explains the kind of AI and the workflow"
    assert "ba-foot" in app.get("html")[-1].proto.body, "a footer at the bottom"
    assert not any("Jump to" in m.value for m in app.sidebar.markdown), "the tabs replace the jump links"
    assert any("passion project" in h.proto.body for h in app.get("html")), "the About card is shown"
    assert any("The shape of the story" in h.proto.body for h in app.get("html")), "the story shape badge is shown"
    weak = design.story_shape_card("A Book", [0, 1, 0], [("Icarus", 0.1), ("Tragedy", 0.05)])
    assert "follows its own path" in weak and "is loosely" not in weak, "no shape is claimed for a weak fit"
    assert "is clearly an <b>Icarus</b> story" in design.story_shape_card("A Book", [0, 1, 0], [("Icarus", 0.8), ("Tragedy", 0)])
    assert not app.info, "every section has data to show (no 'nothing found' messages)"


def test_dialogue_and_pace_sections_show_the_test_books_talk(app):
    tables = [m.value for m in app.markdown]
    assert any("of the book's words are spoken" in t for t in tables)
    assert any("Fastest: **Chapter" in t for t in tables)
    assert app.selectbox(key="voice_character").value.name in ("Anna", "Tom")
    cards = design.pace_cards(charts_pace(), [{"hours": 0.01, "grade": 5, "dialogue": 0.1, "richness": 0.5}] * 3)
    assert "longer than 3 of 3 famous books" in cards[0]["note"] and "Grade" in cards[1]["value"]


def charts_pace():
    from analyzer.pace import measure
    return measure(small_analysis().sentences, 0.5)


def kpi_values(analysis, mode="light"):
    cards = design.kpis(analysis, explore3d.events_of(analysis), charts.THEMES[mode])
    return {c["label"]: c["value"] for c in cards}


def test_kpis_come_first(app):
    page = app.get("html")
    assert "ba-top" in page[0].proto.body, "the top bar comes first"
    bodies = [h.proto.body for h in page]
    hero = next(i for i, b in enumerate(bodies) if "ba-hero" in b)
    assert "ba-toc" in bodies[1] and "ba-kpis" in bodies[hero + 1], "contents bar, then hero, then KPI cards"
    values = kpi_values(small_analysis())
    assert [values[k] for k in ("Chapters", "Sentences", "Characters")] == ["4", "80", "6"]
    assert values["Main character"] == "Anna"
    assert values["Closest pair"].startswith("Anna &amp; ")
    assert values["Darkest chapter"].startswith("Chapter 1 ")  # chapters 1 and 3 are dark, 1 comes first
    assert {"Overall mood", "Strongest emotion", "Brightest chapter", "Talks the most"} <= set(values)
    assert "Mentions" not in values, "the owner asked for no mention counts up top"
    assert values["Talks the most"] in ("Anna", "Tom")  # the two who talk in the test book


def test_3d_scenes_come_in_the_owners_order_and_show_conversations():
    assert list(explore3d.SCENES) == ["crystal", "constellation", "road"]
    data = explore3d.scene_data(small_analysis())
    anna_tom = [l for l in data["links"] if {l["a"], l["b"]} == {0, 1}]
    assert anna_tom and anna_tom[0]["ab"] + anna_tom[0]["ba"] > 0, "Anna and Tom's talk reaches the constellation"
    assert all("words" in c for c in data["characters"])


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
    # 3 3D views + chapter cards + 3 mood + 4 emotion + 3 character (with the journey) + 2 relationship + 3 dialogue + 2 pace
    # + 2 places
    assert len(titles) == 3 + 1 + 3 + 4 + 3 + 2 + 3 + 2 + 2


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
    by_label = lambda label: next(b for b in app.sidebar.selectbox if b.label == label)
    by_label("Merge").select("Lizzy").run()
    by_label("Into").select("Anna").run()
    next(b for b in app.sidebar.button if b.label == "Merge").click().run()
    assert not app.exception
    assert app.session_state["analyses"]["book"]["merges"] == [("Lizzy", "Anna")]
    merged = app.session_state["analyses"]["book"]
    assert kpi_values(merge_characters(merged["analysis"], merged["merges"]))["Characters"] == "5"


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_charts_build_in_both_themes(mode):
    from analyzer.dialogue import find_lines, who_talks_to_whom, words_spoken
    from analyzer.pace import chapter_pace, pace_scores

    theme, analysis = charts.THEMES[mode], small_analysis()
    pair = analysis.relationships[0]
    lines = find_lines(analysis.sentences, analysis.mentions)
    paces = chapter_pace(analysis.sentences, len(analysis.chapters), [0.5] * len(analysis.chapters))
    book = {"title": "A", "hours": 2.0, "grade": 7.0, "sentence_length": 18.0, "dialogue": 0.4, "richness": 0.7}
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
        charts.character_journey(analysis, theme, character_journey(analysis.mentions, analysis.sentences, 0),
                                 "Anna", theme["series"][0], journey_turns(character_journey(
                                     analysis.mentions, analysis.sentences, 0))),
        charts.fine_bars(theme, {"guilt": 0.2, "calmness": 0.1, "grief": 0.05}),
        charts.places_heatmap(analysis, theme),
        charts.entity_bars(analysis.entities, theme),
        charts.talk_bars(analysis, theme, words_spoken(lines, len(analysis.characters))),
        charts.talk_matrix(analysis, theme, who_talks_to_whom(lines, len(analysis.characters))),
        charts.pace_chapters(analysis, theme, paces, pace_scores(paces)),
        charts.library_strip(theme, [book, {**book, "title": "B", "grade": 9.0}], {**book, "title": "C"}),
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
    assert "raccoon" in design.about(), "the raccoon lives on the About page"


def test_start_page_explains_the_method():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception
    bodies = [h.proto.body for h in at.get("html")]
    assert any("Turn a novel into pictures" in b and b.count('class="ba-kicker">I') == 3 for b in bodies)
    assert any("data:image/jpeg" in b for b in bodies), "the About tab still shows the raccoon"


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


def test_the_road_knows_each_chapters_landscape():
    analysis = small_analysis()
    data = explore3d.scene_data(analysis)
    assert len(data["landscape"]) == len(analysis.chapters)
    assert all(l["kind"] in data["landscapeLabels"] for l in data["landscape"])
    # every landscape the analyzer can choose has a look in the 3D scene
    assert all(f"\n  {kind}: {{ icon:" in explore3d.TEMPLATE.read_text(encoding="utf-8") for kind in data["landscapeLabels"])
    # ...and each weather has a picture (the weather is None when a chapter says nothing about it)
    assert len(data["weather"]) == len(analysis.chapters)
    icons = explore3d.TEMPLATE.read_text(encoding="utf-8").split("const WEATHER_ICONS")[1].split("\n")[0]
    assert all(f'{kind}: "' in icons for kind in data["weatherLabels"])
    # ...and each road shape has an icon and a shape
    assert len(data["route"]) == len(analysis.chapters)
    page = explore3d.TEMPLATE.read_text(encoding="utf-8")
    for kind in data["routeLabels"]:
        assert f'{kind}: "' in page.split("const ROUTE_ICONS")[1].split("\n")[0]
        assert f"{kind}: [" in page.split("const ROUTE_SHAPE")[1].split("\n")[0]


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


def test_the_open_book_is_kept_in_the_address(app):
    import looks
    assert app.query_params["book"] == "book", "a reload (to switch light/dark) reopens this book"
    assert '"Dark"' in looks.switch_script("dark") and '"Light"' in looks.switch_script("light")


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


def test_picking_a_famous_book_opens_it():
    import hashlib
    from analyzer.pipeline import ANALYSIS_VERSION
    book = APP.parent.parent / "data" / "great_expectations.txt"
    key = hashlib.sha256(book.read_bytes()).hexdigest() if book.exists() else ""
    if not (APP.parent.parent / "results" / f"v{ANALYSIS_VERSION}-{key}.pkl").exists():
        pytest.skip("needs the sample book, already analyzed (scripts/download_samples.py, analyze_samples.py)")
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert "Great Expectations ⚡" in at.selectbox(key="sample").options  # ⚡ = already analyzed
    at.selectbox(key="sample").set_value("great_expectations.txt").run()
    assert not at.exception and at.session_state["current"] == key
    at.run()  # later reruns keep the book open (the picker doesn't reopen it every time)
    assert at.session_state["current"] == key


def test_picking_dark_remembers_it_in_the_address(app):
    app.segmented_control(key="look_light").set_value("dark").run()
    assert not app.exception
    assert app.query_params["look"] == "dark", "the reload after the switch keeps the choice"


def test_a_characters_journey_is_told_in_words(app):
    # Anna is in every sentence: her mood follows the book (dark, bright, dark, bright)
    assert app.selectbox(key="journey_character").value.name == "Anna"
    lines = [m.value for m in app.markdown]
    assert any(line.startswith("**Mood:** -0.40 at the start (Ch. 1)") for line in lines)
    assert any(line.startswith("▼ **Lowest point** (Chapter") for line in lines)
    assert any(line.startswith("▲ **Highest point** (Chapter") for line in lines)
    assert any(line.startswith("**Emotions:** by the end, more **joy**") for line in lines)
