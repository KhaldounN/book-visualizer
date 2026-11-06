"""The look of the website: page styling, the hero banner and the KPI cards.

Everything here returns HTML/CSS strings that the app shows with `st.html`.
Colours come from `charts.THEMES`, so light and dark mode both work.
"""

import base64
import re
from functools import cache
from html import escape
from pathlib import Path

import charts
from analyzer.dialogue import find_lines, words_spoken
from analyzer.emotions import FAMILIES, average_emotions, book_average
from analyzer.models import BookAnalysis

ASSETS = Path(__file__).with_name("assets")
# The mascot (the owner's raccoon) says what it is doing during each analysis step
MASCOT_LINES = {
    "Reading sentences": "Reading the book, one sentence at a time. Snack breaks included.",
    "Finding characters": "Writing every name on a sticky note.",
    "Linking pronouns": "Working out who “she” is. Harder than it sounds.",
    "Scoring sentiment": "Deciding whether each sentence is happy or sad. Some are both.",
    "Detecting emotions": "Feeling all 38 feelings. Pass the tissues.",
    "Naming chapters": "Giving every chapter a catchy nickname.",
    "Finding relationships": "Figuring out who is friends with whom.",
}
MASCOT_TIPS = (
    "A whole novel takes about 10 minutes. Perfect for a cup of tea ☕",
    "Everything runs on this computer: your book never leaves it.",
    "The raccoon reads about a thousand sentences a minute. Don't tell its teacher.",
    "When it's done, try ▶ Travel on the Story road.",
)
SERIF = '"Newsreader", "Iowan Old Style", Georgia, "Times New Roman", serif'
SANS = 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif'
# One accent, used only for rules and small labels (never for data): a deep oxblood on the
# light paper, a soft copper in dark mode
ACCENT = {"light": "#8a2b1f", "dark": "#e0957a"}
PAGE = {"light": "#fbfaf6", "dark": "#121110"}  # the page background (.streamlit/config.toml)


def page_css(theme: dict, mode: str) -> str:
    """Styling for the whole page, in the manner of a scholarly edition: a masthead, numbered
    parts and figures, hairline rules, small capitals and serif type."""
    t, gold = theme, ACCENT[mode]
    return f"""<style>
    :root {{ --ba-ink: {t["ink"]}; --ba-ink2: {t["ink2"]}; --ba-muted: {t["muted"]}; --ba-line: {t["grid"]};
             --ba-rule: {t["axis"]}; --ba-surface: {t["surface"]}; --ba-gold: {gold}; --ba-glow: none;
             --ba-radius: 4px; --ba-dark: {t["diverging"][0]}; --ba-bright: {t["diverging"][2]};
             --ba-page: {PAGE[mode]}; }}

    /* The masthead: the name of the site over a double rule, like the head of a journal */
    .ba-top {{ display: flex; align-items: flex-end; justify-content: space-between; gap: .6rem 1.5rem; flex-wrap: wrap;
        padding: .4rem 0 1rem; margin-bottom: 4px; border-bottom: 1px solid var(--ba-ink);
        box-shadow: 0 3px 0 var(--ba-page), 0 4px 0 var(--ba-ink); }}  /* a thin double rule */
    .ba-top .ba-mark b {{ display: block; font: 500 2rem/1 {SERIF}; letter-spacing: -.01em; color: var(--ba-ink); }}
    .ba-top .ba-mark span {{ display: block; margin-top: .45rem; font: italic 400 .98rem/1.2 {SERIF}; color: var(--ba-ink2); }}
    .ba-top .ba-meta {{ display: flex; flex-direction: column; align-items: flex-end; gap: .35rem; text-align: right; }}
    .ba-top .ba-meta .book {{ font: italic 500 1.05rem/1.2 {SERIF}; color: var(--ba-ink); max-width: 26rem;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .ba-sc {{ font: 600 .66rem/1.2 {SANS}; letter-spacing: .16em; text-transform: uppercase; color: var(--ba-muted); }}

    /* The tabs are the site's navigation: small capitals, sticky at the top while you scroll
       (Streamlit tabs: [role=tablist] holding [data-testid=stTab] items) */
    .stMainBlockContainer .stTabs [role="tablist"] {{ position: sticky; top: 3.75rem; z-index: 90;
        background: var(--ba-page); gap: .4rem; border-bottom: 1px solid var(--ba-rule); height: auto; padding-top: .2rem; }}
    .stMainBlockContainer [data-testid="stTab"] {{ padding: .85rem .9rem .8rem; border-bottom: 2px solid transparent;
        margin-bottom: -1px; transition: border-color .2s ease; }}
    .stMainBlockContainer [data-testid="stTab"] p {{ font: 600 .74rem/1 {SANS}; letter-spacing: .14em;
        text-transform: uppercase; color: var(--ba-muted); }}
    .stMainBlockContainer [data-testid="stTab"][aria-selected="true"] {{ border-bottom-color: var(--ba-gold); }}
    .stMainBlockContainer [data-testid="stTab"][aria-selected="true"] p,
    .stMainBlockContainer [data-testid="stTab"]:hover p {{ color: var(--ba-ink); }}
    .stMainBlockContainer [data-baseweb="tab-highlight"], .stMainBlockContainer [data-baseweb="tab-border"] {{ display: none; }}
    [data-testid="stHeader"] {{ background: var(--ba-page); }}

    /* The colophon at the bottom of every page */
    .ba-foot {{ margin-top: 4rem; padding: 1.3rem 0 .6rem; border-top: 1px solid var(--ba-rule);
        box-shadow: inset 0 3px 0 var(--ba-page), inset 0 4px 0 var(--ba-rule);
        display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; font-size: .8rem; color: var(--ba-muted); }}
    .ba-foot b {{ font: 500 1rem/1 {SERIF}; color: var(--ba-ink); margin-right: .5rem; }}
    .ba-foot a {{ color: var(--ba-ink2); text-decoration: none; border-bottom: 1px solid var(--ba-rule); }}
    .ba-foot a:hover {{ color: var(--ba-ink); border-color: var(--ba-gold); }}

    /* Parts and figures are numbered, as in a printed study: each tab starts again at Part I, Figure 1 */
    .stMainBlockContainer [data-testid="stHeading"] h2 {{ counter-increment: part;
        font-family: {SERIF}; font-size: 2.35rem; font-weight: 500; letter-spacing: -.015em; line-height: 1.15;
        padding: 2.4rem 0 .6rem; border-bottom: 1px solid var(--ba-rule); }}
    .stMainBlockContainer [data-testid="stHeading"] h2::before {{ content: "Part " counter(part, upper-roman);
        display: block; margin-bottom: .55rem; font: 600 .7rem/1 {SANS}; letter-spacing: .18em; text-transform: uppercase;
        color: var(--ba-gold); }}
    .stMainBlockContainer h4 {{ font-family: {SERIF}; font-weight: 500; font-size: 1.45rem; line-height: 1.25;
        letter-spacing: -.005em; }}
    .stMainBlockContainer blockquote {{ border-left: 2px solid var(--ba-gold); padding: .1rem 0 .1rem 1rem; margin: .4rem 0 .8rem; }}
    .stMainBlockContainer blockquote p {{ font: italic 400 1.08rem/1.55 {SERIF}; color: var(--ba-ink2); }}

    /* Each visualization is a figure on its own white plate, with a numbered label */
    [class*="st-key-panel-"] {{ counter-increment: fig;
        background: var(--ba-surface); border: 1px solid var(--ba-line) !important; border-radius: var(--ba-radius);
        padding: 1.5rem 1.7rem 1.6rem; }}
    [class*="st-key-panel-"] h4:not(article h4)::before {{  /* the figure title, not a chapter card's heading */ content: "Figure " counter(fig); display: block; margin-bottom: .55rem;
        font: 600 .68rem/1 {SANS}; letter-spacing: .16em; text-transform: uppercase; color: var(--ba-gold); }}
    [class*="st-key-panel-"] [data-testid="stMarkdownContainer"] p {{ line-height: 1.6; }}

    /* The title page of the book */
    .ba-hero {{ position: relative; padding: 2.6rem 0 1.6rem; }}
    .ba-kicker {{ font: 600 .7rem/1.3 {SANS}; letter-spacing: .18em; text-transform: uppercase; color: var(--ba-gold); }}
    .ba-hero h1 {{ font-family: {SERIF}; font-size: clamp(2.6rem, 6vw, 4.6rem); line-height: 1.02; margin: .8rem 0 .5rem;
        font-weight: 500; letter-spacing: -.025em; color: var(--ba-ink); padding: 0; }}
    .ba-author {{ font: italic 400 1.35rem/1.3 {SERIF}; color: var(--ba-ink2); }}
    .ba-lede {{ max-width: 44rem; color: var(--ba-ink2); margin: 1.2rem 0 1.6rem; font: 400 1.12rem/1.6 {SERIF}; }}
    .ba-lede b {{ font-weight: 600; }}
    .ba-figure {{ margin: 0; padding: 1.2rem 1.3rem 1rem; background: var(--ba-surface); border: 1px solid var(--ba-line);
        border-radius: var(--ba-radius); }}
    .ba-figure figcaption {{ margin-top: .8rem; font-size: .8rem; line-height: 1.5; color: var(--ba-muted); }}
    .ba-figure figcaption b {{ font: 600 .68rem/1 {SANS}; letter-spacing: .16em; text-transform: uppercase;
        color: var(--ba-gold); margin-right: .4rem; }}
    .ba-ribbon {{ display: flex; align-items: flex-end; gap: 2px; height: 74px; }}
    .ba-ribbon i {{ flex: 1; min-width: 2px; border-radius: 1px 1px 0 0; transition: transform .15s ease; transform-origin: bottom; }}
    .ba-ribbon i:hover {{ transform: scaleY(1.12); filter: brightness(1.15); }}
    .ba-axis {{ display: flex; justify-content: space-between; font-size: .72rem; color: var(--ba-muted);
        border-top: 1px solid var(--ba-rule); padding-top: .4rem; margin-top: 2px; letter-spacing: .04em; }}
    .ba-legend {{ display: flex; flex-wrap: wrap; gap: .4rem 1.1rem; margin-top: .9rem; font-size: .78rem; color: var(--ba-ink2); }}
    .ba-legend span {{ display: inline-flex; align-items: center; gap: .4rem; }}
    .ba-legend i {{ width: 9px; height: 9px; border-radius: 1px; display: inline-block; }}

    .ba-chips > div:last-child {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: .4rem .45rem;
        margin: .6rem 0 1rem; }}
    .ba-chips span {{ font-family: {SERIF}; font-style: italic; color: var(--ba-ink); padding: .1rem .55rem;
        border-radius: 999px; line-height: 1.4; }}
    .ba-focus {{ margin-top: 1rem; padding: 1.1rem 1.3rem; border: 1px solid var(--ba-line);
        border-left: 3px solid var(--ba-gold); border-radius: var(--ba-radius); background: var(--ba-surface); }}
    .ba-focus h3 {{ font: 500 1.5rem/1.25 {SERIF}; color: var(--ba-ink); margin: .4rem 0 .6rem; padding: 0; }}
    .ba-focus blockquote {{ margin: 0 0 .9rem; padding-left: .9rem; border-left: 2px solid var(--ba-line);
        font: italic 400 1.05rem/1.55 {SERIF}; color: var(--ba-ink2); }}
    .ba-focus p {{ font-size: .85rem; color: var(--ba-ink2); margin: .2rem 0 .4rem; }}
    .ba-peaks {{ margin-top: 1.2rem; }}
    .ba-peaks ul {{ list-style: none; padding: 0; margin: .5rem 0 0; display: grid; gap: .3rem; font-size: .85rem;
        color: var(--ba-ink); }}
    .ba-peaks li {{ display: flex; align-items: center; gap: .4rem; margin: 0; }}
    .ba-peaks i {{ width: 9px; height: 9px; border-radius: 2px; flex: none; }}
    .ba-peaks span {{ color: var(--ba-muted); }}
    .ba-who {{ display: flex; flex-wrap: wrap; gap: .3rem .9rem; margin: -.2rem 0 .5rem; font-size: .8rem;
        color: var(--ba-ink2); }}
    .ba-who span {{ display: inline-flex; align-items: center; gap: .35rem; }}
    .ba-brief {{ margin: 1.8rem 0 0; max-width: 50rem; }}
    .ba-brief p {{ margin: .6rem 0 0; font: 400 1.18rem/1.65 {SERIF}; color: var(--ba-ink); }}
    .ba-brief b {{ font-weight: 600; }}

    /* The headline numbers: a compact strip of small tiles (8 in a row), the two key chapters below */
    .ba-kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .55rem; margin: 1.4rem 0 .4rem; }}
    .ba-kpi {{ position: relative; background: var(--ba-surface); padding: .65rem .75rem .7rem; border: 1px solid var(--ba-line);
        border-radius: 8px; display: flex; align-items: center; gap: .8rem; min-width: 0; overflow: hidden;
        transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }}
    .ba-kpi::before {{ content: ""; position: absolute; inset: 0 0 auto 0; height: 2px; background: var(--tone, var(--ba-gold)); opacity: .7; }}
    .ba-kpi:hover {{ transform: translateY(-2px); border-color: var(--ba-rule); box-shadow: 0 10px 22px -16px rgba(0,0,0,.4); }}
    .ba-kpi .head {{ flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; gap: .18rem; }}
    .ba-kpi.wide {{ grid-column: span 2; padding: .6rem .9rem; }}
    .ba-kpi.wide .head {{ flex: none; max-width: 42%; }}
    .ba-kpi .label {{ font: 600 .6rem/1.2 {SANS}; letter-spacing: .12em; text-transform: uppercase; color: var(--ba-muted);
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .ba-kpi .label i {{ font-style: normal; margin-right: .3rem; letter-spacing: 0; }}
    .ba-kpi .value {{ font-family: {SERIF}; font-size: 1.55rem; font-weight: 500; line-height: 1.1; color: var(--ba-ink);
        letter-spacing: -.01em; font-variant-numeric: lining-nums tabular-nums;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
    .ba-kpi .value.small {{ font-size: 1.02rem; line-height: 1.2; }}
    .ba-kpi .note {{ font-size: .68rem; color: var(--ba-ink2); line-height: 1.35; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .ba-kpi .art {{ flex: 0 0 38%; min-width: 0; }}
    .ba-kpi .art:empty {{ display: none; }}
    .ba-kpi.wide .art {{ flex: 1; }}
    .ba-kpi img.spark {{ display: block; width: 100%; height: 30px; }}
    .ba-kpi svg {{ display: block; width: 100%; height: 20px; overflow: visible; }}
    .ba-kpi .ba-faces span {{ width: 22px; height: 22px; margin-right: -6px; border-width: 1.5px; font-size: .6rem; }}
    .ba-kpi .ba-faces img {{ width: 100%; height: 100%; }}
    .ba-kpi .ba-bar {{ height: 6px; }}
    .ba-kpi .ba-gauge {{ height: 6px; margin: 6px 0 4px; }}
    .ba-kpi .ba-gauge b {{ top: -4px; height: 14px; }}
    .ba-kpi .ba-chip {{ font-size: .55rem; padding: .22rem .4rem; }}
    .ba-kpi blockquote {{ margin: 0 !important; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
        overflow: hidden; font-size: .88rem !important; line-height: 1.4 !important; }}
    @media (max-width: 760px) {{ .ba-kpi.wide {{ grid-column: 1 / -1; }} }}
    @media (max-width: 1000px) {{ .ba-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 560px) {{ .ba-kpis {{ gap: .45rem; }} .ba-kpi {{ flex-direction: column; align-items: stretch; gap: .3rem; }}
        .ba-kpi .art {{ flex: none; }} .ba-kpi.wide .head {{ max-width: none; }} }}
    .ba-bar {{ display: flex; height: 8px; border-radius: 1px; overflow: hidden; gap: 2px; }}
    .ba-gauge {{ position: relative; height: 8px; border-radius: 1px;
        background: linear-gradient(90deg, var(--ba-dark), {t["diverging"][1]}, var(--ba-bright)); }}
    .ba-gauge b {{ position: absolute; top: -5px; width: 3px; height: 18px; margin-left: -1.5px; border-radius: 1px;
        background: var(--ba-ink); box-shadow: 0 0 0 2px var(--ba-surface); }}
    .ba-faces {{ display: flex; }}
    .ba-faces span {{ width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center; color: #fff;
        font: 600 .8rem/1 {SANS}; border: 2px solid var(--ba-surface); margin-right: -8px; }}
    .ba-chip {{ display: inline-block; vertical-align: middle; font: 600 .62rem/1 {SANS}; letter-spacing: .12em;
        text-transform: uppercase; padding: .3rem .5rem; border-radius: 2px; color: #fff; }}
    .ba-kpi blockquote {{ margin: .25rem 0 0; padding: 0 0 0 .9rem; border-left: 2px solid var(--tone);
        font-family: {SERIF}; font-style: italic; font-size: 1.05rem; line-height: 1.5; color: var(--ba-ink2); }}


    /* One continuous page: a sticky table of contents (it replaced the tabs) */
    /* sticky on Streamlit's wrapper box around the container (a sticky box only sticks inside its parent) */
    div:has(> .st-key-toc) {{ position: sticky; top: 3.75rem; z-index: 90; }}
    .st-key-toc {{ background: var(--ba-page); border-bottom: 1px solid var(--ba-rule); }}
    .ba-toc {{ display: flex; flex-wrap: wrap; gap: .2rem 1.05rem; padding: .85rem 0 .75rem; }}
    .ba-toc a {{ font: 600 .68rem/1 {SANS}; letter-spacing: .1em; text-transform: uppercase; color: var(--ba-muted);
        text-decoration: none; padding: .2rem 0; border-bottom: 2px solid transparent; }}
    .ba-toc a:hover {{ color: var(--ba-ink); border-bottom-color: var(--ba-gold); }}
    .stMainBlockContainer {{ counter-reset: part fig; }}
    .stMainBlockContainer [id] {{ scroll-margin-top: 8.5rem; }}  /* a jump stops below the sticky contents bar */
    /* phones: the contents bar is one line you swipe sideways, and charts drop their toolbar */
    @media (max-width: 640px) {{
        .ba-toc {{ flex-wrap: nowrap; overflow-x: auto; gap: 1.1rem; padding: .7rem 0 .6rem; scrollbar-width: none;
            -webkit-overflow-scrolling: touch; }}
        .ba-toc::-webkit-scrollbar {{ display: none; }}
        .ba-toc a {{ flex: none; }}
        .stMainBlockContainer [id] {{ scroll-margin-top: 6rem; }}
        .modebar-container {{ display: none !important; }}
        [class*="st-key-panel-"] {{ padding: 1.1rem 1rem 1.2rem; }}
        .ba-top .ba-mark b {{ font-size: 1.6rem; }}
    }}


    /* The mascot's emblem, and its notes */
    .ba-emblem {{ flex: none; }}
    /* How it works as a pipeline run (pipeline_dag): task boxes, flowing connectors, a fan-out */
    .ba-dag {{ margin: .6rem 0 1.6rem; border: 1px solid var(--ba-line); border-radius: 10px; background: var(--ba-surface);
        overflow: hidden; }}
    .ba-dag-bar {{ display: flex; flex-wrap: wrap; gap: .4rem 1.2rem; align-items: center; padding: .6rem 1rem;
        border-bottom: 1px solid var(--ba-line); font: 500 .74rem/1.2 {SANS}; color: var(--ba-muted); }}
    .ba-dag-bar .name {{ color: var(--ba-ink); font-weight: 600; }}
    .ba-dag-bar code, .ba-node code {{ font: 600 .76rem/1 ui-monospace, "Cascadia Code", Consolas, monospace;
        color: var(--ba-ink); background: none; padding: 0; }}
    .ba-dag-bar .state {{ color: #1f8a4c; font-weight: 600; }} .ba-dag-bar .local {{ margin-left: auto; }}
    .ba-dag i.ok {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: #23a35a;
        margin-right: .4rem; box-shadow: 0 0 0 3px rgba(35,163,90,.18); vertical-align: middle; }}
    .ba-dag-flow {{ display: flex; align-items: center; gap: 0; padding: 1.2rem .8rem 1rem; overflow-x: auto;
        background-image: radial-gradient(var(--ba-line) 1px, transparent 1px); background-size: 14px 14px; }}
    .ba-dag .stage {{ display: flex; align-items: center; flex: none; }}
    .ba-dag-flow > :first-child {{ margin-left: auto; }} .ba-dag-flow > :last-child {{ margin-right: auto; }}  /* centred, yet scrollable when too wide */
    .ba-dag .stage.fan {{ flex-direction: column; gap: .45rem; padding: 1.5rem .9rem .6rem; position: relative;
        border-left: 2px solid var(--ba-rule); border-right: 2px solid var(--ba-rule); border-radius: 12px; }}
    .ba-dag .fan-label {{ position: absolute; top: .3rem; left: 0; right: 0; text-align: center;
        font: 600 .58rem/1 {SANS}; letter-spacing: .1em; text-transform: uppercase; color: var(--ba-muted); }}
    .ba-dag .arrow {{ flex: none; width: 18px; height: 2px; position: relative; overflow: hidden;
        background: repeating-linear-gradient(90deg, var(--ba-gold) 0 6px, transparent 6px 11px);
        background-size: 22px 2px; animation: ba-flow 1s linear infinite; }}
    .ba-dag .arrow::after {{ content: ""; position: absolute; right: 0; top: -3px; border: 4px solid transparent;
        border-left-color: var(--ba-gold); border-right: 0; }}
    .ba-node.par {{ position: relative; }}
    .ba-node.par::before, .ba-node.par::after {{ content: ""; position: absolute; top: 50%; width: .9rem; height: 2px;
        background: repeating-linear-gradient(90deg, var(--ba-gold) 0 4px, transparent 4px 7px);
        background-size: 14px 2px; animation: ba-flow 1s linear infinite; }}
    .ba-node.par::before {{ right: 100%; }} .ba-node.par::after {{ left: 100%; }}
    @keyframes ba-flow {{ to {{ background-position: 22px 0; }} }}
    .ba-node {{ box-sizing: border-box; width: 9.4rem; background: var(--ba-page); border: 1px solid var(--ba-line); border-radius: 8px;
        padding: .55rem .7rem .6rem; box-shadow: 0 6px 16px -12px rgba(0,0,0,.35); border-left: 3px solid #23a35a; }}
    .ba-node.par {{ width: 13rem; padding: .45rem .7rem .5rem; }}
    .ba-node .top {{ display: flex; align-items: center; gap: .1rem; }}
    .ba-node .took {{ font: 500 .66rem/1 {SANS}; color: var(--ba-muted); white-space: nowrap; }}
    .ba-node p {{ margin: .35rem 0 .2rem; font-size: .76rem; line-height: 1.3; color: var(--ba-ink2); }}
    .ba-node .model {{ font: 600 .7rem/1.25 {SANS}; color: var(--ba-gold); }}
    .ba-node .libs {{ display: flex; flex-wrap: wrap; gap: .3rem; margin-top: .4rem; }}
    .ba-logo {{ display: inline-flex; align-items: center; justify-content: center; height: 22px; min-width: 22px;
        padding: 0 4px; border-radius: 5px; background: #fff; border: 1px solid #e3e0d8; }}
    .ba-logo img {{ width: 15px; height: 15px; display: block; }}
    .ba-logo.text {{ font: 600 .6rem/1 {SANS}; color: #2b5d8a; padding: 0 6px; }}
    .ba-dag figcaption {{ padding: .6rem 1rem .8rem; font-size: .78rem; color: var(--ba-muted); border-top: 1px solid var(--ba-line); }}
    @media (prefers-reduced-motion: reduce) {{ .ba-dag .arrow, .ba-node.par::before, .ba-node.par::after {{ animation: none; }} }}
    .ba-anim-box {{ margin: .4rem 0 1.4rem; padding: 1rem 1rem .4rem; background: var(--ba-surface);
        border: 1px solid var(--ba-line); border-radius: var(--ba-radius); }}
    .ba-anim {{ display: block; width: 100%; height: auto; }}
    .ba-anim.em-{'dark' if mode == 'light' else 'light'} {{ display: none; }}
    .ba-emblem.em-{'dark' if mode == 'light' else 'light'} {{ display: none; }}
    .ba-top .ba-mark {{ display: flex; align-items: center; gap: .9rem; text-decoration: none !important; color: inherit; }}
    .ba-foot .ba-emblem {{ vertical-align: -5px; margin-right: .45rem; }}
    .ba-rnote {{ display: flex; gap: .9rem; align-items: flex-start; max-width: 46rem; margin: 0 0 2rem; }}
    .ba-rnote p {{ margin: 0; font: italic 400 1.02rem/1.55 {SERIF}; color: var(--ba-ink2); }}
    .ba-rnote b {{ font: 600 .66rem/1 {SANS}; font-style: normal; letter-spacing: .16em; text-transform: uppercase;
        color: var(--ba-gold); margin-right: .3rem; }}

    /* How it works: what kind of AI this is, and the workflow */
    .ba-how h3 {{ font: 500 1.6rem/1.2 {SERIF}; color: var(--ba-ink); margin: .5rem 0 1rem; padding: 0; }}
    .ba-note {{ margin: 1.6rem 0 2.4rem; padding: 1.4rem 1.6rem; background: var(--ba-surface);
        border: 1px solid var(--ba-line); border-left: 3px solid var(--ba-gold); border-radius: var(--ba-radius); }}
    .ba-note p {{ max-width: 48rem; font: 400 1.05rem/1.6 {SERIF}; color: var(--ba-ink2); margin: 0 0 .7rem; }}
    .ba-note p.fine {{ font: 400 .82rem/1.55 {SANS}; color: var(--ba-muted); margin: 0; }}
    .ba-flow {{ list-style: none; margin: 0; padding: 0; counter-reset: none; }}
    .ba-flow li {{ position: relative; display: grid; grid-template-columns: 2.6rem minmax(0, 1.6fr) minmax(0, 1fr) minmax(0, 1fr);
        gap: 1.2rem; align-items: start; padding: 1rem 0; border-top: 1px solid var(--ba-line); margin: 0; }}
    .ba-flow li:last-child {{ border-bottom: 1px solid var(--ba-line); }}
    .ba-flow li:not(:last-child)::after {{ content: ""; position: absolute; left: 1.3rem; top: 3.4rem; bottom: -1rem;
        width: 1px; background: var(--ba-rule); }}  /* the line joining the steps */
    .ba-flow .n {{ width: 2.6rem; height: 2.6rem; border-radius: 50%; display: grid; place-items: center;
        border: 1px solid var(--ba-gold); color: var(--ba-gold); font: 500 1.15rem/1 {SERIF}; background: var(--ba-page);
        position: relative; z-index: 1; }}
    .ba-flow b {{ display: block; font: 500 1.2rem/1.3 {SERIF}; color: var(--ba-ink); }}
    .ba-flow p {{ margin: .25rem 0 0; font-size: .86rem; line-height: 1.55; color: var(--ba-ink2); }}
    .ba-flow .tool code {{ display: inline-block; font-size: .78rem; padding: .2rem .45rem; border-radius: 3px;
        background: var(--ba-surface); border: 1px solid var(--ba-line); color: var(--ba-ink); }}
    .ba-flow .tool span {{ display: block; margin-top: .35rem; font: 600 .62rem/1.2 {SANS}; letter-spacing: .14em;
        text-transform: uppercase; color: var(--ba-muted); }}
    .ba-flow .out {{ font: italic 400 .98rem/1.45 {SERIF}; color: var(--ba-ink2); }}
    .ba-flow-note {{ margin: 1rem 0 0; font-size: .82rem; color: var(--ba-muted); }}
    @media (max-width: 760px) {{ .ba-flow li {{ grid-template-columns: 2.6rem minmax(0, 1fr); }}
        .ba-flow .tool, .ba-flow .out {{ grid-column: 2; }} }}

    .st-key-start-picker {{ max-width: 30rem; margin: .4rem 0 1rem; }}
    .st-key-start-picker label p {{ font: 600 .7rem/1.3 {SANS} !important; letter-spacing: .16em; text-transform: uppercase;
        color: var(--ba-gold); }}
    /* The start page: what the site does, in three steps */
    .ba-method {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0; margin: 2rem 0 .5rem;
        border-top: 1px solid var(--ba-rule); }}
    .ba-method div {{ padding: 1.1rem 1.4rem 0 0; }}
    .ba-method div + div {{ padding-left: 1.4rem; border-left: 1px solid var(--ba-line); }}
    .ba-method b {{ display: block; font: 500 1.25rem/1.25 {SERIF}; color: var(--ba-ink); margin: .45rem 0 .35rem; }}
    .ba-method p {{ margin: 0; font-size: .88rem; line-height: 1.55; color: var(--ba-ink2); }}

    .ba-cast {{ list-style: none; padding: 0; margin: 0; display: grid; gap: .3rem; font-size: .88rem; }}
    .ba-cast li {{ display: flex; align-items: center; gap: .5rem; margin: 0; }}
    .ba-cast i {{ width: 12px; height: 12px; border-radius: 50%; flex: none; }}
    .ba-avatar {{ border-radius: 50%; flex: none; vertical-align: middle; }}
    .ba-dot {{ display: inline-block; border-radius: 50%; flex: none; vertical-align: middle; }}
    .ba-faces img {{ margin-right: -6px; }}
    /* the cast: one row of portraits side by side, no boxes (details in each portrait's tooltip) */
    .ba-castrow {{ margin: 1.8rem 0 .4rem; }}
    .ba-castrow .row {{ display: flex; gap: .3rem; margin-top: .55rem; overflow-x: auto; scrollbar-width: thin;
        padding-bottom: .2rem; }}
    .ba-castrow figure {{ flex: 1 0 5.6rem; max-width: 8rem; margin: 0; display: flex; flex-direction: column;
        align-items: center; text-align: center; gap: .15rem; cursor: help; }}
    .ba-castrow figure img {{ transition: transform .2s ease; }}
    .ba-castrow figure:hover img {{ transform: translateY(-3px) scale(1.05); }}
    .ba-castrow b {{ font: 500 .98rem/1.15 {SERIF}; margin-top: .2rem; }}
    .ba-castrow .role {{ font: 600 .56rem/1.25 {SANS}; letter-spacing: .08em; text-transform: uppercase;
        color: var(--ba-muted); }}
    .ba-castrow .note {{ font-size: .72rem; color: var(--ba-muted); margin: .4rem 0 0; }}
    .ba-castgrid {{ margin: 2.6rem 0 .4rem; }}
    .ba-castgrid h3 {{ font: 500 2rem/1.15 {SERIF}; letter-spacing: -.015em; color: var(--ba-ink); margin: .5rem 0 0;
        padding: 0 0 .6rem; border-bottom: 1px solid var(--ba-rule); }}
    .ba-castgrid .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;
        margin-top: .7rem; }}
    .ba-castgrid article {{ display: flex; flex-direction: column; align-items: center; text-align: center; gap: .3rem;
        padding: 1rem .7rem .9rem; border: 1px solid var(--ba-line); border-radius: var(--ba-radius); background: var(--ba-surface);
        box-shadow: var(--ba-glow); transition: transform .2s ease; }}
    .ba-castgrid article:hover {{ }}
    .ba-castgrid article b {{ font-family: {SERIF}; font-weight: 500; font-size: 1.2rem; margin-top: .3rem; }}
    .ba-castgrid .role {{ font: 600 .62rem/1.3 {SANS}; letter-spacing: .12em; text-transform: uppercase;
        color: var(--ba-gold); }}
    .ba-castgrid .look {{ font-size: .82rem; color: var(--ba-ink); }}
    .ba-castgrid .meta {{ font-size: .75rem; color: var(--ba-ink2); }}
    .ba-castgrid small {{ font-size: .7rem; color: var(--ba-muted); font-style: italic; line-height: 1.35; }}
    .ba-castgrid .note {{ font-size: .75rem; color: var(--ba-muted); margin: .6rem 0 0; }}
    [data-testid="stSidebar"] a {{ color: inherit; text-decoration-color: var(--ba-muted); }}

    /* The mascot */
    .ba-brand {{ display: flex; align-items: center; gap: .75rem; margin: .2rem 0 .4rem; }}
    .ba-brand img {{ width: 52px; height: 52px; border-radius: 50%; box-shadow: 0 0 0 2px var(--ba-gold); }}
    .ba-brand b {{ display: block; font-family: {SERIF}; font-size: 1.45rem; line-height: 1.1; color: var(--ba-ink); }}
    .ba-brand span {{ font-size: .78rem; color: var(--ba-muted); }}
    .ba-split {{ display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 2rem; align-items: center; }}
    .ba-mascot {{ margin: 0; text-align: center; }}
    .ba-shape {{ margin-top: 1rem; padding: 1rem 1.1rem; border-radius: var(--ba-radius); border: 1px solid var(--ba-line);
        background: var(--ba-surface); }}
    .ba-shape h3 {{ font-family: {SERIF}; font-size: 1.25rem; line-height: 1.3; color: var(--ba-ink); margin: .4rem 0 .6rem;
        padding: 0; font-weight: 500; }}
    .ba-shape h3 b {{ color: var(--ba-gold); font-weight: 700; }}
    .ba-shape p {{ font-size: .85rem; color: var(--ba-ink2); margin: .3rem 0; line-height: 1.45; }}
    .ba-shape svg {{ display: block; width: 100%; overflow: visible; }}
    .ba-shape svg.big {{ height: 70px; }}
    .ba-shape polyline {{ fill: none; stroke-linejoin: round; stroke-linecap: round; }}
    .ba-shape .book {{ stroke: var(--ba-gold); stroke-width: 3; }}
    .ba-shape .tpl {{ stroke: var(--ba-muted); stroke-width: 2; stroke-dasharray: 5 4; }}
    .ba-shape .key {{ font-size: .75rem; color: var(--ba-muted); }}
    .ba-shape .key span {{ display: inline-block; width: 16px; vertical-align: middle; margin-right: 3px; }}
    .ba-shape .k-book {{ border-top: 3px solid var(--ba-gold); }}
    .ba-shape .k-tpl {{ border-top: 2px dashed var(--ba-muted); }}
    .ba-minis {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem .6rem; margin-top: .7rem; }}
    .ba-minis figure {{ margin: 0; opacity: .55; }}
    .ba-minis figure.on {{ opacity: 1; }}
    .ba-minis svg {{ height: 20px; }}
    .ba-minis polyline {{ stroke: var(--ba-ink2); stroke-width: 1.6; }}
    .ba-minis .on polyline {{ stroke: var(--ba-gold); stroke-width: 2.4; }}
    .ba-minis figcaption {{ font-size: .68rem; color: var(--ba-muted); line-height: 1.25; margin-top: .2rem; }}
    .ba-minis .on figcaption {{ color: var(--ba-ink); font-weight: 600; }}
    .ba-about {{ display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 2rem; align-items: center;
        margin-top: 1.5rem; padding: 1.6rem 1.8rem; border-radius: var(--ba-radius); border: 1px solid var(--ba-line);
        background: var(--ba-surface); box-shadow: var(--ba-glow); }}
    .ba-about figure {{ margin: 0; text-align: center; }}
    .ba-about img {{ width: 100%; aspect-ratio: 1; object-fit: cover; object-position: 60% 30%; border-radius: 50%;
        box-shadow: 0 0 0 3px var(--ba-gold); }}
    .ba-about figcaption {{ font-size: .78rem; color: var(--ba-muted); margin-top: .6rem; font-style: italic; }}
    .ba-about h2 {{ font-family: {SERIF}; font-size: 1.6rem; color: var(--ba-ink); margin: 0 0 .6rem; padding: 0; }}
    .ba-about p {{ color: var(--ba-ink2); line-height: 1.6; max-width: 46rem; margin: 0 0 .7rem; }}
    .ba-about .ba-byline {{ font: italic 400 1rem/1.3 {SERIF}; color: var(--ba-muted); margin: -.2rem 0 1rem; }}
    .ba-about .ba-links a {{ color: var(--ba-ink); font-weight: 600; text-decoration: none;
        border-bottom: 1px solid var(--ba-gold); }}
    .ba-mascot img {{ width: 100%; aspect-ratio: 4 / 5; object-fit: cover; object-position: 60% 30%; border-radius: var(--ba-radius);
        box-shadow: var(--ba-glow); border: 1px solid var(--ba-line); }}
    .ba-mascot figcaption {{ font-size: .8rem; font-style: italic; color: var(--ba-muted); margin-top: .5rem; }}
    .ba-working {{ display: grid; grid-template-columns: 300px minmax(0, 1fr); gap: 1.6rem; align-items: center;
        padding: 1.4rem 1.6rem; border-radius: var(--ba-radius); border: 1px solid var(--ba-line); background: var(--ba-surface);
        box-shadow: var(--ba-glow); margin-bottom: .8rem; }}
    .ba-working img {{ width: 170px; aspect-ratio: 1; object-fit: cover; object-position: 55% 62%; border-radius: var(--ba-radius);
        animation: ba-typing .5s ease-in-out infinite alternate; }}
    .ba-working img.ba-scene {{ width: 300px; aspect-ratio: 32 / 22; border-radius: var(--ba-radius); animation: none;
        object-fit: contain; }}
    .ba-doing {{ font-size: 1.05rem; font-style: italic; color: var(--ba-ink); margin: 0 0 .6rem; }}
    .ba-working h2 {{ font-family: {SERIF}; font-size: 1.9rem; margin: .4rem 0 .6rem; padding: 0; color: var(--ba-ink); }}
    .ba-dots {{ display: inline-flex; gap: 5px; margin-left: .5rem; vertical-align: middle; }}
    .ba-dots i {{ width: 7px; height: 7px; border-radius: 50%; background: var(--ba-gold);
        animation: ba-dot 1.2s ease-in-out infinite; }}
    .ba-dots i:nth-child(2) {{ animation-delay: .2s; }} .ba-dots i:nth-child(3) {{ animation-delay: .4s; }}
    .ba-tips {{ position: relative; min-height: 2.8em; color: var(--ba-ink2); font-size: .95rem; }}
    .ba-tips span {{ position: absolute; inset: 0; opacity: 0; animation: ba-tip 24s infinite; }}
    @keyframes ba-typing {{ from {{ transform: translateY(0) rotate(0deg); }} to {{ transform: translateY(-2px) rotate(.4deg); }} }}
    @keyframes ba-dot {{ 0%, 60%, 100% {{ opacity: .25; transform: translateY(0); }} 30% {{ opacity: 1; transform: translateY(-4px); }} }}
    @keyframes ba-tip {{ 0% {{ opacity: 0; }} 3%, 22% {{ opacity: 1; }} 25%, 100% {{ opacity: 0; }} }}
    @media (prefers-reduced-motion: reduce) {{
        .ba-working img, .ba-dots i {{ animation: none; }}
        .ba-tips span {{ animation: none; }} .ba-tips span:first-child {{ opacity: 1; }} }}

    @media (max-width: 560px) {{
        
        .ba-split, .ba-working, .ba-about {{ grid-template-columns: 1fr; }} .ba-about figure {{ max-width: 180px; margin: 0 auto; }} .ba-castgrid .grid {{ grid-template-columns: repeat(2, 1fr); }} .ba-mascot img {{ max-width: 260px; }}
        .ba-hero {{ padding: 1.4rem 1.1rem 1.1rem; }} }}
    </style>"""


# --- the mascot ------------------------------------------------------------------------------


@cache  # read and encode each picture once per server
def image_uri(name: str) -> str:
    """A picture from app/assets as a data: URI, so it can sit inside st.html."""
    kind = "png" if name.endswith(".png") else "jpeg"
    return f"data:image/{kind};base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


def mascot_line(step: str) -> str:
    return MASCOT_LINES.get(step, "Getting comfortable at the keyboard…")


# The maker, from his LinkedIn profile (edit here: it is shown on the start page and at the bottom)
ABOUT = {
    "name": "Khaldoun Al-Naierat",
    # a short article on why the project exists (impersonal: the owner asked for no personal details)
    "title": "Turning words into data",
    "paragraphs": [
        "Data is one of the best ways we have to represent reality. A single number says very little, but "
        "thousands of them, put in order, reveal patterns that no one could see by looking at things one at a "
        "time: how a city moves, how an idea spreads, how a season changes. Structured data lets us step back "
        "and understand a much larger picture of the world.",
        "Yet much of what people know and feel is not stored in tables. It lives in written words: novels, "
        "letters, histories and stories. Words are rich, but they are unstructured. You cannot sort, count or "
        "chart a paragraph the way you can a column of numbers.",
        "This project was created to close that gap. It takes a book and turns its words into understandable, "
        "structured data. Every sentence becomes a record with its tone and its emotions; every character "
        "becomes a set of appearances, relationships and lines of dialogue; every chapter becomes a point on "
        "a curve. Once a story is data, it can be measured, compared and drawn.",
        "None of this replaces reading. A chart cannot feel what a reader feels. But it can show the shape of a "
        "story at a glance: where it darkens, who stands at its centre, how two people drift together or "
        "apart. And it can set one book beside many others, something no single reading can do.",
        "It is built with small, specialised machine-learning models that run on an ordinary computer, so a "
        "book never leaves it. It is a passion project and still growing, so expect the odd mistake: the "
        "raccoon is still learning too.",
    ],
    "links": [("LinkedIn", "https://www.linkedin.com/in/khaldoun-al-naierat"),
              ("GitHub", "https://github.com/KhaldounN")],
}


# The workflow: (what happens, the tool that does it, what kind of tool it is, what comes out)
WORKFLOW = [
    ("Read the book", "Python + spaCy", "rules",
     "The Project Gutenberg header and licence are removed, the text is cut into chapters, then into sentences.",
     "chapters and sentences"),
    ("Find the names", "spaCy en_core_web_lg", "statistical model",
     "A named-entity recognizer marks people, places and organizations. Forms of one full name "
     "(Elizabeth Bennet, Elizabeth) are grouped; nicknames can be merged by hand in the sidebar.", "characters, places"),
    ("Link the pronouns", "fastcoref", "coreference model",
     "Works out who “she”, “his” and “the young lady” refer to, so a character is counted even when "
     "they are not named. Right about 3 times in 4.", "every mention of every character"),
    ("Score the tone", "RoBERTa sentiment classifier", "classifier",
     "Gives every sentence a score from −1 (negative) to +1 (positive).", "the mood of each sentence"),
    ("Tag the emotions", "EmoLit RoBERTa classifier", "classifier",
     "Trained on sentences from classic literature: rates 38 fine emotions (grief, guilt, gratitude, "
     "curiosity…) in every sentence, grouped into 8 families.", "the emotions of each sentence"),
    ("Name the chapters", "MiniLM sentence embeddings", "similarity model",
     "Turns each chapter's sentences into numbers and finds the closest of a list of themes "
     "(ball, proposal, scandal, journey…).", "a theme for each chapter"),
    ("Count and compare", "plain statistics", "no model",
     "Averages, counts and correlations: who appears near whom, who speaks, how fast the book reads, "
     "and which of six classic story shapes its mood follows.", "every chart on this page"),
]


# --- the emblem: the raccoon as a publisher's mark ----------------------------------------------


def _emblem_svg(size: int, ink: str = "", paper: str = "", accent: str = "") -> str:
    """The mascot, drawn after the owner's raccoon photo (app/assets/raccoon.jpg): fluffy grey-brown fur,
    rounded ears with cream insides, white brows over a dark mask, big glossy eyes, a white muzzle and
    whiskers, a gentle smile, and black gaming headphones with orange rims. Fixed colours, with a cream
    "sticker" border so it stands out on light and dark pages alike.
    (The ink/paper/accent arguments are kept for the callers; unused.)"""
    line = "#2a211c"
    head = ("M32 13 C44 13 52 19 54 28 L59 32 L54.5 34.5 L58 39 L52.5 40 C49 49 41.5 54.5 32 54.5 "
            "C22.5 54.5 15 49 11.5 40 L6 39 L9.5 34.5 L5 32 L10 28 C12 19 20 13 32 13 Z")
    band = "M8.6 37 C7 17 18 7 32 7 C46 7 57 17 55.4 37"
    cups = ('<rect x="3" y="29.5" width="9.5" height="15" rx="4.2"/>'
            '<rect x="51.5" y="29.5" width="9.5" height="15" rx="4.2"/>')
    ear = lambda x, turn: (  # noqa: E731
        f'<g transform="rotate({turn} {x} 15)"><ellipse cx="{x}" cy="15" rx="7.6" ry="8.2" fill="#7c6d60" '
        f'stroke="{line}" stroke-width="1.4"/><ellipse cx="{x}" cy="15.8" rx="5" ry="5.6" fill="#efe4d4"/>'
        f'<ellipse cx="{x}" cy="16.6" rx="2.8" ry="3.4" fill="#8a6e60"/></g>')
    eye = lambda x: (  # noqa: E731
        f'<circle cx="{x}" cy="31.6" r="5" fill="#120c0a"/><circle cx="{x}" cy="31.6" r="4.2" fill="#2e1d15"/>'
        f'<circle cx="{x}" cy="31.8" r="2.6" fill="#0b0706"/>'
        f'<circle cx="{x + 1.6}" cy="29.9" r="1.7" fill="#fff"/><circle cx="{x - 1.4}" cy="33.4" r=".7" fill="#fff" opacity=".8"/>')
    whiskers = "".join(f'<path d="M{a} {b} L{c} {d}" stroke="#f6f1ea" stroke-width=".55" stroke-linecap="round" opacity=".85"/>'
                       for a, b, c, d in ((24, 44, 13, 42.5), (24, 45.6, 13.5, 46.5), (40, 44, 51, 42.5), (40, 45.6, 50.5, 46.5)))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 64 64">
      <defs>
        <radialGradient id="fur" cx="50%" cy="40%" r="62%"><stop offset="0" stop-color="#b9ab9c"/>
          <stop offset=".6" stop-color="#9a8b7d"/><stop offset="1" stop-color="#6e6055"/></radialGradient>
        <radialGradient id="mask" cx="50%" cy="45%" r="60%"><stop offset="0" stop-color="#241a15"/>
          <stop offset="1" stop-color="#3e312a"/></radialGradient>
        <linearGradient id="cup" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3a3a40"/>
          <stop offset="1" stop-color="#141417"/></linearGradient>
      </defs>
      <g stroke="#fbf6ec" stroke-width="5" stroke-linejoin="round" fill="#fbf6ec">
        <ellipse cx="16" cy="15" rx="7.6" ry="8.2"/><ellipse cx="48" cy="15" rx="7.6" ry="8.2"/><path d="{head}"/>{cups}</g>
      <path d="{band}" fill="none" stroke="#fbf6ec" stroke-width="8.5" stroke-linecap="round"/>
      {ear(16, -18)}{ear(48, 18)}
      <path d="{head}" fill="url(#fur)" stroke="{line}" stroke-width="1.4" stroke-linejoin="round"/>
      <path d="M32 13.5 Q29.6 20 30 27.5 L34 27.5 Q34.4 20 32 13.5 Z" fill="#4f433b" opacity=".8"/>
      <ellipse cx="21.5" cy="24.6" rx="7" ry="3" fill="#f4eee6" transform="rotate(-10 21.5 24.6)"/>
      <ellipse cx="42.5" cy="24.6" rx="7" ry="3" fill="#f4eee6" transform="rotate(10 42.5 24.6)"/>
      <path d="M8 32 C11 25.5 22 24.6 29 30 L32 32.4 L35 30 C42 24.6 53 25.5 56 32 C53 38.6 44.6 40.6 38.6 37.6
               L32 36.2 L25.4 37.6 C19.4 40.6 11 38.6 8 32 Z" fill="url(#mask)"/>
      {eye(22.5)}{eye(41.5)}
      <path d="M16.5 41 C18.5 37.6 24 37.2 27 39 C29 37 35 37 37 39 C40 37.2 45.5 37.6 47.5 41 C46.5 48.8 40 53.2 32 53.2
               C24 53.2 17.5 48.8 16.5 41 Z" fill="#f6f1ea"/>
      {whiskers}
      <path d="M28.4 39.2 Q32 37.5 35.6 39.2 Q35.2 42.4 32 43.4 Q28.8 42.4 28.4 39.2 Z" fill="{line}"/>
      <ellipse cx="30.8" cy="39.5" rx="1.4" ry=".65" fill="#fff" opacity=".65"/>
      <path d="M32 43.4 L32 44.9 M28.4 44.6 Q30.2 47 32 44.9 Q33.8 47 35.6 44.6" fill="none" stroke="{line}"
            stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="{band}" fill="none" stroke="#18181b" stroke-width="3.6" stroke-linecap="round"/>
      <path d="M11 26 C13 15 21 9.3 32 9.3 C43 9.3 51 15 53 26" fill="none" stroke="#5a5a62" stroke-width=".9" opacity=".7"/>
      <g fill="url(#cup)" stroke="#ff8a2a" stroke-width="1.5">{cups}</g>
      <path d="M5.2 33 L5.2 41 M58.8 33 L58.8 41" stroke="#ffb066" stroke-width=".9" stroke-linecap="round" opacity=".8"/>
    </svg>"""


# the emblem's colours in each look: ink, paper (the page), the accent inside the ears
EMBLEM_COLOURS = {"light": ("#1b1a17", "#fbfaf6", "#8a2b1f"), "dark": ("#ece8df", "#121110", "#e0957a")}


@cache
def _emblem_uri(mode: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(_emblem_svg(64, *EMBLEM_COLOURS[mode]).encode()).decode()


def emblem(size: int = 44) -> str:
    """The mascot's emblem as pictures, one per look; page_css shows the one that matches.
    (A picture, because st.html removes inline SVG drawings.)"""
    return "".join(f'<img class="ba-emblem em-{mode}" src="{_emblem_uri(mode)}" width="{size}" height="{size}" '
                   f'alt="{"The Book Visualizer raccoon" if mode == "light" else ""}">' for mode in EMBLEM_COLOURS)


def favicon_svg() -> str:
    """The emblem for the browser tab (app/assets/raccoon-emblem.png was made from it)."""
    return _emblem_svg(64, *EMBLEM_COLOURS["light"])


def raccoon_note(text: str) -> str:
    """A short aside from the mascot, set in the margin style of a printed edition."""
    return (f'<aside class="ba-rnote">{emblem(34)}<p><b>The raccoon’s note.</b> {escape(text)}</p></aside>')


# --- How it works, animated --------------------------------------------------------------------------
# An SVG with CSS animations, shown as a picture (like a GIF, but sharp at any size and a few KB):
# the raccoon pushes a page cart from the book, past the seven stations, to a growing dashboard.

ANIM_COLOURS = {  # ink, muted text, station fill, page, accent
    "light": ("#1b1a17", "#6f6a60", "#ffffff", "#fbfaf6", "#8a2b1f"),
    "dark": ("#ece8df", "#a39e93", "#1c1b19", "#121110", "#e0957a"),
}
STATION_ICONS = [  # one simple line drawing per workflow step, in a 32 x 32 box centred on 0,0
    # read: an open book
    '<path d="M-13 -9 Q-6 -12 0 -8 Q6 -12 13 -9 L13 10 Q6 7 0 11 Q-6 7 -13 10 Z M0 -8 L0 11"/>',
    # names: a magnifying glass over "Aa"
    '<circle cx="-3" cy="-3" r="8"/><path d="M3 3 L11 11"/><text x="-3" y="0" font-size="8" text-anchor="middle" '
    'stroke="none" fill="currentColor" font-family="Georgia, serif">Aa</text>',
    # pronouns: two chain links
    '<rect x="-14" y="-5" width="15" height="10" rx="5"/><rect x="-1" y="-5" width="15" height="10" rx="5"/>',
    # tone: a gauge from minus to plus
    '<path d="M-13 6 A13 13 0 0 1 13 6"/><path d="M0 6 L7 -5"/><text x="-14" y="13" font-size="7" stroke="none" '
    'fill="currentColor">−</text><text x="10" y="13" font-size="7" stroke="none" fill="currentColor">+</text>',
    # emotions: a heart
    '<path d="M0 11 C-14 1 -13 -11 -5 -10 C-2 -10 0 -7 0 -5 C0 -7 2 -10 5 -10 C13 -11 14 1 0 11 Z"/>',
    # chapters: a tag
    '<path d="M-12 -9 L3 -9 L13 0 L3 9 L-12 9 Z"/><circle cx="-6" cy="0" r="2"/>',
    # statistics: a sigma
    '<text x="0" y="8" font-size="22" text-anchor="middle" stroke="none" fill="currentColor" '
    'font-family="Georgia, serif">Σ</text>',
]
STATION_NAMES = [("Read", "spaCy"), ("Names", "spaCy NER"), ("Pronouns", "fastcoref"), ("Tone", "RoBERTa"),
                 ("Emotions", "EmoLit"), ("Chapters", "MiniLM"), ("Count", "statistics")]
ANIM_SECONDS = 14


def _workflow_svg(mode: str) -> str:
    ink, muted, fill, page, accent = ANIM_COLOURS[mode]
    xs = [190 + i * 112 for i in range(len(STATION_ICONS))]
    travel = ANIM_SECONDS * 0.8  # the cart rides for 80% of the loop, then the dashboard holds
    stations = []
    for i, (x, icon, (name, tool)) in enumerate(zip(xs, STATION_ICONS, STATION_NAMES)):
        arrive = (x - 70) / (1040 - 70) * travel  # when the cart passes this station
        stations.append(
            f'<g transform="translate({x} 150)">'
            f'<circle r="34" fill="{fill}" stroke="{muted}" stroke-width="1.5"/>'
            f'<circle r="34" fill="none" stroke="{accent}" stroke-width="3" class="lit" '
            f'style="animation-delay:{arrive:.2f}s"/>'
            f'<g fill="none" stroke="{ink}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'color="{ink}" class="icon" style="animation-delay:{arrive:.2f}s">{icon}</g>'
            f'<circle cx="24" cy="-24" r="10" fill="{accent}"/>'
            f'<text x="24" y="-20.5" font-size="11" text-anchor="middle" fill="{page}" font-weight="700">{i + 1}</text>'
            f'<text y="58" font-size="15" text-anchor="middle" fill="{ink}" font-family="Georgia, serif">{name}</text>'
            f'<text y="76" font-size="11" text-anchor="middle" fill="{muted}">{tool}</text></g>')
    raccoon = re.sub(r"^<svg[^>]*>|</svg>$", "", _emblem_svg(64).strip())
    bars = "".join(f'<rect x="{1072 + k * 14}" y="{170 - h}" width="10" height="{h}" rx="2" fill="{c}" class="bar" '
                   f'style="animation-delay:{travel:.2f}s"/>'
                   for k, (h, c) in enumerate(((22, "#2a78d6"), (38, "#e87ba4"), (30, "#eda100"), (46, "#1baf7a"))))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1160 250" font-family="Inter, Arial, sans-serif">
  <style>
    .belt {{ stroke-dasharray: 10 8; animation: belt 1s linear infinite; }}
    @keyframes belt {{ to {{ stroke-dashoffset: -18; }} }}
    .cart {{ animation: ride {ANIM_SECONDS}s linear infinite; }}
    @keyframes ride {{ 0% {{ transform: translate(70px, 0); }} 80% {{ transform: translate(1040px, 0); }}
                       80.01%, 100% {{ transform: translate(1040px, 0); opacity: 0; }} }}
    .lit {{ opacity: 0; animation: lit {ANIM_SECONDS}s ease-out infinite; }}
    @keyframes lit {{ 0% {{ opacity: 1; }} 12% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
    .icon {{ animation: pop {ANIM_SECONDS}s ease-out infinite; transform-box: fill-box; transform-origin: center; }}
    @keyframes pop {{ 0% {{ transform: scale(1.35); }} 6% {{ transform: scale(1); }} 100% {{ transform: scale(1); }} }}
    .bar {{ transform-box: fill-box; transform-origin: bottom; transform: scaleY(.15);
            animation: grow {ANIM_SECONDS}s ease-out infinite; }}
    @keyframes grow {{ 0% {{ transform: scaleY(.15); }} 8% {{ transform: scaleY(1); }} 18%, 100% {{ transform: scaleY(1); }} }}
    .bob {{ animation: bob .5s ease-in-out infinite alternate; }}
    @keyframes bob {{ to {{ transform: translateY(-3px); }} }}
    @media (prefers-reduced-motion: reduce) {{ .belt, .cart, .lit, .icon, .bar, .bob {{ animation: none; }}
      .cart {{ transform: translate(70px, 0); }} .bar {{ transform: none; }} }}
  </style>
  <path d="M40 72 L1120 72" stroke="{muted}" stroke-width="3" class="belt"/>
  <g transform="translate(70 150)"><path d="M-30 -26 Q-14 -34 0 -24 Q14 -34 30 -26 L30 26 Q14 18 0 28 Q-14 18 -30 26 Z"
     fill="{fill}" stroke="{ink}" stroke-width="2"/><path d="M0 -24 L0 28" stroke="{ink}" stroke-width="2"/>
    <path d="M-24 -14 L-6 -14 M-24 -6 L-6 -6 M-24 2 L-6 2 M6 -14 L24 -14 M6 -6 L24 -6 M6 2 L24 2" stroke="{muted}"/>
    <text y="58" font-size="15" text-anchor="middle" fill="{ink}" font-family="Georgia, serif">Your book</text></g>
  {"".join(stations)}
  <g><rect x="1062" y="118" width="72" height="62" rx="6" fill="{fill}" stroke="{ink}" stroke-width="2"/>{bars}
    <text x="1098" y="208" font-size="15" text-anchor="middle" fill="{ink}" font-family="Georgia, serif">Charts</text></g>
  <g class="cart"><g class="bob">
    <rect x="-22" y="38" width="30" height="22" rx="3" fill="{page}" stroke="{ink}" stroke-width="2"/>
    <path d="M-17 45 L3 45 M-17 51 L3 51" stroke="{muted}" stroke-width="1.5"/>
    <circle cx="-14" cy="66" r="5" fill="{ink}"/><circle cx="2" cy="66" r="5" fill="{ink}"/>
    <svg x="4" y="14" width="42" height="42" viewBox="0 0 64 64">{raccoon}</svg></g></g>
</svg>"""


@cache
def _workflow_uri(mode: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(_workflow_svg(mode).encode()).decode()



# --- How it works as a pipeline run, like an orchestration tool (Airflow, Prefect, Dagster) ---------
# Library logos: Simple Icons (CC0, app/assets/logos/, downloaded once), each in its brand colour on a
# white chip so it reads in both looks. A library without a logo there is shown by name.
LOGO_COLOURS = {"python": "#3776AB", "spacy": "#09A3D5", "pytorch": "#EE4C2C", "huggingface": "#FF9D00",
                "pandas": "#150458", "numpy": "#013243", "scikitlearn": "#F7931E", "plotly": "#3F4F75",
                "threedotjs": "#000000", "streamlit": "#FF4B4B"}
LOGO_NAMES = {"python": "Python", "spacy": "spaCy", "pytorch": "PyTorch", "huggingface": "Hugging Face",
              "pandas": "pandas", "numpy": "NumPy", "scikitlearn": "scikit-learn", "plotly": "Plotly",
              "threedotjs": "Three.js", "streamlit": "Streamlit", "networkx": "NetworkX"}


@cache
def logo(name: str) -> str:
    """A library's logo as a small chip (or its name, when there is no logo file)."""
    path = ASSETS / "logos" / f"{name}.svg"
    label = LOGO_NAMES.get(name, name)
    if not path.exists():
        return f'<span class="ba-logo text" title="{escape(label)}">{escape(label)}</span>'
    svg = path.read_text(encoding="utf-8").replace("<svg ", f'<svg fill="{LOGO_COLOURS.get(name, "#333")}" ', 1)
    uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return f'<span class="ba-logo" title="{escape(label)}"><img src="{uri}" alt="{escape(label)}"></span>'


# (task id, what it does, the model it runs, its libraries, typical time on a novel)
DAG_START = [
    ("load_text", "Clean the Gutenberg file, find the chapters", "rules, no model", ["python"], "1 s"),
    ("parse_sentences", "Split into sentences, tag every word", "spaCy en_core_web_lg", ["spacy"], "1 min"),
]
DAG_PARALLEL = [
    ("find_characters", "Names of people and places", "spaCy named-entity recognizer", ["spacy"], "5 s"),
    ("link_pronouns", "Who “she” and “his” refer to", "fastcoref (coreference)", ["pytorch", "huggingface"], "2 min"),
    ("score_sentiment", "Tone of every sentence, −1 to +1", "RoBERTa sentiment classifier", ["pytorch", "huggingface"], "3 min"),
    ("tag_emotions", "38 fine emotions per sentence", "EmoLit RoBERTa classifier", ["pytorch", "huggingface"], "2–3 min"),
    ("name_chapters", "A theme and key sentence per chapter", "MiniLM sentence embeddings", ["pytorch", "huggingface", "numpy"], "30 s"),
]
DAG_END = [
    ("aggregate", "Relationships, dialogue, pace, story shape", "statistics, no model", ["pandas", "numpy", "networkx"], "2 s"),
    ("visualize", "Charts, 3D scenes and this page", "no model", ["plotly", "threedotjs", "streamlit"], "live"),
]


def _dag_node(task: tuple, extra: str = "") -> str:
    tid, what, model, libraries, took = task
    return (f'<div class="ba-node{extra}"><div class="top"><i class="ok" title="success"></i><code>{escape(tid)}</code>'
            f'</div><p>{escape(what)}</p><div class="model">{escape(model)} <span class="took">· {escape(took)}</span></div>'
            f'<div class="libs">{"".join(logo(n) for n in libraries)}</div></div>')


def pipeline_dag() -> str:
    """The analysis as a pipeline run: each task with its status, model, libraries and typical time;
    the five detections fan out from the sentences and join again before the charts."""
    start = '<div class="arrow"></div>'.join(_dag_node(t) for t in DAG_START)
    parallel = "".join(_dag_node(t, " par") for t in DAG_PARALLEL)
    end = '<div class="arrow"></div>'.join(_dag_node(t) for t in DAG_END)
    return f"""<figure class="ba-dag">
      <div class="ba-dag-bar"><span class="name">DAG <code>book_analysis</code></span>
        <span class="state"><i class="ok"></i>success</span><span>9 tasks</span><span>~8 min on a novel</span>
        <span class="local">every model runs on this computer</span></div>
      <div class="ba-dag-flow">
        <div class="stage">{start}</div><div class="arrow"></div>
        <div class="stage fan"><div class="fan-label">independent · one model at a time</div>{parallel}</div>
        <div class="arrow"></div><div class="stage">{end}</div>
      </div>
      <figcaption>Each box is one task. The five in the middle only need the sentences, so they don't depend
      on each other: an orchestration tool would run them in parallel; here they run one after another so
      that only one AI model is in memory at a time.</figcaption>
    </figure>"""


def workflow_animation() -> str:
    """The animated workflow, one picture per look (page_css shows the one that matches)."""
    return "".join(f'<img class="ba-anim em-{mode}" src="{_workflow_uri(mode)}" alt="'
                   f'{"An animation of the workflow: the raccoon carries a page of the book past seven stations, "
                      "read, names, pronouns, tone, emotions, chapters and count, and a chart grows at the end" if mode == "light" else ""}">'
                   for mode in ANIM_COLOURS)


# The table of contents: (label, the anchor that streamlit_app.section() gives each part's heading)
CONTENTS = [("Overview", "overview"), ("3D", "explore-in-3d"), ("Story", "the-story"), ("Pace", "pace"),
            ("Mood", "mood"), ("Emotions", "emotions"), ("Characters", "characters"),
            ("Relationships", "relationships"), ("Dialogue", "dialogue"), ("Places", "places"),
            ("How it works", "how-it-works"), ("About", "about")]


def contents() -> str:
    """The sticky bar of links to every part of the page."""
    links = "".join(f'<a href="#{anchor}">{escape(label)}</a>' for label, anchor in CONTENTS)
    return f'<nav class="ba-toc" aria-label="Contents">{links}</nav>'


def how_it_works() -> str:
    """What kind of AI this is (and isn't), and the workflow from the book to the charts."""
    steps = "".join(
        f'<li><span class="n">{i}</span><div><b>{escape(what)}</b><p>{escape(text)}</p></div>'
        f'<div class="tool"><code>{escape(tool)}</code><span>{escape(kind)}</span></div>'
        f'<div class="out">→ {escape(out)}</div></li>'
        for i, (what, tool, kind, text, out) in enumerate(WORKFLOW, 1))
    return f"""<section class="ba-how">
      <div class="ba-note">
        <div class="ba-kicker">Not a chatbot</div>
        <h3>Good old machine learning, not a large language model</h3>
        <p>Nothing here writes text or “understands” the book the way ChatGPT or Claude do, and nothing is sent
        to an online AI service. Book Visualizer uses small, specialised machine-learning models, each trained for one
        narrow job: spotting names, linking pronouns, scoring a sentence's tone, tagging its emotions. Their
        answers are then counted and compared with plain statistics. Every model runs on this computer.</p>
        <p class="fine">To be exact: the tone and emotion models are built on RoBERTa, a small (125-million-parameter)
        neural network pre-trained on English text and then trained to classify. Unlike a chatbot it can only pick
        labels from a fixed list; it cannot write, answer questions or invent anything.</p>
      </div>
      {raccoon_note("I do not read the way you do. I count, compare and score, sentence by sentence, "
                    "and I never make anything up: every chart can be traced back to sentences in the book.")}
      <div class="ba-kicker">The workflow</div>
      <h3>From a text file to a picture of the novel, in seven steps</h3>
      {pipeline_dag()}
      <ol class="ba-flow">{steps}</ol>
      <p class="ba-flow-note">A whole novel takes about ten minutes on an ordinary laptop. The results are saved, so a
      book is only read once. All the numbers are estimates: they show trends, not exact counts.</p>
    </section>"""


def about() -> str:
    """Who made the site: a short, friendly card with the raccoon."""
    text = "".join(f"<p>{escape(p)}</p>" for p in ABOUT["paragraphs"])
    links = " · ".join(f'<a href="{url}" target="_blank" rel="noopener">{escape(label)} ↗</a>'
                       for label, url in ABOUT["links"])
    return f"""<section class="ba-about">
      <figure><img src="{image_uri("raccoon.jpg")}" alt="The Book Visualizer raccoon in headphones at a keyboard">
      <figcaption>The raccoon, head of reading</figcaption></figure>
      <div><div class="ba-kicker">About · a passion project</div>
      <h2>{escape(ABOUT["title"])}</h2><p class="ba-byline">By {escape(ABOUT["name"])}</p>{text}
      <p class="ba-links">{links}</p></div>
    </section>"""


def top_bar(title: str | None = None) -> str:
    """The masthead above the tabs on every page: the site's name and motto, then the open book."""
    book = (f'<span class="book" title="{escape(title)}">{escape(title)}</span>') if title else ""
    return f"""<header class="ba-top">
      <a class="ba-mark" href="?home=1" target="_self" title="The start page: all the books">{emblem(58)}<div><b>Book Visualizer</b><span>A computational reading of the novel</span></div></a>
      <div class="ba-meta">{book}<span class="ba-sc">Local models · Your book stays on this computer</span></div>
    </header>"""


def footer() -> str:
    """The colophon at the bottom of every page."""
    links = " · ".join(f'<a href="{url}" target="_blank" rel="noopener">{escape(label)}</a>'
                       for label, url in ABOUT["links"])
    return (f'<footer class="ba-foot"><span>{emblem(22)}<b>Book Visualizer</b>A passion project by {escape(ABOUT["name"])}. '
            f'Every model runs locally; results are estimates.</span><span>{links}</span></footer>')


def sidebar_title() -> str:
    return (f'<div class="ba-brand"><img src="{image_uri("raccoon-face.png")}" alt="">'
            f'<div><b>Book Visualizer</b><span>with a raccoon at the keyboard</span></div></div>')


def working_card(step: str = "") -> str:
    """Shown while a book is analyzed: an animated cartoon raccoon doing this step's job
    (app/raccoon.py), what it's up to, typing dots, and tips that take turns."""
    from raccoon import scene_uri
    tips = "".join(f'<span style="animation-delay:{i * 6}s">{escape(t)}</span>' for i, t in enumerate(MASCOT_TIPS))
    doing = f'<p class="ba-doing">🦝 {escape(mascot_line(step))}</p>'
    return f"""<section class="ba-working">
      <img class="ba-scene" src="{scene_uri(step)}" alt="A cartoon raccoon at work: {escape(step or 'getting started')}">
      <div>
        <div class="ba-kicker">Analyzing your book{" · " + escape(step) if step else ""}</div>
        <h2>The raccoon is on it<span class="ba-dots"><i></i><i></i><i></i></span></h2>
        {doing}
        <div class="ba-tips">{tips}</div>
      </div>
    </section>"""


# --- small pictures inside the cards ------------------------------------------------------


def _sparkline(values: list[float], color: str, theme: dict, zero: bool = False) -> str:
    """A tiny line chart as SVG (no axes): the shape of a series at a glance."""
    if len(values) < 2:
        return ""
    low, high = min(values + ([0.0] if zero else [])), max(values + ([0.0] if zero else []))
    span = (high - low) or 1
    x = lambda i: i / (len(values) - 1) * 100  # noqa: E731
    y = lambda v: 36 - (v - low) / span * 34  # noqa: E731
    points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    base = f'<line x1="0" x2="100" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{theme["axis"]}" stroke-dasharray="2 2" ' \
           f'vector-effect="non-scaling-stroke"/>' if zero else ""
    return (f'<svg viewBox="0 0 100 38" preserveAspectRatio="none">{base}'
            f'<polyline points="0,38 {points} 100,38" fill="{color}" fill-opacity=".14" stroke="none"/>'
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" '
            f'vector-effect="non-scaling-stroke"/></svg>')


def _shape_path(values: list[float], width: float, height: float, pad: float = 3) -> str:
    """SVG points for a curve, stretched to fill the box (only its shape matters)."""
    low, high = min(values), max(values)
    span = (high - low) or 1
    return " ".join(f"{i / (len(values) - 1) * width:.1f},{pad + (high - v) / span * (height - 2 * pad):.1f}"
                    for i, v in enumerate(values))


def story_shape_card(title: str, curve: list[float], fits: list[tuple[str, float]]) -> str:
    """'<Book> is a Cinderella story': the book's mood curve over the best-fitting of the six
    classic story shapes, and a row of all six with how well each one fits."""
    from analyzer.progression import STORY_SHAPES, WEAK_FIT, shape_curve
    if not fits:
        return ""
    best, fit = fits[0]
    how = "clearly" if fit >= 0.6 else "mostly" if fit >= 0.35 else "loosely"
    runner = f" Next closest: <b>{escape(fits[1][0])}</b> ({max(fits[1][1], 0):.0%})." if fit < 0.6 else ""
    article = "an" if best[0] in "AEIOU" else "a"
    heading = (f"<i>{escape(title)}</i> is {how} {article} <b>{escape(best)}</b> story" if fit >= WEAK_FIT else
               f"<i>{escape(title)}</i> follows its own path")
    if fit < WEAK_FIT:  # no shape really fits: say so, and show the closest one only as a hint
        runner = f" None of the six classic shapes fits well; the closest is <b>{escape(best)}</b>."
    minis = "".join(
        f'<figure class="{"on" if name == best else ""}"><svg viewBox="0 0 40 20" preserveAspectRatio="none">'
        f'<polyline points="{_shape_path(shape_curve(name, 20), 40, 20)}" vector-effect="non-scaling-stroke"/></svg>'
        f'<figcaption>{escape(name)}<br>{max(f, 0):.0%}</figcaption></figure>'
        for name, f in sorted(fits, key=lambda f: list(STORY_SHAPES).index(f[0])))
    return f"""<div class="ba-shape">
      <div class="ba-kicker">The shape of the story</div>
      <h3>{heading}</h3>
      <svg class="big" viewBox="0 0 200 60" preserveAspectRatio="none" role="img"
           aria-label="The book's mood curve next to the {escape(best)} shape">
        <polyline class="tpl" points="{_shape_path(shape_curve(best), 200, 60)}" vector-effect="non-scaling-stroke"/>
        <polyline class="book" points="{_shape_path(curve, 200, 60)}" vector-effect="non-scaling-stroke"/></svg>
      <p class="key"><span class="k-book"></span> this book's mood &nbsp; <span class="k-tpl"></span> {escape(best)}</p>
      <p>{escape(STORY_SHAPES[best][1]) + " " if fit >= WEAK_FIT else ""}The curves match {max(fit, 0):.0%}.{runner}</p>
      <div class="ba-minis">{minis}</div>
    </div>"""


def _mini_bars(values: list[int], color: str) -> str:
    top = max(values) or 1
    width = 100 / len(values)
    bars = "".join(f'<rect x="{i * width:.2f}" y="{38 - v / top * 36:.1f}" width="{max(width - 0.4, 0.2):.2f}" '
                   f'height="{v / top * 36:.1f}" rx=".3" fill="{color}"/>' for i, v in enumerate(values))
    return f'<svg viewBox="0 0 100 38" preserveAspectRatio="none">{bars}</svg>'


def _stack(parts: list[tuple[float, str, str]]) -> str:
    """A thin bar split into coloured parts: (share, colour, hover text)."""
    return '<div class="ba-bar">' + "".join(
        f'<i style="flex:{share:.4f};background:{color}" title="{escape(tip)}"></i>' for share, color, tip in parts if share
    ) + "</div>"


def _emotion_legend(theme: dict, shares: dict[str, float]) -> str:
    return '<div class="ba-legend">' + "".join(
        f'<span><i style="background:{theme["emotions"][e]}"></i>{charts.EMOTION_LABELS[e].split(" (")[0]} '
        f'{shares[e]:.0%}</span>' for e in charts.EMOTION_ORDER if shares.get(e)
    ) + "</div>"


def _initials(name: str) -> str:
    words = [w for w in name.replace(".", " ").split() if w[0].isupper() and w not in {"Mr", "Mrs", "Miss", "Dr", "Sir", "Lady", "Lord"}]
    return "".join(w[0] for w in words[-2:]) or name[:2]


def face(avatars: dict | None, character, size: int, color: str = "") -> str:
    """A character's avatar as an <img>, or (without one) a dot in their colour."""
    if avatars and character.id in avatars:
        return (f'<img class="ba-avatar" src="{avatars[character.id]}" alt="" title="{escape(character.name)}" '
                f'style="width:{size}px;height:{size}px">')
    return f'<i class="ba-dot" style="background:{color};width:{size // 2}px;height:{size // 2}px"></i>'


def _faces(characters: list, colors: dict, avatars: dict | None = None) -> str:
    """The characters' avatars side by side (round initials in their colour if there is no avatar)."""
    return '<div class="ba-faces">' + "".join(
        face(avatars, c, 38) if avatars and c.id in avatars else
        f'<span style="background:{colors[c.id]}" title="{escape(c.name)}">{escape(_initials(c.name))}</span>'
        for c in characters) + "</div>"


def cast_legend(analysis: BookAnalysis, theme: dict, avatars: dict | None = None) -> str:
    """The colour (and avatar) of each main character, used in every chart on the page."""
    colors = charts.character_colors(analysis, theme)
    rows = "".join(f'<li>{face(avatars, c, 28, colors[c.id])}{escape(c.name)}</li>'
                   for c in charts.top_characters(analysis, len(theme["series"])))
    return f'<ul class="ba-cast">{rows}<li><i style="background:{theme["muted"]}"></i>everyone else</li></ul>'


# --- hero banner ---------------------------------------------------------------------------


def in_brief(analysis: BookAnalysis, events: list) -> list[str]:
    """The book in a few plain sentences, written from the analysis by templates (no language model):
    who it follows and its shape, its darkest and brightest chapters, the closest pair and how they
    change, who talks most, and the leading emotion. Each sentence is skipped when the numbers are unclear."""
    from analyzer.progression import STORY_SHAPES, WEAK_FIT, story_shape
    out = []
    ranked = charts.top_characters(analysis, len(analysis.characters))
    if not ranked or not analysis.chapters:
        return out
    main = ranked[0]
    from analyzer.narration import narrator
    lines = find_lines(analysis.sentences, analysis.mentions)
    teller = narrator(analysis, lines)
    if teller is not None:  # a first-person book: its narrator, not the most named character, is who it follows
        main = analysis.characters[teller]
        first = (f"It is told in the first person, mostly by <b>{escape(main.name)}</b>, "
                 f"over {len(analysis.chapters)} chapters")
    else:
        first = f"It follows <b>{escape(main.name)}</b> through {len(analysis.chapters)} chapters"
    _, fits = story_shape(analysis.sentences)
    if fits and fits[0][1] >= WEAK_FIT:
        shape = fits[0][0]
        article = "an" if shape[0].lower() in "aeiou" else "a"
        first += (f", and its mood traces {article} <b>{escape(shape)}</b> story: "
                  f"{escape(STORY_SHAPES[shape][1][:1].lower() + STORY_SHAPES[shape][1][1:])}")
    out.append(first + ("" if first.endswith(".") else "."))

    mood = analysis.chapter_sentiment
    if len(mood) >= 3:
        dark, bright = min(range(len(mood)), key=mood.__getitem__), max(range(len(mood)), key=mood.__getitem__)
        def what(i):  # "Chapter 23 (theme: revelation)"
            theme = events[i].theme.lower() if i < len(events) and events[i].theme else ""
            return f"{escape(analysis.chapters[i].title.split(':')[0])}" + (f" (theme: {escape(theme)})" if theme else "")
        out.append(f"The darkest moment comes in {what(dark)}; the brightest in {what(bright)}.")

    pairs = [r for r in analysis.relationships if main.id in (r.source, r.target)]
    if pairs:
        pair = max(pairs, key=lambda r: r.count)
        other = analysis.characters[pair.target if pair.source == main.id else pair.source]
        sentence = f"{escape(main.name)} shares the most moments with <b>{escape(other.name)}</b> ({pair.count})"
        tones = [t for t in pair.chapter_sentiment if t is not None]
        third = max(1, len(tones) // 3)
        if len(tones) >= 6:
            start, end = sum(tones[:third]) / third, sum(tones[-third:]) / third
            if abs(end - start) >= 0.08:
                sentence += f", and their scenes grow {'warmer' if end > start else 'colder'} by the end"
        out.append(sentence + ".")

    spoken = words_spoken(lines, len(analysis.characters))
    said = sum(spoken)
    if said:
        talker = max(analysis.characters, key=lambda c: spoken[c.id])
        out.append(f"{escape(talker.name)} has the most to say: {spoken[talker.id] / said:.0%} of the dialogue "
                   f"with a known speaker.")

    shares = charts.without_neutral(book_average(analysis.sentences, "emotions"))
    if shares:
        top = max(shares, key=shares.get)
        out.append(f"Beyond plain narration, the strongest feeling is <b>{escape(charts.short_label(top).lower())}</b> "
                   f"({shares[top]:.0%} of the emotional sentences).")
    return out


# cloth-binding colours for the shelf of book covers (cream lettering on all of them)
COVER_COLOURS = ["#5b2733", "#2c3e5c", "#2f4a3a", "#6b4a2e", "#3d3a5c", "#5a3d2b", "#274a4f", "#4a2f45"]


def shelf_css(names: list[str]) -> str:
    """Styling that turns each cover button (key cover_<file>) into the book's real cover picture
    (app/assets/covers/<file>.jpg, from scripts/download_covers.py), or a cloth-bound book when there
    is none. On a picture the button's own text is hidden: the cover shows the title."""
    import hashlib
    rules = []
    for name in names:
        colour = COVER_COLOURS[int(hashlib.md5(name.encode()).hexdigest(), 16) % len(COVER_COLOURS)]
        key = re.sub(r"[^A-Za-z0-9_-]", "-", f"cover_{name}")
        cover = ASSETS / "covers" / f"{Path(name).stem}.jpg"
        if cover.exists():
            rules.append(f'.st-key-{key} button {{ background: {colour} url("{image_uri("covers/" + cover.name)}") '
                         f'center / cover no-repeat !important; }} .st-key-{key} button p {{ opacity: 0; }}')
        else:
            rules.append(f'.st-key-{key} button {{ background: {colour} !important; }}')
    return f"""<style>
    [class*="st-key-cover_"] button {{ min-height: 0; aspect-ratio: 2 / 3; align-items: flex-start; justify-content: flex-start;
        text-align: left; padding: .9rem .8rem; border: none !important; border-radius: 3px 6px 6px 3px;
        box-shadow: inset 6px 0 0 rgba(0,0,0,.25), 0 2px 6px rgba(0,0,0,.18); transition: transform .15s ease; }}
    [class*="st-key-cover_"] button:hover {{ transform: translateY(-3px); }}
    [class*="st-key-cover_"] button p, [class*="st-key-cover_"] button div {{ white-space: normal !important;
        overflow: visible !important; text-overflow: clip !important; }}
    [class*="st-key-cover_"] button p {{ color: #f3ead7 !important; font-family: "Newsreader", Georgia, serif;
        font-size: 1.05rem; line-height: 1.22; font-weight: 500; text-align: left; width: 100%; }}
    [class*="st-key-cover_"] button > div {{ width: 100%; justify-content: flex-start; }}
    {"".join(rules)}
    </style>"""


def relative_tone(analysis: BookAnalysis, tone: float) -> float:
    """A chapter's mood compared with the book's own average, scaled so the book's darkest and
    brightest chapters reach the ends of the colour scale (for colouring chapters)."""
    mood = analysis.chapter_sentiment
    mean = sum(mood) / len(mood) if mood else 0.0
    reach = max((abs(t - mean) for t in mood), default=0) or 1
    return (tone - mean) / reach * charts.TONE_RANGE


def chapter_focus(analysis: BookAnalysis, index: int, events: list, avatars: dict, theme: dict) -> str:
    """One chapter in detail: its theme and mood, its most telling sentence, who is in it, the
    feelings that stand out against the whole book, and its typical words."""
    from analyzer.emotions import stand_out
    chapter = analysis.chapters[index]
    event = events[index] if index < len(events) else None
    sentences = [s for s in analysis.sentences if s.chapter == index]
    if not sentences:
        return ""
    mood = analysis.chapter_sentiment[index]
    tone_color = charts._tone_color(theme, relative_tone(analysis, mood))
    feels = stand_out(average_emotions([s.fine for s in sentences]), book_average(analysis.sentences, "fine"))
    theme_chip = (f'<span class="ba-chip" style="background:{tone_color}">{escape(event.theme)} · {mood:+.2f}</span>'
                  if event and event.theme else "")
    return f"""<article class="ba-focus">
      <div class="ba-kicker">Chapter {index + 1} of {len(analysis.chapters)} · {len(sentences):,} sentences</div>
      <h3>{escape(chapter.title)} {theme_chip}</h3>
      {f'<blockquote>“{escape(_shorten(event.event, 320))}”</blockquote>' if event and event.event else ""}
      <div class="ba-kicker">Who is here</div>{who_is_there(analysis, sentences[0].index, sentences[-1].index, avatars, theme, 6)}
      {f'<p><b>Feelings that stand out:</b> {escape(", ".join(feels))}</p>' if feels else ""}
      {word_chips("Its typical words", event.keywords[:8], theme["axis"]) if event and event.keywords else ""}
    </article>"""


def word_chips(title: str, words: list[str], color: str) -> str:
    """Words as chips tinted in a colour, the first (most typical) largest."""
    n = max(len(words) - 1, 1)
    chips = "".join(f'<span style="font-size:{1.35 - 0.5 * i / n:.2f}rem;'
                    f'background:color-mix(in srgb, {color} {22 - 12 * i / n:.0f}%, transparent)">{escape(w)}</span>'
                    for i, w in enumerate(words))
    return f'<div class="ba-chips"><div class="ba-kicker">{escape(title)}</div><div>{chips}</div></div>'


def emotion_peaks(analysis: BookAnalysis, events: list, theme: dict) -> str:
    """Where each emotion family peaks: the chapter where it takes the biggest share of the
    emotional sentences, with that chapter's theme, in the family's colour."""
    shares = [charts.without_neutral(mix) if mix else {} for mix in analysis.chapter_emotions]
    rows = []
    for e in charts.EMOTION_ORDER:
        values = [mix.get(e, 0) for mix in shares]
        if not any(values):
            continue
        i = max(range(len(values)), key=values.__getitem__)
        theme_word = events[i].theme.lower() if i < len(events) and events[i].theme else ""
        rows.append(f'<li><i style="background:{theme["emotions"][e]}"></i><b>{escape(charts.short_label(e))}</b> '
                    f'{escape(analysis.chapters[i].title.split(":")[0])}'
                    + (f' <span>· {escape(theme_word)}</span>' if theme_word else "") + "</li>")
    return (f'<div class="ba-peaks"><div class="ba-kicker">Where each feeling peaks</div><ul>{"".join(rows)}</ul></div>'
            if rows else "")


def who_is_there(analysis: BookAnalysis, first: int, last: int, avatars: dict, theme: dict, n: int = 4) -> str:
    """The characters named in a passage (sentences first..last), most present first, as small faces."""
    from collections import Counter
    present = Counter(m.character_id for m in analysis.mentions if first <= m.sentence_index <= last)
    if not present:
        return '<div class="ba-who">No named character</div>'
    colors = charts.character_colors(analysis, theme)
    people = [analysis.characters[i] for i, _ in present.most_common(n)]
    return ('<div class="ba-who">' + "".join(f'<span>{face(avatars, c, 22, colors[c.id])}{escape(c.name)}</span>'
                                              for c in people) + "</div>")


def _tone_word(tone: float) -> str:
    return ("very warm" if tone > 0.15 else "warm" if tone > 0.05 else "neutral" if tone > -0.05
            else "cool" if tone > -0.15 else "cold")


def pair_story(analysis: BookAnalysis, pair, events: list) -> str:
    """A relationship in a few plain sentences (markdown), from the same numbers as its charts:
    how it starts and ends, where they meet most, their lowest and highest chapters, and which
    emotion grows between them."""
    a, b = analysis.characters[pair.source].name, analysis.characters[pair.target].name
    chapters = [i for i, n in enumerate(pair.chapter_counts) if n >= 2 and pair.chapter_sentiment[i] is not None]
    if len(chapters) < 3:
        return f"{a} and {b} share {pair.count} moments, too few chapters together to follow a change."
    third = max(1, len(chapters) // 3)
    start = sum(pair.chapter_sentiment[i] for i in chapters[:third]) / third
    end = sum(pair.chapter_sentiment[i] for i in chapters[-third:]) / third

    def name(i: int) -> str:
        theme = events[i].theme.lower() if i < len(events) and events[i].theme else ""
        return f"{analysis.chapters[i].title.split(':')[0]}" + (f" ({theme})" if theme else "")
    low = min(chapters, key=lambda i: pair.chapter_sentiment[i])
    high = max(chapters, key=lambda i: pair.chapter_sentiment[i])
    busiest = max(range(len(pair.chapter_counts)), key=pair.chapter_counts.__getitem__)
    text = (f"**{a} and {b}** start out **{_tone_word(start)}** ({start:+.2f}) and end **{_tone_word(end)}** "
            f"({end:+.2f}). They meet most in {name(busiest)}, {pair.chapter_counts[busiest]} moments. "
            f"Their lowest point is {name(low)}, their highest {name(high)}.")
    parts = [p for p in pair.emotions_by_part if p]
    if len(parts) >= 2:
        early, late = charts.without_neutral(parts[0]), charts.without_neutral(parts[-1])
        if early and late:
            grows = max(late, key=lambda e: late[e] - early.get(e, 0))
            if late[grows] - early.get(grows, 0) >= 0.03:
                text += f" By the end, more **{charts.short_label(grows).lower()}** runs between them."
    return text


def _brief_html(analysis: BookAnalysis, events: list) -> str:
    sentences = in_brief(analysis, events)
    return (f'<div class="ba-brief"><div class="ba-kicker">In brief</div><p>{" ".join(sentences)}</p></div>'
            if sentences else "")


def hero(analysis: BookAnalysis, title: str, events: list, theme: dict) -> str:
    """The book's title over a 'mood barcode': one stripe per chapter, coloured by its
    mood (blue brighter, red darker) and as tall as the chapter is emotional."""
    intensity = [1 - mix.get("neutral", 1) if mix else 0.5 for mix in analysis.chapter_emotions]
    top = max(intensity) or 1
    # colours relative to this book: compared with its own average mood, its darkest and brightest
    # chapters get the full red and blue (a gloomy book is not red from end to end)
    stripes = "".join(
        f'<i style="height:{20 + 80 * level / top:.0f}%;'
        f'background:{charts._tone_color(theme, relative_tone(analysis, tone))}" '
        f'title="{escape(chapter.title)} · {escape(event.theme)} · mood {tone:+.2f}"></i>'
        for chapter, event, tone, level in zip(analysis.chapters, events, analysis.chapter_sentiment, intensity)
    )
    shares = charts.without_neutral(book_average(analysis.sentences, "emotions"))
    author = f'<div class="ba-author">by {escape(analysis.author)}</div>' if analysis.author else ""
    words = sum(len(s.text.split()) for s in analysis.sentences)
    return f"""<section class="ba-hero ba-anchor" id="overview">
      <div class="ba-kicker">A computational reading · {len(analysis.chapters)} chapters · {words:,} words</div>
      <h1>{escape(title)}</h1>{author}
      <p class="ba-lede">Every sentence of the novel has been read by machine-learning models running on this computer,
      scored for its mood and emotions, and searched for characters and places. The contents bar above jumps to each
      part of the reading; this first part gives the whole book at a glance.</p>
      <figure class="ba-figure">
        <div class="ba-ribbon">{stripes}</div>
        <div class="ba-axis"><span>Beginning</span><span>Middle</span><span>End</span></div>
        {_emotion_legend(theme, shares) if shares else ""}
        <figcaption><b>The mood of each chapter</b>One stripe per chapter, from first to last:
        <span style="color:var(--ba-bright);font-weight:600">blue</span> where the mood
        is bright, <span style="color:var(--ba-dark);font-weight:600">red</span> where it
        turns dark (compared with the rest of the book), taller where emotions run high. Hover a stripe for its chapter.
        </figcaption>
      </figure>
      {_brief_html(analysis, events)}
    </section>"""


def landing() -> str:
    """The page before any book is chosen: what the site does, and how."""
    steps = (
        ("I · Read", "Every sentence", "The novel is split into chapters and sentences; names, places and pronouns "
                                       "are found and linked to the characters they refer to."),
        ("II · Measure", "Tone and feeling", "Trained classifiers score the mood of each sentence and 38 fine emotions, "
                                             "from grief and guilt to gratitude and curiosity."),
        ("III · Map", "The shape of the story", "Who meets whom, where the story happens, how each character's "
                                                "journey rises and falls, and which classic shape the plot follows."),
    )
    method = "".join(f'<div><span class="ba-kicker">{a}</span><b>{b}</b><p>{c}</p></div>' for a, b, c in steps)
    return f"""<section class="ba-hero"><div class="ba-split"><div>
      <div class="ba-kicker">A computational reading</div>
      <h1>Turn a novel into pictures.</h1>
      <div class="ba-author">Characters, relationships, places and moods, drawn from the text itself</div>
      <p class="ba-lede">Upload an English novel as a <code>.txt</code> file in the sidebar, or open one of the
      50 free classics below, from <i>Pride and Prejudice</i> and <i>Dracula</i> to <i>Moby Dick</i>
      and <i>The Great Gatsby</i>. Every model
      runs on this computer: the book is never sent anywhere.</p>
      </div>
      <figure class="ba-mascot"><img src="{image_uri("raccoon.jpg")}" alt="The Book Visualizer raccoon in headphones at a keyboard">
      <figcaption>Your reader for today: the raccoon. Careful, quick, and fond of a good ending.</figcaption></figure>
      </div>
      <div class="ba-method">{method}</div>
    </section>"""


# --- KPI cards ------------------------------------------------------------------------------


def cast_strip(analysis: BookAnalysis, looks: dict, avatars: dict, theme: dict, n: int = 8) -> str:
    """The main characters as portrait cards: avatar, name, their look in words and
    what it is based on (the book's own words, or the story when it says nothing)."""
    from analyzer.emotions import stand_out
    from analyzer.roles import story_roles
    from avatars import look_in_words
    colors = charts.character_colors(analysis, theme)
    from analyzer.narration import narrator
    teller = narrator(analysis, find_lines(analysis.sentences, analysis.mentions))
    roles = story_roles(analysis, n, teller)
    book_fine = book_average(analysis.sentences, "fine")
    cards = []
    people = charts.top_characters(analysis, n)
    if teller is not None and analysis.characters[teller] not in people:  # the narrator always has a card, first
        people = [analysis.characters[teller]] + people[:-1]
    elif teller is not None:
        people = [analysis.characters[teller]] + [c for c in people if c.id != teller]
    for c in people:
        look = looks.get(c.id)
        if not look:
            continue
        feels = stand_out(analysis.character_fine[c.id], book_fine) if analysis.character_fine else []
        source = ("From the book: " + ", ".join(look.evidence)) if look.evidence else "Imagined from the story"
        # one compact figure per person, side by side; the details are in the tooltip (no mention counts up top)
        details = " · ".join(x for x in (", ".join(roles.get(c.id, [])), look_in_words(look),
                                          ("stands out: " + ", ".join(feels)) if feels else "", source) if x)
        role = roles.get(c.id, [""])[0]
        cards.append(f'<figure title="{escape(c.name)}: {escape(details)}">{face(avatars, c, 64).replace(chr(32) + "title=" + chr(34) + escape(c.name) + chr(34), "")}'
                     f'<b style="color:{colors[c.id]}">{escape(c.name)}</b>'
                     f'<span class="role">{escape(role)}</span></figure>')
    return (f'<section class="ba-castrow"><div class="ba-kicker">Dramatis personae · the cast</div>'
            f'<div class="row">{"".join(cards)}</div>'
            f'<p class="note">Portraits are drawn from what the book says about each character (where it says nothing, '
            f'the story fills in the blanks). Hover a portrait for the details.</p></section>')


def kpis(analysis: BookAnalysis, events: list, theme: dict, avatars: dict | None = None) -> list[dict]:
    """The headline numbers of the book, each with a small picture.
    Each card: icon, label, value, note, art (HTML), and optional wide/tone."""
    names = {c.id: c for c in analysis.characters}
    colors = charts.character_colors(analysis, theme)
    ranked = charts.top_characters(analysis, len(analysis.characters))
    main = ranked[0]
    mood = analysis.chapter_sentiment
    book_tone = sum(mood) / len(mood)
    shares = charts.without_neutral(book_average(analysis.sentences, "emotions"))
    words = sum(len(s.text.split()) for s in analysis.sentences)
    lines = find_lines(analysis.sentences, analysis.mentions)
    spoken = words_spoken(lines, len(analysis.characters))
    talker = max(analysis.characters, key=lambda c: spoken[c.id])
    said = sum(line.words for line in lines)
    negative, middle, positive = theme["diverging"]
    from analyzer.narration import narrator
    teller = narrator(analysis, lines)  # in a first-person book the narrator is the main character
    if teller is not None:
        main = analysis.characters[teller]

    cards = [
        dict(icon="📚", label="Chapters", value=f"{len(analysis.chapters)}",
             note="the mood of each, from first to last", art=_sparkline(mood, theme["ink2"], theme, zero=True)),
        dict(icon="✍️", label="Sentences", value=f"{len(analysis.sentences):,}",
             note=f"≈ {words:,} words · about {words / 250 / 60:.0f} hours of reading",
             art=_mini_bars([sum(s.chapter == i for s in analysis.sentences) for i in range(len(analysis.chapters))],
                            theme["muted"])),
        dict(icon="👥", label="Characters", value=f"{len(analysis.characters)}",
             note="the most mentioned: " + ", ".join(c.name for c in ranked[:3]),
             art=_faces(ranked[:8], colors, avatars)),
        dict(icon="💬", label="Talks the most", value=escape(talker.name) if spoken[talker.id] else "—", small=True,
             note=(f"{spoken[talker.id]:,} words, {spoken[talker.id] / max(said, 1):.0%} of all the dialogue"
                   if spoken[talker.id] else "no dialogue with a known speaker"),
             art=_stack([(spoken[c.id], colors[c.id], f"{c.name}: {spoken[c.id]:,} words")
                         for c in sorted(analysis.characters, key=lambda c: -spoken[c.id])[:8] if spoken[c.id]])),
        dict(icon="👑", label="Narrator" if teller is not None else "Main character", value=escape(main.name),
             small=True,
             note=("tells the story as “I”; named by others " if teller is not None else "")
                  + f"in {sum(1 for n in analysis.mentions_by_chapter[main.id] if n)} of {len(analysis.chapters)} chapters",
             art=_mini_bars(analysis.mentions_by_chapter[main.id], colors[main.id])),
        dict(icon="🌗", label="Overall mood", value=f"{book_tone:+.2f}",
             note="brighter than neutral" if book_tone > 0.02 else "darker than neutral" if book_tone < -0.02
             else "close to neutral",
             art=f'<div class="ba-gauge"><b style="left:{(max(-0.3, min(0.3, book_tone)) + 0.3) / 0.6:.1%}"></b></div>'),
    ]
    if shares:
        top = max(shares, key=shares.get)
        # the fine emotions that make up most of that family, e.g. "mostly disapproval, disgust"
        fine = book_average(analysis.sentences, "fine")
        members = sorted((e for e in FAMILIES[top] if fine.get(e)), key=fine.get, reverse=True)[:2]
        cards.append(dict(icon="🎭", label="Strongest emotion", value=charts.short_label(top),
                          note=f"{shares[top]:.0%} of the emotional sentences"
                               + (f" · mostly {', '.join(members)}" if members else ""),
                          art=_stack([(shares[e], theme["emotions"][e], f"{charts.EMOTION_LABELS[e]} {shares[e]:.0%}")
                                      for e in charts.EMOTION_ORDER])))
    else:
        cards.append(dict(icon="🎭", label="Strongest emotion", value="—", note="emotions were not detected", art=""))
    if analysis.relationships:
        pair = analysis.relationships[0]
        a, b = names[pair.source], names[pair.target]
        cards.append(dict(icon="💞", label="Closest pair", value=f"{escape(a.name)} &amp; {escape(b.name)}", small=True,
                          note=f"{pair.count} moments together · tone {pair.sentiment:+.2f}",
                          art=_faces([a, b], colors, avatars)))
    else:
        cards.append(dict(icon="💞", label="Closest pair", value="—", note="no pairs found", art=""))

    order = sorted(range(len(mood)), key=lambda i: mood[i])
    for icon, label, ch, color in (("🌑", "Darkest chapter", order[0], negative),
                                   ("☀️", "Brightest chapter", order[-1], positive)):
        cards.append(dict(
            icon=icon, label=label, small=True, wide=True, tone=color,
            value=f'{escape(analysis.chapters[ch].title)} <span class="ba-chip" style="background:{color}">'
                  f'{escape(events[ch].theme)} · {mood[ch]:+.2f}</span>',
            note="", art=f"<blockquote>“{escape(_shorten(events[ch].event, 220))}”</blockquote>"))
    return cards


def _shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def _as_img(art: str) -> str:
    """st.html removes inline SVG, so a drawing is shown as a picture (a data URI) instead."""
    if not art.startswith("<svg"):
        return art
    svg = art if "xmlns=" in art else art.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    return f'<img class="spark" alt="" src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}">'


def kpi_html(cards: list[dict]) -> str:
    """A compact strip of tiles: icon and label, the value, a one-line note (the whole note on hover)
    and a small picture. Wide cards (the darkest and brightest chapter) put the picture beside the text."""
    out = []
    for c in cards:
        classes = "ba-kpi" + (" wide" if c.get("wide") else "") + (" toned" if c.get("tone") else "")
        style = f' style="--tone:{c["tone"]}"' if c.get("tone") else ""
        note = f'<div class="note" title="{escape(c["note"])}">{escape(c["note"])}</div>' if c["note"] else ""
        icon = f'<i aria-hidden="true">{c["icon"]}</i>' if c.get("icon") else ""
        out.append(f'<div class="{classes}"{style}><div class="head"><div class="label">{icon}{escape(c["label"])}</div>'
                   f'<div class="value{" small" if c.get("small") else ""}">{c["value"]}</div>{note}</div>'
                   f'<div class="art">{_as_img(c["art"])}</div></div>')
    return f'<div class="ba-kpis">{"".join(out)}</div>'


def shape_neighbours(best: str, same_shape: list[str], closest: list[tuple[str, float]]) -> str:
    """Under the story-shape card: the famous books whose mood moves most like this one,
    and the ones that share its shape."""
    if not closest:
        return ""
    near = ", ".join(f"<i>{escape(t)}</i> ({max(r, 0):.0%})" for t, r in closest)
    same = (f"<p>Other <b>{escape(best)}</b> stories among the famous books: "
            + ", ".join(f"<i>{escape(t)}</i>" for t in same_shape) + ".</p>") if same_shape else ""
    return f"""<div class="ba-shape">
      <div class="ba-kicker">Compared with the famous books</div>
      <p>Its mood moves most like {near}.</p>{same}
      <p class="key">The % is how closely the two mood curves match.</p>
    </div>"""


def _rank(value: float, others: list[float], more: str, less: str) -> str:
    """'more than 7 of 10 famous books' (or the opposite, whichever is the majority)."""
    if not others:
        return ""
    above = sum(value > o for o in others)
    if above >= len(others) / 2:
        return f"{more} than {above} of {len(others)} famous books"
    return f"{less} than {sum(value < o for o in others)} of {len(others)} famous books"


def pace_cards(pace, others: list[dict]) -> list[dict]:
    """KPI cards for the whole book's pace, each compared with the famous books."""
    from analyzer.pace import grade_label

    hours = pace.minutes / 60
    when = f"{hours:.1f} hours" if hours >= 1 else f"{pace.minutes:.0f} minutes"
    col = {k: [o[k] for o in others] for k in ("hours", "grade", "dialogue", "richness")}
    return [
        dict(icon="⏱️", label="Reading time", value=when, art="", small=True,
             note=f"{pace.words:,} words at {230} a minute; " + _rank(hours, col["hours"], "longer", "shorter")),
        dict(icon="🎓", label="Reading level", value=f"Grade {max(pace.grade, 1):.0f}", art="", small=True,
             note=f"{grade_label(pace.grade)}; {pace.sentence_length:.0f} words per sentence; "
                  + _rank(pace.grade, col["grade"], "harder", "easier")),
        dict(icon="💬", label="Dialogue", value=f"{pace.dialogue:.0%}", art="",
             note="of the words are spoken; " + _rank(pace.dialogue, col["dialogue"], "chattier", "quieter")),
        dict(icon="🔤", label="Vocabulary", value=f"{pace.richness:.0%}", art="",
             note="different words in every 100; " + _rank(pace.richness, col["richness"], "richer", "plainer")),
    ]
