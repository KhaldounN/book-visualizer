"""The look of the website: page styling, the hero banner and the KPI cards.

Everything here returns HTML/CSS strings that the app shows with `st.html`.
Colours come from `charts.THEMES`, so light and dark mode both work.
"""

import base64
from functools import cache
from html import escape
from pathlib import Path

import charts
from analyzer.dialogue import find_lines, words_spoken
from analyzer.emotions import FAMILIES, average_emotions
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
SERIF = '"Fraunces", Georgia, "Times New Roman", serif'
# used only for small decorations: a vivid orange (the raccoon's headphones) in the bright
# light mode, old gold in dark mode
ACCENT = {"light": "#e8590c", "dark": "#e0b25b"}
# In light mode the hero gets brighter glows: sky blue, a little sunshine and rose
LIGHT_HERO = """.ba-hero { background:
    radial-gradient(70% 110% at 0% 0%, rgba(57,135,229,.22), transparent 60%),
    radial-gradient(45% 80% at 100% 0%, rgba(255,200,40,.22), transparent 60%),
    radial-gradient(70% 120% at 100% 100%, rgba(232,73,72,.16), transparent 60%), #ffffff !important; }"""


def page_css(theme: dict, mode: str) -> str:
    """Styling for the whole page: section headings, visualization cards, KPI cards."""
    t, gold = theme, ACCENT[mode]
    glow = "0 1px 2px rgba(30,60,120,.06), 0 10px 28px rgba(30,60,120,.09)" if mode == "light" \
        else "0 1px 2px rgba(0,0,0,.4), 0 12px 32px rgba(0,0,0,.35)"
    return f"""<style>
    :root {{ --ba-ink: {t["ink"]}; --ba-ink2: {t["ink2"]}; --ba-muted: {t["muted"]}; --ba-line: {t["grid"]};
             --ba-surface: {t["surface"]}; --ba-gold: {gold}; --ba-glow: {glow};
             --ba-dark: {t["diverging"][0]}; --ba-bright: {t["diverging"][2]}; }}

    /* Section headings: a numbered gold kicker above a big serif title */
    .stMainBlockContainer {{ counter-reset: section; }}
    .stMainBlockContainer [data-testid="stHeading"] h2 {{
        font-family: {SERIF}; font-size: 2.3rem; font-weight: 600; letter-spacing: -.01em;
        padding-top: 2.6rem; }}
    .stMainBlockContainer [data-testid="stHeading"] h2::before {{
        counter-increment: section; content: "Chapter " counter(section, upper-roman);
        display: block; font: 600 .72rem/1 system-ui, sans-serif; letter-spacing: .22em;
        text-transform: uppercase; color: var(--ba-gold); margin-bottom: .55rem; }}
    .stMainBlockContainer [data-testid="stHeading"] h2::after {{
        content: ""; display: block; width: 64px; height: 3px; margin-top: .7rem; border-radius: 2px;
        background: linear-gradient(90deg, var(--ba-dark), var(--ba-gold), var(--ba-bright)); }}
    .stMainBlockContainer h4 {{ font-family: {SERIF}; font-weight: 600; font-size: 1.35rem; }}

    /* Each visualization sits on its own card */
    [class*="st-key-panel-"] {{
        background: var(--ba-surface); border: 1px solid var(--ba-line) !important; border-radius: 16px;
        box-shadow: var(--ba-glow); padding: 1.4rem 1.5rem; transition: border-color .25s ease; }}
    [class*="st-key-panel-"]:hover {{ border-color: color-mix(in srgb, var(--ba-gold) 55%, var(--ba-line)) !important; }}

    /* Hero */
    .ba-hero {{ position: relative; overflow: hidden; border-radius: 22px; padding: 2.2rem 2.2rem 1.6rem;
        border: 1px solid var(--ba-line); box-shadow: var(--ba-glow);
        background: radial-gradient(90% 120% at 0% 0%, color-mix(in srgb, var(--ba-bright) 16%, transparent), transparent 60%),
                    radial-gradient(70% 120% at 100% 100%, color-mix(in srgb, var(--ba-dark) 14%, transparent), transparent 60%),
                    var(--ba-surface); }}
    {LIGHT_HERO if mode == "light" else ""}
    .ba-kicker {{ font: 600 .72rem/1 system-ui, sans-serif; letter-spacing: .22em; text-transform: uppercase;
        color: var(--ba-gold); }}
    .ba-hero h1 {{ font-family: {SERIF}; font-size: clamp(2.2rem, 5vw, 3.8rem); line-height: 1.05; margin: .7rem 0 .3rem;
        font-weight: 700; letter-spacing: -.02em; color: var(--ba-ink); padding: 0; }}
    .ba-author {{ font-family: {SERIF}; font-style: italic; font-size: 1.15rem; color: var(--ba-ink2); }}
    .ba-lede {{ max-width: 46rem; color: var(--ba-ink2); margin: 1rem 0 1.4rem; line-height: 1.55; }}
    .ba-ribbon {{ display: flex; align-items: flex-end; gap: 2px; height: 74px; }}
    .ba-ribbon i {{ flex: 1; min-width: 2px; border-radius: 2px 2px 0 0; transition: transform .15s ease; transform-origin: bottom; }}
    .ba-ribbon i:hover {{ transform: scaleY(1.12); filter: brightness(1.15); }}
    .ba-axis {{ display: flex; justify-content: space-between; font-size: .75rem; color: var(--ba-muted);
        border-top: 1px solid var(--ba-line); padding-top: .4rem; margin-top: 2px; }}
    .ba-legend {{ display: flex; flex-wrap: wrap; gap: .4rem 1.1rem; margin-top: 1rem; font-size: .8rem; color: var(--ba-ink2); }}
    .ba-legend span {{ display: inline-flex; align-items: center; gap: .4rem; }}
    .ba-legend i {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}

    /* KPI cards */
    .ba-kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin: 1.2rem 0 .4rem; }}
    .ba-kpi {{ position: relative; background: var(--ba-surface); border: 1px solid var(--ba-line); border-radius: 16px;
        padding: 1rem 1.1rem 1.05rem; box-shadow: var(--ba-glow); display: flex; flex-direction: column; gap: .35rem;
        min-height: 150px; transition: transform .2s ease, border-color .2s ease; }}
    .ba-kpi:hover {{ transform: translateY(-3px); border-color: color-mix(in srgb, var(--ba-gold) 55%, var(--ba-line)); }}
    .ba-kpi.wide {{ grid-column: span 2; }}
    .ba-kpi .label {{ display: flex; align-items: center; gap: .45rem; font: 600 .7rem/1 system-ui, sans-serif;
        letter-spacing: .14em; text-transform: uppercase; color: var(--ba-muted); }}
    .ba-kpi .label b {{ font-size: 1rem; letter-spacing: 0; }}
    .ba-kpi .value {{ font-family: {SERIF}; font-size: 2.1rem; font-weight: 600; line-height: 1.1; color: var(--ba-ink);
        overflow-wrap: anywhere; }}
    .ba-kpi .value.small {{ font-size: 1.5rem; }}
    .ba-kpi .note {{ font-size: .82rem; color: var(--ba-ink2); line-height: 1.4; }}
    .ba-kpi .art {{ margin-top: auto; padding-top: .4rem; }}
    .ba-kpi svg {{ display: block; width: 100%; height: 38px; overflow: visible; }}
    .ba-bar {{ display: flex; height: 10px; border-radius: 5px; overflow: hidden; gap: 2px; }}
    .ba-gauge {{ position: relative; height: 10px; border-radius: 5px;
        background: linear-gradient(90deg, var(--ba-dark), {t["diverging"][1]}, var(--ba-bright)); }}
    .ba-gauge b {{ position: absolute; top: -5px; width: 4px; height: 20px; margin-left: -2px; border-radius: 2px;
        background: var(--ba-ink); box-shadow: 0 0 0 2px var(--ba-surface); }}
    .ba-faces {{ display: flex; }}
    .ba-faces span {{ width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center; color: #fff;
        font: 600 .8rem/1 system-ui, sans-serif; border: 2px solid var(--ba-surface); margin-right: -8px; }}
    .ba-chip {{ display: inline-block; font-size: .72rem; font-weight: 600; letter-spacing: .04em; padding: .2rem .55rem;
        border-radius: 99px; color: #fff; }}
    .ba-kpi blockquote {{ margin: .25rem 0 0; padding: 0 0 0 .8rem; border-left: 3px solid var(--tone);
        font-family: {SERIF}; font-style: italic; font-size: .98rem; line-height: 1.45; color: var(--ba-ink2); }}
    .ba-kpi.toned {{ background: linear-gradient(135deg, color-mix(in srgb, var(--tone) 12%, var(--ba-surface)), var(--ba-surface) 60%); }}

    .ba-cast {{ list-style: none; padding: 0; margin: 0; display: grid; gap: .3rem; font-size: .88rem; }}
    .ba-cast li {{ display: flex; align-items: center; gap: .5rem; margin: 0; }}
    .ba-cast i {{ width: 12px; height: 12px; border-radius: 50%; flex: none; }}
    .ba-avatar {{ border-radius: 50%; flex: none; vertical-align: middle; }}
    .ba-dot {{ display: inline-block; border-radius: 50%; flex: none; vertical-align: middle; }}
    .ba-faces img {{ margin-right: -6px; }}
    .ba-castgrid {{ margin: 1.4rem 0 .4rem; }}
    .ba-castgrid .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px;
        margin-top: .7rem; }}
    .ba-castgrid article {{ display: flex; flex-direction: column; align-items: center; text-align: center; gap: .3rem;
        padding: 1rem .7rem .9rem; border: 1px solid var(--ba-line); border-radius: 16px; background: var(--ba-surface);
        box-shadow: var(--ba-glow); transition: transform .2s ease; }}
    .ba-castgrid article:hover {{ transform: translateY(-3px); }}
    .ba-castgrid article b {{ font-family: {SERIF}; font-size: 1.1rem; margin-top: .3rem; }}
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
    .ba-shape {{ margin-top: 1rem; padding: 1rem 1.1rem; border-radius: 14px; border: 1px solid var(--ba-line);
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
        margin-top: 1.5rem; padding: 1.6rem 1.8rem; border-radius: 22px; border: 1px solid var(--ba-line);
        background: var(--ba-surface); box-shadow: var(--ba-glow); }}
    .ba-about figure {{ margin: 0; text-align: center; }}
    .ba-about img {{ width: 100%; aspect-ratio: 1; object-fit: cover; object-position: 60% 30%; border-radius: 50%;
        box-shadow: 0 0 0 3px var(--ba-gold); }}
    .ba-about figcaption {{ font-size: .78rem; color: var(--ba-muted); margin-top: .6rem; font-style: italic; }}
    .ba-about h2 {{ font-family: {SERIF}; font-size: 1.6rem; color: var(--ba-ink); margin: 0 0 .6rem; padding: 0; }}
    .ba-about p {{ color: var(--ba-ink2); line-height: 1.6; max-width: 46rem; margin: 0 0 .7rem; }}
    .ba-about .ba-links a {{ color: var(--ba-ink); font-weight: 600; text-decoration: none;
        border-bottom: 1px solid var(--ba-gold); }}
    .ba-mascot img {{ width: 100%; aspect-ratio: 4 / 5; object-fit: cover; object-position: 60% 30%; border-radius: 18px;
        box-shadow: var(--ba-glow); border: 1px solid var(--ba-line); }}
    .ba-mascot figcaption {{ font-size: .8rem; font-style: italic; color: var(--ba-muted); margin-top: .5rem; }}
    .ba-working {{ display: grid; grid-template-columns: 300px minmax(0, 1fr); gap: 1.6rem; align-items: center;
        padding: 1.4rem 1.6rem; border-radius: 20px; border: 1px solid var(--ba-line); background: var(--ba-surface);
        box-shadow: var(--ba-glow); margin-bottom: .8rem; }}
    .ba-working img {{ width: 170px; aspect-ratio: 1; object-fit: cover; object-position: 55% 62%; border-radius: 16px;
        animation: ba-typing .5s ease-in-out infinite alternate; }}
    .ba-working img.ba-scene {{ width: 300px; aspect-ratio: 32 / 22; border-radius: 16px; animation: none;
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

    @media (max-width: 900px) {{ .ba-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 560px) {{
        .ba-kpis {{ grid-template-columns: 1fr; }} .ba-kpi.wide {{ grid-column: auto; }}
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
    "paragraphs": [
        "Hi, I'm Khaldoun. I live in Barcelona and work where data, pricing and tech meet: today at Criteo, "
        "and before that as a pricing consultant in IT at Ingram Micro, after starting my career in Amman, "
        "Jordan. I studied data analysis and digital innovation at the University of Barcelona, which is "
        "where Python and machine learning first got me hooked.",
        "Book Analyzer is a passion project, made purely for fun while I keep learning AI and programming. "
        "It began as a small experiment in 2020 and grew into this. Every AI model runs on my own computer, "
        "so your book never leaves it. Expect the odd mistake: the raccoon is still learning too.",
    ],
    "links": [("LinkedIn", "https://www.linkedin.com/in/khaldoun-al-naierat"),
              ("GitHub", "https://github.com/KhaldounN")],
}


def about() -> str:
    """Who made the site: a short, friendly card with the raccoon."""
    text = "".join(f"<p>{escape(p)}</p>" for p in ABOUT["paragraphs"])
    links = " · ".join(f'<a href="{url}" target="_blank" rel="noopener">{escape(label)} ↗</a>'
                       for label, url in ABOUT["links"])
    return f"""<section class="ba-about">
      <figure><img src="{image_uri("raccoon.jpg")}" alt="The Book Analyzer raccoon in headphones at a keyboard">
      <figcaption>The raccoon, head of reading</figcaption></figure>
      <div><div class="ba-kicker">About · a passion project</div>
      <h2>Made for fun by {escape(ABOUT["name"])}</h2>{text}
      <p class="ba-links">{links}</p></div>
    </section>"""


def sidebar_title() -> str:
    return (f'<div class="ba-brand"><img src="{image_uri("raccoon-face.png")}" alt="">'
            f'<div><b>Book Analyzer</b><span>with a raccoon at the keyboard</span></div></div>')


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


def hero(analysis: BookAnalysis, title: str, events: list, theme: dict) -> str:
    """The book's title over a 'mood barcode': one stripe per chapter, coloured by its
    mood (blue brighter, red darker) and as tall as the chapter is emotional."""
    intensity = [1 - mix.get("neutral", 1) if mix else 0.5 for mix in analysis.chapter_emotions]
    top = max(intensity) or 1
    # colours relative to this book: its darkest and brightest chapters get the full red and blue
    reach = max(abs(t) for t in analysis.chapter_sentiment) or 1
    stripes = "".join(
        f'<i style="height:{20 + 80 * level / top:.0f}%;'
        f'background:{charts._tone_color(theme, tone / reach * charts.TONE_RANGE)}" '
        f'title="{escape(chapter.title)} · {escape(event.theme)} · mood {tone:+.2f}"></i>'
        for chapter, event, tone, level in zip(analysis.chapters, events, analysis.chapter_sentiment, intensity)
    )
    shares = charts.without_neutral(average_emotions([s.emotions for s in analysis.sentences]))
    author = f'<div class="ba-author">by {escape(analysis.author)}</div>' if analysis.author else ""
    return f"""<section class="ba-hero">
      <div class="ba-kicker">📖 Book Analyzer · the novel as pictures</div>
      <h1>{escape(title)}</h1>{author}
      <p class="ba-lede">Below, the whole book is turned into images: every stripe in this barcode is one of its
      {len(analysis.chapters)} chapters, <b style="color:var(--ba-bright)">blue</b> where the mood is bright,
      <b style="color:var(--ba-dark)">red</b> where it turns dark (compared with the rest of the book), taller where emotions run high.
      Hover a stripe to see the chapter, then scroll down to dive deeper.</p>
      <div class="ba-ribbon">{stripes}</div>
      <div class="ba-axis"><span>Beginning</span><span>Middle</span><span>End</span></div>
      {_emotion_legend(theme, shares) if shares else ""}
    </section>"""


def landing() -> str:
    """The page before any book is chosen."""
    return f"""<section class="ba-hero ba-split"><div>
      <div class="ba-kicker">📖 Book Analyzer</div>
      <h1>Turn a novel into pictures.</h1>
      <p class="ba-lede">Give it a book and AI models running on this computer read every sentence: who appears,
      who meets whom, where the story goes, and how the mood and emotions rise and fall. The words become a
      road through the story, a constellation, a crystal and a dozen charts you can dive into.</p>
      <p class="ba-lede"><b>Start in the sidebar:</b> upload an English novel as a <code>.txt</code> file, or pick
      a famous book (Dracula, Frankenstein, Alice in Wonderland…).</p></div>
      <figure class="ba-mascot"><img src="{image_uri("raccoon.jpg")}" alt="A raccoon in headphones at a keyboard">
      <figcaption>Your reader for today. Fast, careful, slightly snack-obsessed.</figcaption></figure>
    </section>"""


# --- KPI cards ------------------------------------------------------------------------------


def cast_strip(analysis: BookAnalysis, looks: dict, avatars: dict, theme: dict, n: int = 8) -> str:
    """The main characters as portrait cards: avatar, name, their look in words and
    what it is based on (the book's own words, or the story when it says nothing)."""
    from analyzer.emotions import stand_out
    from avatars import look_in_words
    colors = charts.character_colors(analysis, theme)
    book_fine = average_emotions([s.fine for s in analysis.sentences])
    cards = []
    for c in charts.top_characters(analysis, n):
        look = looks.get(c.id)
        if not look:
            continue
        feels = stand_out(analysis.character_fine[c.id], book_fine) if analysis.character_fine else []
        source = ("From the book: " + ", ".join(look.evidence)) if look.evidence else "Imagined from the story"
        cards.append(
            f'<article>{face(avatars, c, 88)}<b style="color:{colors[c.id]}">{escape(c.name)}</b>'
            f'<span class="look">{escape(look_in_words(look))}</span>'
            f'<span class="meta">{c.mentions:,} mentions{" · " + escape(", ".join(feels)) if feels else ""}</span>'
            f'<small>{escape(source)}</small></article>')
    return (f'<section class="ba-castgrid"><div class="ba-kicker">The cast</div>'
            f'<div class="grid">{"".join(cards)}</div>'
            f'<p class="note">Portraits are drawn by this website from what the book says about each character; '
            f'where it says nothing, the story fills in the blanks (title, job, the book\'s world and mood).</p>'
            f'</section>')


def kpis(analysis: BookAnalysis, events: list, theme: dict, avatars: dict | None = None) -> list[dict]:
    """The headline numbers of the book, each with a small picture.
    Each card: icon, label, value, note, art (HTML), and optional wide/tone."""
    names = {c.id: c for c in analysis.characters}
    colors = charts.character_colors(analysis, theme)
    ranked = charts.top_characters(analysis, len(analysis.characters))
    main = ranked[0]
    mood = analysis.chapter_sentiment
    book_tone = sum(mood) / len(mood)
    shares = charts.without_neutral(average_emotions([s.emotions for s in analysis.sentences]))
    words = sum(len(s.text.split()) for s in analysis.sentences)
    lines = find_lines(analysis.sentences, analysis.mentions)
    spoken = words_spoken(lines, len(analysis.characters))
    talker = max(analysis.characters, key=lambda c: spoken[c.id])
    said = sum(line.words for line in lines)
    negative, middle, positive = theme["diverging"]

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
        dict(icon="👑", label="Main character", value=escape(main.name), small=True,
             note=f"in {sum(1 for n in analysis.mentions_by_chapter[main.id] if n)} "
                  f"of {len(analysis.chapters)} chapters",
             art=_mini_bars(analysis.mentions_by_chapter[main.id], colors[main.id])),
        dict(icon="🌗", label="Overall mood", value=f"{book_tone:+.2f}",
             note="brighter than neutral" if book_tone > 0.02 else "darker than neutral" if book_tone < -0.02
             else "close to neutral",
             art=f'<div class="ba-gauge"><b style="left:{(max(-0.3, min(0.3, book_tone)) + 0.3) / 0.6:.1%}"></b></div>'),
    ]
    if shares:
        top = max(shares, key=shares.get)
        # the fine emotions that make up most of that family, e.g. "mostly disapproval, disgust"
        fine = average_emotions([s.fine for s in analysis.sentences])
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


def kpi_html(cards: list[dict]) -> str:
    out = []
    for c in cards:
        classes = "ba-kpi" + (" wide" if c.get("wide") else "") + (" toned" if c.get("tone") else "")
        style = f' style="--tone:{c["tone"]}"' if c.get("tone") else ""
        note = f'<div class="note">{escape(c["note"])}</div>' if c["note"] else ""
        out.append(f'<div class="{classes}"{style}><div class="label"><b>{c["icon"]}</b>{escape(c["label"])}</div>'
                   f'<div class="value{" small" if c.get("small") else ""}">{c["value"]}</div>{note}'
                   f'<div class="art">{c["art"]}</div></div>')
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
        dict(icon="⏱️", label="Reading time", value=when, art="",
             note=f"{pace.words:,} words at {230} a minute; " + _rank(hours, col["hours"], "longer", "shorter")),
        dict(icon="🎓", label="Reading level", value=f"Grade {max(pace.grade, 1):.0f}", art="",
             note=f"{grade_label(pace.grade)}; {pace.sentence_length:.0f} words per sentence; "
                  + _rank(pace.grade, col["grade"], "harder", "easier")),
        dict(icon="💬", label="Dialogue", value=f"{pace.dialogue:.0%}", art="",
             note="of the words are spoken; " + _rank(pace.dialogue, col["dialogue"], "chattier", "quieter")),
        dict(icon="🔤", label="Vocabulary", value=f"{pace.richness:.0%}", art="",
             note="different words in every 100; " + _rank(pace.richness, col["richness"], "richer", "plainer")),
    ]
