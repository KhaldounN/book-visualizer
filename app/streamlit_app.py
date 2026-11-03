"""Book Analyzer website. Run from the project folder:

    .venv\\Scripts\\streamlit run app\\streamlit_app.py
"""

import hashlib
import html
import itertools
import pickle
import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so "analyzer" can be imported when Streamlit runs this file

import streamlit.components.v1 as components  # noqa: E402

import charts  # noqa: E402
import design  # noqa: E402
import explore3d  # noqa: E402
import fun  # noqa: E402
from avatars import cast_avatars  # noqa: E402
from analyzer.emotions import average_emotions, stand_out  # noqa: E402
from analyzer.merge import merge_characters  # noqa: E402
from analyzer.pipeline import ANALYSIS_VERSION, analyze  # noqa: E402
from analyzer.progression import WEAK_FIT, key_moments, rolling_sentiment, story_shape  # noqa: E402

SAMPLE = ROOT / "data" / "great_expectations.txt"  # from scripts/download_samples.py
SAMPLE_TITLE = "Great Expectations"
CACHE = ROOT / "results"  # finished analyses, so a book is only analyzed once
ENTITY_TYPES = {
    "GPE": "Country or city", "LOC": "Place", "FAC": "Building", "ORG": "Organization",
    "NORP": "Group or nationality", "EVENT": "Event", "WORK_OF_ART": "Title of a work",
}
KINDS = {"place": "Places", "organization": "Organizations", "group": "Groups and families", "other": "Other"}

st.set_page_config(page_title="Book Analyzer", page_icon=str(ROOT / "app" / "assets" / "raccoon-face.png"),
                   layout="wide")
MODE = "dark" if st.context.theme.type == "dark" else "light"
theme = charts.THEMES[MODE]
st.html(design.page_css(theme, MODE))
PANELS = itertools.count()  # numbers each visualization card (restarts on every rerun)


def table(df: pd.DataFrame) -> None:
    with st.expander("Show as table"):
        st.dataframe(df, hide_index=True, width="stretch")


def passage(analysis, moment, limit: int = 450) -> str:
    """The text of a key moment, shortened to about `limit` characters."""
    text = " ".join(s.text for s in analysis.sentences[moment.first:moment.last + 1])
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def how_many(label: str, available: int, default: int, key: str) -> int:
    """Slider for how many characters to show (no slider for tiny casts)."""
    if available <= 5:
        return available
    return st.slider(label, 5, min(40, available), min(default, available), key=key)


def run_analysis(data: bytes, key: str, filename: str):
    """Analyze the book, or load the saved result if it was analyzed before.
    The file is never stored, only the analysis results. The version in the
    file name means results from an older version of the analysis are ignored."""
    saved = CACHE / f"v{ANALYSIS_VERSION}-{key}.pkl"
    if saved.exists():
        return pickle.loads(saved.read_bytes())
    # the raccoon at work: its card changes with each step (a new animated scene);
    # in between only the progress bar moves
    holder = st.empty()
    with holder.container():
        card = st.empty()
        card.html(design.working_card())
        bar = st.progress(0.0, text="Starting… a full novel takes about 10 minutes.")
    shown = [None]

    def progress(step: str, fraction: float) -> None:
        if step != shown[0]:  # a new step: a new scene and line from the raccoon
            shown[0] = step
            card.html(design.working_card(step))
        bar.progress(min(fraction, 1.0), text=f"{step}… {fraction:.0%}")

    try:
        result = analyze(data, progress, filename=filename)
    finally:
        holder.empty()
    CACHE.mkdir(exist_ok=True)
    saved.write_bytes(pickle.dumps(result))
    return result


def panel(title: str, explanation: str, columns: tuple = (1, 2.4)):
    """One dashboard row: what the visualization shows on the left, the
    visualization itself on the right. Returns both columns."""
    st.space("small")
    with st.container(key=f"panel-{next(PANELS)}"):  # the key gives the card its CSS class
        left, right = st.columns(columns, gap="large")
    with left:
        st.markdown(f"#### {title}")
        st.markdown(explanation)
    return left, right


def section(title: str, intro: str) -> None:
    st.header(title, anchor=title.lower().replace(" ", "-"))
    st.caption(intro)


# --- Upload and analysis (in the sidebar, so the page is all dashboard) -----------

with st.sidebar:
    st.html(design.sidebar_title())
    # The look. Light and dark are Streamlit's own themes, so switching between them reloads
    # the page once (the open book is kept in the address); fun adds a playful skin and a buddy.
    asked = st.query_params.get("look")
    if "look_seen" not in st.session_state:  # the page just opened: follow the address (a bookmark, a shared link)
        st.session_state["look_seen"] = True
        current_look = asked if asked in fun.LOOKS else MODE
    else:  # afterwards the page's real theme wins, so Streamlit's own settings menu works too
        current_look = "fun" if asked == "fun" else MODE
    look = st.segmented_control("Look", list(fun.LOOKS), format_func=fun.LOOKS.get, default=current_look,
                                key=f"look_{current_look}") or current_look
    if look != st.query_params.get("look"):
        st.query_params["look"] = look
    if look in ("light", "dark") and look != MODE:
        components.html(fun.switch_script(look), height=0)
    if look == "fun":
        st.html(fun.fun_css(MODE))
    st.caption("Upload an English novel as a `.txt` file to see its characters, how they relate, "
               "and how the mood changes through the story.")
    uploaded = st.file_uploader("Book file", type=["txt"])
    sample_clicked = SAMPLE.exists() and st.button(f"Try it with *{SAMPLE_TITLE}*")

if uploaded is not None:
    data, filename = uploaded.getvalue(), uploaded.name
elif sample_clicked:
    data, filename = SAMPLE.read_bytes(), SAMPLE.name
elif "current" in st.session_state:
    data, filename = None, None  # keep showing the last book
elif re.fullmatch(r"[0-9a-f]{64}", st.query_params.get("book", "")) and \
        (CACHE / f"v{ANALYSIS_VERSION}-{st.query_params['book']}.pkl").exists():
    # the page was reloaded (e.g. to switch light/dark): reopen the book from its saved analysis
    key = st.query_params["book"]
    result = pickle.loads((CACHE / f"v{ANALYSIS_VERSION}-{key}.pkl").read_bytes())
    st.session_state.setdefault("analyses", {})[key] = {"title": result.title, "analysis": result, "merges": []}
    st.session_state["current"] = key
    data, filename = None, None
else:
    st.html(design.landing())
    st.html(design.about())
    if look == "fun":
        st.html(fun.buddy_html())
        components.html(fun.buddy_script(["Upload a book and I'll read it for you!", "I love a good novel. 📚",
                                          "Try the sample: Great Expectations!"], peek=False), height=0)
    st.stop()

analyses = st.session_state.setdefault("analyses", {})
if data is not None:
    key = hashlib.sha256(data).hexdigest()
    if key not in analyses:
        try:
            result = run_analysis(data, key, filename)
            analyses[key] = {"title": result.title, "analysis": result, "merges": []}
        except ValueError as error:
            st.error(str(error))
            st.stop()
    st.session_state["current"] = key

book = analyses[st.session_state["current"]]
if st.query_params.get("book") != st.session_state["current"]:
    st.query_params["book"] = st.session_state["current"]  # so a reload reopens this book
analysis = merge_characters(book["analysis"], book["merges"]) if book["merges"] else book["analysis"]
if not analysis.characters:
    st.warning("No characters were found in this book.")
    st.stop()


def cast_for(mode: str):
    """The main characters' looks and avatars for this book, its merges and a colour mode,
    drawn once per session (reading the clues takes a second on a long novel)."""
    key = (st.session_state["current"], tuple(book["merges"]), mode)
    cache = st.session_state.setdefault("avatars", {})
    if key not in cache:
        cache[key] = cast_avatars(analysis, charts.THEMES[mode])
    return cache[key]


looks, faces = cast_for(MODE)
faces_3d = cast_for("dark")[1]  # the 3D stage is always dark

# --- Sidebar: title and merging characters ----------------------------------------

with st.sidebar:
    st.divider()
    new_title = st.text_input("Book title", book["title"], key=f"title_{st.session_state['current']}")
    if new_title.strip() and new_title != book["title"]:
        book["title"] = new_title.strip()
        st.rerun()
    st.subheader("Merge characters")
    st.caption("Nicknames and married names need knowledge of the story, so the analysis "
               "keeps them apart. Merge them here, e.g. *Lizzy* into *Elizabeth*.")
    names = [c.name for c in charts.top_characters(analysis, len(analysis.characters))]
    source = st.selectbox("Merge", names, index=None, placeholder="Choose a character")
    into = st.selectbox("Into", [n for n in names if n != source], index=None, placeholder="Choose a character")
    if st.button("Merge", disabled=not (source and into), type="primary"):
        book["merges"].append((source, into))
        st.rerun()
    if book["merges"]:
        st.write("**Merged so far**")
        for s, i in book["merges"]:
            st.write(f"- {s} → {i}")
        if st.button("Undo all merges"):
            book["merges"].clear()
            st.rerun()
    st.divider()
    st.subheader("Character colours")
    st.caption("Each main character keeps one colour in every chart and 3D view.")
    st.html(design.cast_legend(analysis, theme, faces))
    st.divider()
    st.subheader("Jump to")
    st.markdown("\n".join(f"- [{name}](#{name.lower().replace(' ', '-')})" for name in (
        "Explore in 3D", "The story", "Mood", "Emotions", "Characters", "Relationships", "Places", "About")))

has_emotions = any(analysis.chapter_emotions)
events = explore3d.events_of(analysis)
book_mix = average_emotions([s.emotions for s in analysis.sentences])
book_fine = average_emotions([s.fine for s in analysis.sentences])  # the 38 fine emotions
names = {c.id: c.name for c in analysis.characters}

# --- Header and KPIs ---------------------------------------------------------------

st.html(design.hero(analysis, book["title"], events, theme))
st.html(design.kpi_html(design.kpis(analysis, events, theme, faces)))
st.html(design.cast_strip(analysis, looks, faces, theme))

with st.container():
    with st.expander("How to read these results"):
        st.markdown(
            "- **Tone** comes from an AI model that scores each sentence from −1 (negative) to +1 "
            "(positive). It reads the *words*, not the characters' true feelings: polite flattery "
            "scores positive even when it is ridiculous.\n"
            "- **Mentions** include names *and* pronouns (\"she\", \"his\"). Pronouns are linked by "
            "another AI model that is right roughly 3 times out of 4, so treat counts as estimates "
            "and look at trends. \"I\" and \"you\" in dialogue are not counted.\n"
            "- Two characters are **together** when both are mentioned in the same or neighbouring "
            "sentences. Their tone is the tone of those shared moments.\n"
            "- **Emotions** come from a third AI model, trained on sentences from classic books, that "
            "scores 38 fine emotions (grief, guilt, gratitude, curiosity…) in every sentence. The charts "
            "group them into 8 families; most sentences in a novel are *neutral*. On a hand check it was "
            "right about 4 times in 5, and it is weakest at fear.\n"
            "- If a character appears twice under different names, merge them in the sidebar."
        )
    st.caption("Analysis time: " + ", ".join(f"{k} {v:.0f}s" for k, v in analysis.timings.items()))

# --- Explore in 3D ---------------------------------------------------------------------

SCENE_HELP = {
    "road": "**The story as a journey.** The road runs from the first chapter to the last and climbs or dips with "
            "the story's overall mood: **hills** where it is bright, **valleys** where it turns dark. Its colour is "
            "each chapter's own mood (blue brighter, red darker). **Signposts** name the turning points: gold "
            "▲ on the high points, red ▼ in the low ones. A **gate** marks where each act begins. Round **badges** show the theme "
            "of the key chapters (⚔️ battle, 💍 proposal, 🪦 death…), and small **faces** at the roadside mark where "
            "one feeling clearly stands out (😨 fear, 🥰 love, 😢 sadness…). The **cast walks with you**: a "
            "character's face steps onto the road when they enter the story and walks off it when they leave, so "
            "the main character travels the whole way and others come and go.\n\n"
            "**Try:** press **Travel** to ride the road and read what happens in each chapter, or click the road "
            "to stop at a chapter.",
    "constellation": "**Each character is a star.** Where it sits says who they are emotionally: left to right "
                     "is darker to brighter tone, bottom to top is early to late in the book, back to front is "
                     "cold emotions (sadness, anger, fear, shame, disapproval) to warm ones (love, joy, "
                     "surprise). Size = how "
                     "often they are mentioned; colour = the emotion that stands out for them; lines = "
                     "relationships, coloured by tone.\n\n**Try:** click a star to light up only its "
                     "relationships and open its emotion card.",
    "crystal": "**A hologram portrait of one character.** Eight crystal spikes grow from the core, one per "
               "emotion family, as long as that family's share. The ring around it goes once round the book: it rises "
               "and turns blue in bright chapters, and sinks and turns red in dark ones.\n\nIt shows **each "
               "character in turn**, a new one every 5 seconds. **Try:** pick a character from the list to stop "
               "and explore, and compare their shapes.",
}

section("Explore in 3D", "Interactive views to explore the book. Drag any of them to rotate. They are best for "
        "spotting patterns; the charts further down give exact numbers.")
for scene, title in explore3d.SCENES.items():
    left, right = panel(title, SCENE_HELP[scene])
    if scene == "road":
        with left:
            st.html(design.story_shape_card(book["title"], *story_shape(analysis.sentences)))
    with right:
        if scene in explore3d.EMOTION_SCENES and not has_emotions:
            st.info("This view needs emotions, which were not detected for this book.")
        else:
            components.html(explore3d.scene_html(analysis, scene, faces_3d), height=520)

# --- The story ---------------------------------------------------------------------------


def chapter_cards(events: list, details: list[dict]) -> str:
    """A sideways-scrolling strip of chapter cards (plain HTML and CSS)."""
    negative, middle, positive = theme["diverging"]
    by_id = charts.character_colors(analysis, theme)
    colors = {c.name: by_id[c.id] for c in analysis.characters}
    ids = {c.name: c.id for c in analysis.characters}
    cards = []
    for ch, (event, detail) in enumerate(zip(events, details)):
        tone = analysis.chapter_sentiment[ch]
        color = positive if tone >= 0.04 else negative if tone <= -0.04 else middle
        mix_shares = charts.without_neutral(analysis.chapter_emotions[ch]) if has_emotions else {}
        mix = "".join(f'<i style="flex:{mix_shares[e]};background:{theme["emotions"][e]}"></i>'
                      for e in charts.EMOTION_ORDER if mix_shares.get(e))
        place = f"<br>at {html.escape(detail['place'])}" if detail["place"] else ""
        people = ", ".join((f'<img src="{faces[ids[n]]}" alt="" class="face">' if ids.get(n) in faces else
                            f'<b style="color:{colors.get(n, theme["muted"])}">●</b> ') + html.escape(n)
                           for n in detail["people"])
        feels = stand_out(analysis.chapter_fine[ch], book_fine) if analysis.chapter_fine else []
        feels = f'<span class="feels">{html.escape(", ".join(feels))}</span>' if feels else ""
        cards.append(
            f'<article><div class="top"><span>{html.escape(analysis.chapters[ch].title)}</span>'
            f'<b style="background:{color}">{tone:+.2f}</b></div>'
            f'<h4>{html.escape(event.theme)}</h4><p>{html.escape(event.event)}</p><div class="mix">{mix}</div>{feels}'
            f'<small>{people}{place}<br>{html.escape(" · ".join(event.keywords))}</small></article>'
        )
    return f"""<style>
      .cards {{ display: grid; grid-auto-flow: column; grid-auto-columns: 230px; gap: 10px; overflow-x: auto; padding-bottom: 10px; }}
      .cards article {{ border: 1px solid {theme["grid"]}; border-radius: 6px; padding: 12px; display: grid; gap: 7px;
                        align-content: start; background: {theme["surface"]}; color: {theme["ink"]}; }}
      .cards .top {{ display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: {theme["muted"]}; }}
      .cards .top b {{ color: #fff; font-weight: 500; font-size: 12px; padding: 2px 6px; border-radius: 3px; }}
      .cards h4 {{ margin: 0; font-size: 19px; }}
      .cards p {{ margin: 0; font-size: 13px; color: {theme["ink2"]}; line-height: 1.4; }}
      .cards .mix {{ display: flex; gap: 1px; height: 7px; border-radius: 2px; overflow: hidden; }}
      .cards .face {{ width: 20px; height: 20px; border-radius: 50%; vertical-align: middle; margin-right: 4px; }}
      .cards .feels {{ font-size: 12px; font-style: italic; color: {theme["ink2"]}; }}
      .cards small {{ color: {theme["muted"]}; font-size: 12px; line-height: 1.45; }}
    </style><div class="cards">{"".join(cards)}</div>"""


section("The story", "What happens chapter by chapter. Each chapter's theme is picked by a small AI model running "
        "on this computer; it is right about half the time, so every label comes with the sentence and words it "
        "is based on.")
if not analysis.chapter_events:
    st.info("This analysis was made before chapter themes existed, so the themes are keywords. "
            "Analyze the book again to get model themes.")

left, right = panel("Chapter by chapter", "One card per chapter: its theme, its most telling sentence, its mood, "
                    "its mix of emotions, who is in it and where it happens.\n\n**Scroll sideways** through "
                    "the cards.")
with right:
    st.html(chapter_cards(events, charts.chapter_details(analysis)))
    table(pd.DataFrame([
        {"Chapter": c.title, "Theme": e.theme, "Main event": e.event, "Keywords": ", ".join(e.keywords),
         "Mood": round(analysis.chapter_sentiment[i], 3)}
        for i, (c, e) in enumerate(zip(analysis.chapters, events))
    ]))

# --- Mood --------------------------------------------------------------------------------------

section("Mood", "The tone of the sentences, from −1 (negative) to +1 (positive), scored by an AI model.")

candidates = charts.top_characters(analysis, 8)
left, right = panel("Mood by chapter", "The average tone of each chapter for the **whole book** (gray), next to "
                    "the tone of the sentences that mention the characters you pick. Smoothing averages "
                    "neighbouring chapters to show the trend.")
with left:
    chosen = st.multiselect("Characters", [c.name for c in candidates], default=[c.name for c in candidates[:2]],
                            max_selections=4, key="mood_characters")
    smooth = st.select_slider("Smoothing", options=[1, 3, 5, 7], value=3, key="mood_smooth")
ids = [c.id for c in candidates if c.name in chosen]
with right:
    st.plotly_chart(charts.story_sentiment(analysis, theme, ids, smooth), width="stretch")
    rows = []
    for i, chapter in enumerate(analysis.chapters):
        row = {"Chapter": chapter.title, "Whole book": round(analysis.chapter_sentiment[i], 3)}
        for c in candidates:
            if c.id in ids and analysis.sentiment_by_chapter[c.id][i] is not None:
                row[c.name] = round(analysis.sentiment_by_chapter[c.id][i], 3)
        rows.append(row)
    table(pd.DataFrame(rows))

moments = key_moments(analysis.sentences, window=20, n=3)
left, right = panel("Mood sentence by sentence", "The mood along the whole book, sentence by sentence: **blue** "
                    "above the line is brighter, **red** below is darker. ▼ and ▲ mark the darkest and brightest "
                    "passages, quoted below.\n\n**Detailed** follows the small ups and downs, **Broad** the "
                    "big movements.")
with left:
    detail = st.radio("Detail", ["Detailed", "Broad"], horizontal=True, key="mood_detail",
                      captions=["average of 15 sentences", "average of 60 sentences"])
with right:
    window = 15 if detail == "Detailed" else 60
    st.plotly_chart(charts.mood_arc(analysis, theme, rolling_sentiment(analysis.sentences, window), moments),
                    width="stretch")

left, right = panel("Key moments", "The passages of 20 sentences with the darkest and the brightest tone in the "
                    "book, so you can read what the numbers point at.")
with right:
    for column, kind, found in zip(st.columns(2), ("Darkest", "Brightest"), moments):
        with column:
            for n, m in enumerate(found, start=1):
                st.markdown(f"**{kind} {n}** · {analysis.chapters[m.chapter].title} · tone {m.score:+.2f}")
                st.markdown(f"> {passage(analysis, m)}")

# --- Emotions -----------------------------------------------------------------------------------

section("Emotions", "An AI model trained on classic books scores 38 fine emotions in every sentence; the "
        f"charts group them into 8 families. About {book_mix.get('neutral', 0):.0%} of this book is neutral "
        "narration; the charts show how the rest divides.")
if not has_emotions:
    st.info("Emotions were not detected for this book.")
else:
    left, right = panel("The book's emotional mix", "How the emotional (non-neutral) sentences of the book divide "
                        "between the 8 emotion families. Hover a bar to see which fine emotions it holds.")
    with right:
        st.plotly_chart(charts.emotion_bars(theme, book_mix), width="stretch")

    left, right = panel("The finer feelings", "The fine emotions behind the families: how strongly each one runs "
                        "through the book, on average per sentence. Each bar has its family's colour (gray = calm "
                        "feelings, which count as neutral).")
    with left:
        fine_top = st.slider("Emotions to show", 5, 38, 15, key="fine_top")
    with right:
        st.plotly_chart(charts.fine_bars(theme, book_fine, fine_top), width="stretch")

    left, right = panel("Emotions through the story", "How the mix of emotions changes from chapter to chapter. "
                        "Each colour band is one emotion family; a wider band means that family is a bigger part of "
                        "the chapter.")
    with left:
        smooth = st.select_slider("Smoothing", options=[1, 3, 5, 7], value=5, key="emotion_smooth")
    with right:
        st.plotly_chart(charts.emotion_journey(analysis, theme, smooth), width="stretch")
        table(pd.DataFrame([
            {"Chapter": c.title, **{charts.EMOTION_LABELS[e]: round(mix.get(e, 0), 3)
                                    for e in [*charts.EMOTION_ORDER, "neutral"]}}
            for c, mix in zip(analysis.chapters, analysis.chapter_emotions)
        ]))

    left, right = panel("A character's emotions", "The emotions of the sentences that mention one character "
                        "(in colour), next to the whole book (in gray). Bars longer than the gray ones are what "
                        "stands out about them, and the fine emotions most above the book's average are named.")
    with left:
        who = st.selectbox("Character", charts.top_characters(analysis, 20), format_func=lambda c: c.name,
                           key="emotion_character")
        if who.id in faces:
            st.html(f'<img src="{faces[who.id]}" alt="" style="width:96px;height:96px;border-radius:50%">')
        feels = stand_out(analysis.character_fine[who.id], book_fine) if analysis.character_fine else []
        if feels:
            st.markdown(f"**Stands out for {who.name}:** " + ", ".join(feels))
    with right:
        st.plotly_chart(charts.emotion_bars(theme, analysis.character_emotions[who.id], book_mix, name=who.name),
                        width="stretch")

# --- Characters ---------------------------------------------------------------------------------

section("Characters", "Who the book is about. Mentions count names and pronouns (\"she\", \"his\"); pronouns are "
        "linked by an AI model that is right about 3 times in 4, so treat counts as estimates.")

left, right = panel("Mentions", "How often each character is mentioned, **by name** and **by pronoun or "
                    "description**. Two names for one person (a nickname, a married name)? Merge them in the "
                    "sidebar.")
with left:
    top = how_many("Characters to show", len(analysis.characters), 15, "mentions_top")
with right:
    st.plotly_chart(charts.mentions_bars(analysis, theme, top, faces), width="stretch")
    by_name = pd.Series([m.character_id for m in analysis.mentions if m.source == "name"]).value_counts()
    table(pd.DataFrame([
        {"Character": c.name, "Mentions": c.mentions, "By name": int(by_name.get(c.id, 0)),
         "Also called": ", ".join(c.aliases[1:6])}
        for c in charts.top_characters(analysis, len(analysis.characters))
    ]))

left, right = panel("Where they appear", "Each row is a character, each column a chapter: the darker the "
                    "square, the more they are mentioned there. It shows who carries which part of the story.")
with left:
    top = how_many("Characters to show", len(analysis.characters), 15, "timeline_top")
with right:
    st.plotly_chart(charts.timeline_heatmap(analysis, theme, top), width="stretch")
    table(pd.DataFrame(
        {c.name: analysis.mentions_by_chapter[c.id] for c in charts.top_characters(analysis, top)},
        index=[ch.title for ch in analysis.chapters],
    ).reset_index(names="Chapter"))

# --- Relationships ------------------------------------------------------------------------------

section("Relationships", "Two characters are together when both are mentioned in the same or neighbouring "
        "sentences. A relationship's tone is the tone of those shared moments.")
if not analysis.relationships:
    st.info("No characters appear together often enough to show relationships.")
else:
    left, right = panel("Who is connected", "Each dot is a character (bigger = mentioned more). A line joins two "
                        "characters who share moments: **thicker** means together more often, and its **colour** "
                        "is the average tone of those moments (blue brighter, red darker).")
    with left:
        top = how_many("Characters in the network", len(analysis.characters), 20, "network_top")
        min_count = st.slider("Hide links with fewer moments together than", 3, 50, 10, key="network_min")
    with right:
        st.plotly_chart(charts.relationship_network(analysis, theme, top, min_count, faces), width="stretch")

    left, right = panel("How a relationship changes", "Pick a pair to follow through the book: the **tone** of "
                        "their shared moments chapter by chapter, **how often** they meet, and their **emotions** "
                        "in the early, middle and late book.")
    with left:
        pair_labels = [f"{names[r.source]} & {names[r.target]} ({r.count})" for r in analysis.relationships[:40]]
        picked = st.selectbox("Pair", range(len(pair_labels)), format_func=lambda i: pair_labels[i], key="pair")
        smooth = st.select_slider("Smoothing", options=[1, 3, 5, 7], value=5, key="pair_smooth")
    pair = analysis.relationships[picked]
    with right:
        st.plotly_chart(charts.pair_tone(analysis, theme, pair, smooth), width="stretch")
        st.plotly_chart(charts.pair_moments(analysis, theme, pair), width="stretch")
        if any(pair.emotions_by_part):
            st.plotly_chart(charts.pair_emotions(theme, pair), width="stretch")
        table(pd.DataFrame([
            {"Character": names[r.source], "With": names[r.target], "Moments together": r.count,
             "Average tone": round(r.sentiment, 3)}
            for r in analysis.relationships
        ]))

# --- Places ---------------------------------------------------------------------------------------

section("Places", "Places, organizations and other named things in the book.")
if not analysis.entities:
    st.info("No places or other entities were found.")
else:
    places = [e for e in analysis.entities if e.kind == "place"]
    if places:
        left, right = panel("Where the story happens", "Each row is a place, each column a chapter: the darker "
                            "the square, the more the place is mentioned there. It traces the story's journey.")
        with left:
            top = how_many("Places to show", len(places), 15, "places_top")
        with right:
            st.plotly_chart(charts.places_heatmap(analysis, theme, top), width="stretch")

    left, right = panel("Most mentioned", "The places, organizations and groups (such as families) named most "
                        "often in the book.")
    with right:
        kinds = [(k, label) for k, label in KINDS.items() if any(e.kind == k for e in analysis.entities)]
        for column, (kind, label) in zip(st.columns(len(kinds)), kinds):
            with column:
                st.markdown(f"**{label}**")
                st.plotly_chart(charts.entity_bars([e for e in analysis.entities if e.kind == kind][:10], theme),
                                width="stretch", key=f"entity_bars_{kind}")
        table(pd.DataFrame([
            {"Name": e.name, "Kind": KINDS.get(e.kind, e.kind), "spaCy type": ENTITY_TYPES.get(e.label, e.label),
             "Mentions": e.count}
            for e in analysis.entities
        ]))

# --- About ----------------------------------------------------------------------------------------

section("About", "Who made this, and why.")
st.html(design.about())

# --- The fun theme's raccoon buddy (last, so its hidden frame adds no gap at the top) ---------------

if look == "fun":
    fits = story_shape(analysis.sentences)[1]
    st.html(fun.buddy_html())
    components.html(fun.buddy_script(fun.book_facts(analysis, fits[0][0] if fits and fits[0][1] >= WEAK_FIT else None)),
                    height=0)
