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

import charts  # noqa: E402
from analyzer.merge import merge_characters  # noqa: E402
from analyzer.pipeline import analyze  # noqa: E402

SAMPLE = ROOT / "data" / "pride_and_prejudice.txt"
CACHE = ROOT / "results"  # finished analyses, so a book is only analyzed once
ENTITY_TYPES = {
    "GPE": "Country or city", "LOC": "Place", "FAC": "Building", "ORG": "Organization",
    "NORP": "Group or nationality", "EVENT": "Event", "WORK_OF_ART": "Title of a work",
}

st.set_page_config(page_title="Book Analyzer", page_icon="📖", layout="wide")
theme = charts.THEMES["dark" if st.context.theme.type == "dark" else "light"]


def table(df: pd.DataFrame) -> None:
    with st.expander("Show as table"):
        st.dataframe(df, hide_index=True, width="stretch")


def how_many(label: str, available: int, default: int, key: str) -> int:
    """Slider for how many characters to show (no slider for tiny casts)."""
    if available <= 5:
        return available
    return st.slider(label, 5, min(40, available), min(default, available), key=key)


def run_analysis(data: bytes, key: str):
    """Analyze the book, or load the saved result if it was analyzed before.
    The file is never stored, only the analysis results."""
    saved = CACHE / f"{key}.pkl"
    if saved.exists():
        return pickle.loads(saved.read_bytes())
    bar = st.progress(0.0, text="Starting… a full novel takes about 7 minutes.")
    try:
        result = analyze(data, lambda step, f: bar.progress(min(f, 1.0), text=f"{step}… {f:.0%}"))
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
    data, title = uploaded.getvalue(), uploaded.name
elif SAMPLE.exists() and st.button("Or try it with *Pride and Prejudice*"):
    data, title = SAMPLE.read_bytes(), "Pride and Prejudice"
elif "current" in st.session_state:
    data, title = None, None  # keep showing the last book
else:
    st.stop()

analyses = st.session_state.setdefault("analyses", {})
if data is not None:
    key = hashlib.sha256(data).hexdigest()
    if key not in analyses:
        try:
            analyses[key] = {"title": title, "analysis": run_analysis(data, key), "merges": []}
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
overview, mentions, mood, timeline, relations, entities = st.tabs(
    ["Overview", "Mentions", "Story sentiment", "Timeline", "Relationships", "Entities"]
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
        table(pd.DataFrame([
            {"Character": names[r.source], "With": names[r.target], "Moments together": r.count,
             "Average tone": round(r.sentiment, 3)}
            for r in analysis.relationships
        ]))

# --- Entities -------------------------------------------------------------------------------

with entities:
    st.write("Places, organizations and other named things in the book.")
    if analysis.entities:
        st.dataframe(pd.DataFrame([
            {"Name": e.name, "Type": ENTITY_TYPES.get(e.label, e.label), "Mentions": e.count}
            for e in analysis.entities
        ]), hide_index=True, width="stretch", height=500)
    else:
        st.info("No other entities were found.")
