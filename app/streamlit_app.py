"""Book Analyzer website. Run from the project folder:

    .venv\\Scripts\\streamlit run app\\streamlit_app.py
"""

import hashlib
import pickle
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so "analyzer" can be imported when Streamlit runs this file

import streamlit.components.v1 as components  # noqa: E402

import charts  # noqa: E402
import explore3d  # noqa: E402
from analyzer.emotions import average_emotions  # noqa: E402
from analyzer.merge import merge_characters  # noqa: E402
from analyzer.pipeline import ANALYSIS_VERSION, analyze  # noqa: E402
from analyzer.progression import key_moments, rolling_sentiment  # noqa: E402

SAMPLE = ROOT / "data" / "pride_and_prejudice.txt"
CACHE = ROOT / "results"  # finished analyses, so a book is only analyzed once
ENTITY_TYPES = {
    "GPE": "Country or city", "LOC": "Place", "FAC": "Building", "ORG": "Organization",
    "NORP": "Group or nationality", "EVENT": "Event", "WORK_OF_ART": "Title of a work",
}
KINDS = {"place": "Places", "organization": "Organizations", "group": "Groups and families", "other": "Other"}

st.set_page_config(page_title="Book Analyzer", page_icon="📖", layout="wide")
theme = charts.THEMES["dark" if st.context.theme.type == "dark" else "light"]


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
    bar = st.progress(0.0, text="Starting… a full novel takes about 7 minutes.")
    try:
        result = analyze(data, lambda step, f: bar.progress(min(f, 1.0), text=f"{step}… {f:.0%}"),
                         filename=filename)
    finally:
        bar.empty()
    CACHE.mkdir(exist_ok=True)
    saved.write_bytes(pickle.dumps(result))
    return result


# --- Upload and analysis ---------------------------------------------------

st.title("📖 Book Analyzer")
st.write("Upload an English novel as a `.txt` file to see its characters, how they relate, "
         "and how the mood changes through the story.")

uploaded = st.file_uploader("Book file", type=["txt"], label_visibility="collapsed")
if uploaded is not None:
    data, filename = uploaded.getvalue(), uploaded.name
elif SAMPLE.exists() and st.button("Or try it with *Pride and Prejudice*"):
    data, filename = SAMPLE.read_bytes(), SAMPLE.name
elif "current" in st.session_state:
    data, filename = None, None  # keep showing the last book
else:
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
analysis = merge_characters(book["analysis"], book["merges"]) if book["merges"] else book["analysis"]
if not analysis.characters:
    st.warning("No characters were found in this book.")
    st.stop()

# --- Sidebar: merge characters ----------------------------------------------

with st.sidebar:
    st.header("Merge characters")
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

st.subheader(book["title"])
if analysis.author:
    st.caption(f"by {analysis.author}")
with st.expander("✏️ Edit title"):
    new_title = st.text_input("Title", book["title"], key=f"title_{st.session_state['current']}")
    if new_title.strip() and new_title != book["title"]:
        book["title"] = new_title.strip()
        st.rerun()
has_emotions = any(analysis.chapter_emotions)
overview, mentions, mood, feelings, timeline, relations, entities, explore = st.tabs(
    ["Overview", "Mentions", "Story sentiment", "Emotions", "Timeline", "Relationships", "Places & entities",
     "Explore in 3D"]
)

# --- Overview -----------------------------------------------------------------

with overview:
    cols = st.columns(4)
    cols[0].metric("Chapters", len(analysis.chapters))
    cols[1].metric("Sentences", f"{len(analysis.sentences):,}")
    cols[2].metric("Characters", len(analysis.characters))
    cols[3].metric("Character mentions", f"{len(analysis.mentions):,}")

    ranked = sorted(range(len(analysis.chapters)), key=lambda i: analysis.chapter_sentiment[i])
    left, right = st.columns(2)
    with left:
        st.markdown("**Darkest chapters**")
        for i in ranked[:3]:
            st.write(f"{analysis.chapters[i].title} — tone {analysis.chapter_sentiment[i]:+.2f}")
    with right:
        st.markdown("**Brightest chapters**")
        for i in ranked[::-1][:3]:
            st.write(f"{analysis.chapters[i].title} — tone {analysis.chapter_sentiment[i]:+.2f}")

    st.markdown("**Main characters**")
    st.write(" · ".join(f"{c.name} ({c.mentions:,})" for c in charts.top_characters(analysis, 8)))

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
            "- **Emotions** come from a third AI model that picks one of seven for each sentence "
            "(most sentences in a novel are *neutral*). Its \"disgust\" mostly means disapproval or "
            "contempt, which classic novels are full of.\n"
            "- If a character appears twice under different names, merge them in the sidebar."
        )
    st.caption("Analysis time: " + ", ".join(f"{k} {v:.0f}s" for k, v in analysis.timings.items()))

# --- Mentions -------------------------------------------------------------------

with mentions:
    top = how_many("Characters to show", len(analysis.characters), 15, "mentions_top")
    st.plotly_chart(charts.mentions_bars(analysis, theme, top), width="stretch")
    by_name = pd.Series([m.character_id for m in analysis.mentions if m.source == "name"]).value_counts()
    table(pd.DataFrame([
        {"Character": c.name, "Mentions": c.mentions, "By name": int(by_name.get(c.id, 0)),
         "Also called": ", ".join(c.aliases[1:6])}
        for c in charts.top_characters(analysis, len(analysis.characters))
    ]))

# --- Story sentiment --------------------------------------------------------------

with mood:
    candidates = charts.top_characters(analysis, 8)
    left, right = st.columns([3, 1])
    chosen = left.multiselect(
        "Compare with characters (shows the tone of the sentences that mention them)",
        [c.name for c in candidates], default=[c.name for c in candidates[:2]], max_selections=4,
    )
    smooth = right.select_slider("Smoothing", options=[1, 3, 5, 7], value=3,
                                 help="Average over this many neighbouring chapters to show the trend")
    ids = [c.id for c in candidates if c.name in chosen]
    st.plotly_chart(charts.story_sentiment(analysis, theme, ids, smooth), width="stretch")
    rows = []
    for i, chapter in enumerate(analysis.chapters):
        row = {"Chapter": chapter.title, "Whole book": round(analysis.chapter_sentiment[i], 3)}
        for c in candidates:
            if c.id in ids and analysis.sentiment_by_chapter[c.id][i] is not None:
                row[c.name] = round(analysis.sentiment_by_chapter[c.id][i], 3)
        rows.append(row)
    table(pd.DataFrame(rows))

    st.markdown("#### Mood sentence by sentence")
    detail = st.radio("Detail", ["Detailed", "Broad"], horizontal=True, label_visibility="collapsed",
                      captions=["average of 15 sentences", "average of 60 sentences"])
    window = 15 if detail == "Detailed" else 60
    moments = key_moments(analysis.sentences, window=20, n=3)
    st.plotly_chart(charts.mood_arc(analysis, theme, rolling_sentiment(analysis.sentences, window), moments),
                    width="stretch")

    st.markdown("#### Key moments")
    st.caption("The passages of 20 sentences with the darkest and the brightest tone (marked ▼ and ▲ above).")
    for column, kind, found in zip(st.columns(2), ("Darkest", "Brightest"), moments):
        with column:
            for n, m in enumerate(found, start=1):
                st.markdown(f"**{kind} {n}** · {analysis.chapters[m.chapter].title} · tone {m.score:+.2f}")
                st.markdown(f"> {passage(analysis, m)}")

# --- Emotions -------------------------------------------------------------------------

with feelings:
    if not has_emotions:
        st.info("Emotions were not detected for this book.")
    else:
        book_mix = average_emotions([s.emotions for s in analysis.sentences])
        st.caption(f"About {book_mix.get('neutral', 0):.0%} of the text is neutral narration. The charts below "
                   "show how the rest divides between the six emotions.")
        st.markdown("#### The book's emotional mix")
        st.plotly_chart(charts.emotion_bars(theme, book_mix), width="stretch")

        st.markdown("#### Emotions through the story")
        smooth = st.select_slider("Smoothing  ", options=[1, 3, 5, 7], value=5, key="emotion_smooth",
                                  help="Average over this many neighbouring chapters to show the trend")
        st.plotly_chart(charts.emotion_journey(analysis, theme, smooth), width="stretch")
        table(pd.DataFrame([
            {"Chapter": c.title, **{charts.EMOTION_LABELS[e]: round(mix.get(e, 0), 3) for e in mix}}
            for c, mix in zip(analysis.chapters, analysis.chapter_emotions)
        ]))

        st.markdown("#### A character's emotions")
        st.caption("The emotions of the sentences that mention them, next to the whole book in gray.")
        options = charts.top_characters(analysis, 20)
        who = st.selectbox("Character", options, format_func=lambda c: c.name, key="emotion_character")
        st.plotly_chart(charts.emotion_bars(theme, analysis.character_emotions[who.id], book_mix, name=who.name),
                        width="stretch")

# --- Timeline -------------------------------------------------------------------------

with timeline:
    st.write("Where each character appears: darker means mentioned more in that chapter.")
    top = how_many("Characters to show", len(analysis.characters), 15, "timeline_top")
    st.plotly_chart(charts.timeline_heatmap(analysis, theme, top), width="stretch")
    shown = charts.top_characters(analysis, top)
    table(pd.DataFrame(
        {c.name: analysis.mentions_by_chapter[c.id] for c in shown},
        index=[ch.title for ch in analysis.chapters],
    ).reset_index(names="Chapter"))

# --- Relationships -------------------------------------------------------------------------

with relations:
    if not analysis.relationships:
        st.info("No characters appear together often enough to show relationships.")
    else:
        left, right = st.columns(2)
        with left:
            top = how_many("Characters in the network", len(analysis.characters), 20, "network_top")
        min_count = right.slider("Hide links with fewer moments together than", 3, 50, 10)
        st.caption("Bigger dot = mentioned more. Thicker line = together more often. "
                   "Line colour = average tone of their shared moments.")
        st.plotly_chart(charts.relationship_network(analysis, theme, top, min_count), width="stretch")

        st.markdown("#### How a relationship changes")
        names = {c.id: c.name for c in analysis.characters}
        labels = [f"{names[r.source]} & {names[r.target]} ({r.count})" for r in analysis.relationships[:40]]
        picked = st.selectbox("Pair", range(len(labels)), format_func=lambda i: labels[i])
        pair = analysis.relationships[picked]
        smooth = st.select_slider("Smoothing ", options=[1, 3, 5, 7], value=5, key="pair_smooth")
        st.plotly_chart(charts.pair_tone(analysis, theme, pair, smooth), width="stretch")
        st.plotly_chart(charts.pair_moments(analysis, theme, pair), width="stretch")
        if any(pair.emotions_by_part):
            st.markdown("**Their emotions in the early, middle and late book**")
            st.plotly_chart(charts.pair_emotions(theme, pair), width="stretch")
        table(pd.DataFrame([
            {"Character": names[r.source], "With": names[r.target], "Moments together": r.count,
             "Average tone": round(r.sentiment, 3)}
            for r in analysis.relationships
        ]))

# --- Explore in 3D -------------------------------------------------------------------------

SCENE_HELP = {
    "constellation": "Each character is a star. Left to right: darker to brighter tone. Bottom to top: early to "
                     "late in the book. Back to front: cold to warm emotions. Size = mentions, colour = strongest "
                     "emotion, lines = relationships. Click a star to see only its relationships.",
    "terrain": "Each character is a ridge running through the chapters. Height = how much they are mentioned, "
               "colour = the tone around them (red darker, blue brighter). Hover to read the values.",
    "crystal": "One character as a hologram: each spike is an emotion, as long as its share. The ring goes once "
               "round the book and rises (blue) in bright chapters and sinks (red) in dark ones.",
    "dna": "Two characters as the strands of a double helix. A rung joins them in every chapter where they "
           "share a moment: thicker when they meet more, coloured by tone. Gaps = chapters apart.",
    "tunnel": "Fly through the book. Each chapter is a ring split into its emotions; bright chapters open wide, "
              "dark chapters close in. Use the slider to jump to a chapter.",
}

with explore:
    scene = st.radio("Scene", list(explore3d.SCENES), format_func=explore3d.SCENES.get, horizontal=True,
                     label_visibility="collapsed", key="scene")
    st.caption(SCENE_HELP[scene] + " Drag to rotate. These views are for exploring; the other tabs give "
               "exact numbers.")
    if scene in explore3d.EMOTION_SCENES and not has_emotions:
        st.info("This scene needs emotions, which were not detected for this book.")
    else:
        components.html(explore3d.scene_html(analysis, scene), height=580)

# --- Entities -------------------------------------------------------------------------------

with entities:
    if not analysis.entities:
        st.info("No places or other entities were found.")
    else:
        places = [e for e in analysis.entities if e.kind == "place"]
        if places:
            st.markdown("#### Where the story happens")
            st.caption("Places by chapter: darker means mentioned more in that chapter.")
            top = how_many("Places to show", len(places), 15, "places_top")
            st.plotly_chart(charts.places_heatmap(analysis, theme, top), width="stretch")

        st.markdown("#### Most mentioned")
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
