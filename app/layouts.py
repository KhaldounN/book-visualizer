"""Page layouts to try out, picked with ?layout= in the address (or the sidebar).

The content is the same in every layout; only how the parts are arranged and styled changes:
- classic   one continuous scholarly page with a sticky contents bar (the original)
- tabs      convenient: one tab per part, nothing to scroll past
- guided    convenient: one part at a time, with big Previous / Next buttons (good on a phone)
- cinematic impressive: big title, giant numbered part openers, figures full width, a floating dock
- bento     impressive: a wide gallery of rounded tiles, two figures side by side
"""

import streamlit as st

LAYOUTS = {
    "classic": ("Classic", "One long scholarly page (the current layout)"),
    "tabs": ("Tabs", "Convenient: one tab per part"),
    "guided": ("Step by step", "Convenient: one part at a time, Previous / Next"),
    "cinematic": ("Cinematic", "Impressive: big openers, full-width figures"),
    "bento": ("Gallery", "Impressive: a grid of tiles"),
}
STACKED = {"cinematic", "bento"}  # a figure's explanation sits above its chart, not beside it


def current() -> str:
    asked = st.query_params.get("layout", "classic")
    return asked if asked in LAYOUTS else "classic"


def css(layout: str, serif: str, sans: str) -> str:
    """Extra styling on top of design.page_css for one layout ('' for classic)."""
    return {"tabs": _TABS, "guided": _GUIDED, "cinematic": _CINEMATIC, "bento": _BENTO}.get(layout, "") \
        .replace("SERIF", serif).replace("SANS", sans)


# --- Tabs: Streamlit's own tabs, styled by page_css (sticky small-caps tab bar) ------------------
_TABS = """<style>
.stMainBlockContainer .stTabs [role="tablist"] { overflow-x: auto; scrollbar-width: none; }
.stMainBlockContainer [data-testid="stTab"] { flex: none; }
.stMainBlockContainer [data-baseweb="tab-panel"] { padding-top: .4rem; }
/* each tab starts again at Part I / Figure 1 */
.stMainBlockContainer [data-baseweb="tab-panel"] { counter-reset: part fig; }
</style>"""

# --- Step by step: a sticky row of part buttons, one part shown, big Previous / Next -------------
_GUIDED = """<style>
.st-key-hidden-parts, div:has(> .st-key-hidden-parts) { display: none !important; }
.st-key-toc { padding: .6rem 0 .5rem; }
.st-key-toc [data-testid="stButtonGroup"] { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; }
.st-key-toc [data-testid="stButtonGroup"] button { flex: none; }
.st-key-step { display: flex; align-items: baseline; gap: .7rem; }
.ba-step { font: 600 .7rem/1 SANS; letter-spacing: .16em; text-transform: uppercase; color: var(--ba-muted);
    margin: .3rem 0 0; }
.ba-step b { color: var(--ba-gold); }
.ba-step i { display: block; height: 3px; margin-top: .6rem; border-radius: 3px; background: var(--ba-line); overflow: hidden; }
.ba-step i::after { content: ""; display: block; height: 100%; width: var(--done); background: var(--ba-gold);
    border-radius: 3px; transition: width .4s ease; }
.st-key-guided-nav { margin-top: 2.5rem; padding-top: 1.4rem; border-top: 1px solid var(--ba-rule); }
.st-key-guided-nav button { min-height: 3.4rem; font-size: 1rem; }
.stMainBlockContainer [data-testid="stHeading"] h2::before { content: "Part"; }
/* phones: the part buttons wrap to several rows, so they scroll away instead of staying on top */
@media (max-width: 640px) { div:has(> .st-key-toc) { position: static !important; } }
</style>"""

# --- Cinematic -------------------------------------------------------------------------------
_CINEMATIC = """<style>
/* the title page: a full-width band with a soft glow of the accent colour */
.ba-hero { padding: 5rem 2rem 3rem; margin: 0 -2rem; text-align: center; overflow: hidden;
    background: radial-gradient(ellipse 60% 70% at 50% 0%, color-mix(in srgb, var(--ba-gold) 22%, transparent), transparent 70%); }
.ba-hero h1 { font-size: clamp(3rem, 9vw, 7.5rem) !important; line-height: .95 !important; letter-spacing: -.04em !important; }
.ba-hero > * { margin-left: auto; margin-right: auto; }
.ba-hero p, .ba-lede { margin-left: auto !important; margin-right: auto !important; }

/* each part opens like a film chapter: a giant numeral behind a centred title */
.stMainBlockContainer [data-testid="stHeading"] h2 { position: relative; text-align: center; border: none !important;
    font-size: clamp(2.4rem, 5vw, 4rem) !important; padding: 7rem 0 1rem !important; letter-spacing: -.03em; }
.stMainBlockContainer [data-testid="stHeading"] h2::before { position: absolute; left: 0; right: 0; top: 1.2rem;
    content: counter(part, upper-roman) !important; font: 500 9rem/1 SERIF !important; letter-spacing: -.04em !important;
    color: transparent !important; -webkit-text-stroke: 1px var(--ba-gold); opacity: .45; z-index: -1; }
.stMainBlockContainer [data-testid="stCaptionContainer"] { text-align: center; max-width: 40rem; margin: 0 auto; }

/* figures: no box, a centred caption over a full-width chart */
[class*="st-key-panel-"] { background: transparent !important; border: none !important; padding: 2.5rem 0 1rem !important; }
[class*="st-key-panel-"] > div:first-child [data-testid="stMarkdownContainer"] { max-width: 44rem; margin: 0 auto; text-align: center; }
[class*="st-key-panel-"] h4 { font-size: 2rem !important; text-align: center; }
[class*="st-key-panel-"] .stPlotlyChart { border-radius: 18px; background: var(--ba-surface);
    box-shadow: 0 30px 60px -30px rgba(0,0,0,.35); padding: .6rem; }

/* fade figures in as they scroll into view (where the browser supports it) */
@supports (animation-timeline: view()) {
  [class*="st-key-panel-"] { animation: ba-rise linear both; animation-timeline: view(); animation-range: entry 0% entry 40%; }
  @keyframes ba-rise { from { opacity: 0; transform: translateY(40px); } to { opacity: 1; transform: none; } }
}

/* the contents bar becomes a floating dock at the bottom of the screen */
div:has(> .st-key-toc) { position: static !important; height: 0; }
.st-key-toc { position: fixed !important; bottom: 1.1rem; right: 1.5rem; left: auto; z-index: 999;
    width: auto !important; max-width: min(62rem, calc(100vw - 3rem)); border: 1px solid var(--ba-rule) !important; border-radius: 999px;
    background: color-mix(in srgb, var(--ba-page) 78%, transparent) !important; backdrop-filter: blur(14px);
    box-shadow: 0 12px 40px -10px rgba(0,0,0,.35); padding: 0 1.2rem; }
.st-key-toc .ba-toc { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; padding: .8rem 0 !important; }
.st-key-toc .ba-toc a { flex: none; }
.stMainBlockContainer [id] { scroll-margin-top: 4.5rem !important; }
.ba-foot { margin-bottom: 4.5rem; }
</style>"""

# --- Gallery (bento) -------------------------------------------------------------------------
_BENTO = """<style>
.stMainBlockContainer { --tile: 22px; }
/* the parts with figures become a two-column grid of tiles; headings and the rest span both */
[class*="st-key-part-"]:is(.st-key-part-story, .st-key-part-mood, .st-key-part-people, .st-key-part-places) {
    display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1.1rem; align-items: stretch; }
:is(.st-key-part-story, .st-key-part-mood, .st-key-part-people, .st-key-part-places) > * { grid-column: 1 / -1; min-width: 0; }
:is(.st-key-part-story, .st-key-part-mood, .st-key-part-people, .st-key-part-places) > div:has(> [class*="st-key-panel-"]) {
    grid-column: auto; }
/* a tile without a chart (cards, tables, text) is too wide for half the page: it gets the whole row */
:is(.st-key-part-story, .st-key-part-mood, .st-key-part-people, .st-key-part-places) > div:has(> [class*="st-key-panel-"]):is(:not(:has(.stPlotlyChart)), :has(.ba-kpis)) {
    grid-column: 1 / -1; }
:is(.st-key-part-story, .st-key-part-mood, .st-key-part-people, .st-key-part-places) > div:has(> [class*="st-key-panel-"]) > * { height: 100%; }

/* tiles: big rounded corners, a soft shadow, a thin glowing top edge */
[class*="st-key-panel-"] { border-radius: var(--tile) !important; border: 1px solid var(--ba-line) !important;
    padding: 1.6rem 1.6rem 1.4rem !important; position: relative; overflow: hidden;
    box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 18px 40px -24px rgba(0,0,0,.28); transition: transform .25s ease, box-shadow .25s ease; }
[class*="st-key-panel-"]::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 3px;
    background: linear-gradient(90deg, var(--ba-dark), var(--ba-gold), var(--ba-bright)); opacity: .85; }
[class*="st-key-panel-"]:hover { transform: translateY(-3px); box-shadow: 0 1px 2px rgba(0,0,0,.04), 0 28px 50px -24px rgba(0,0,0,.35); }
[class*="st-key-panel-"] h4 { font-size: 1.3rem !important; }
.ba-kpis > * { border-radius: var(--tile) !important; }

/* part headings: a big left-aligned label with a pill number */
.stMainBlockContainer [data-testid="stHeading"] h2 { border: none !important; padding-top: 3.2rem !important; font-size: 2.6rem !important; }
.stMainBlockContainer [data-testid="stHeading"] h2::before { display: block !important; width: fit-content; padding: .35rem .7rem;
    border-radius: 999px; background: color-mix(in srgb, var(--ba-gold) 14%, transparent); }

/* contents: pill chips */
.st-key-toc { border: none !important; }
.ba-toc { gap: .4rem !important; }
.ba-toc a { border: 1px solid var(--ba-line) !important; border-radius: 999px; padding: .45rem .8rem !important;
    background: var(--ba-surface); }
.ba-toc a:hover { border-color: var(--ba-gold) !important; }

@media (max-width: 900px) {
  [class*="st-key-part-"] { grid-template-columns: 1fr !important; }
}
</style>"""
