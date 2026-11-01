"""The look of the website: page styling, the hero banner and the KPI cards.

Everything here returns HTML/CSS strings that the app shows with `st.html`.
Colours come from `charts.THEMES`, so light and dark mode both work.
"""

from html import escape

import charts
from analyzer.emotions import average_emotions
from analyzer.models import BookAnalysis

SERIF = '"Fraunces", Georgia, "Times New Roman", serif'
ACCENT = {"light": "#b7791f", "dark": "#e0b25b"}  # old-gold, used only for small decorations


def page_css(theme: dict, mode: str) -> str:
    """Styling for the whole page: section headings, visualization cards, KPI cards."""
    t, gold = theme, ACCENT[mode]
    glow = "0 1px 2px rgba(0,0,0,.05), 0 8px 24px rgba(0,0,0,.06)" if mode == "light" \
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
    [data-testid="stSidebar"] a {{ color: inherit; text-decoration-color: var(--ba-muted); }}

    @media (max-width: 900px) {{ .ba-kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 560px) {{
        .ba-kpis {{ grid-template-columns: 1fr; }} .ba-kpi.wide {{ grid-column: auto; }}
        .ba-hero {{ padding: 1.4rem 1.1rem 1.1rem; }} }}
    </style>"""


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


def _faces(characters: list, colors: dict) -> str:
    """Round badges with initials, each in the character's own colour."""
    return '<div class="ba-faces">' + "".join(
        f'<span style="background:{colors[c.id]}" title="{escape(c.name)}">{escape(_initials(c.name))}</span>'
        for c in characters) + "</div>"


def cast_legend(analysis: BookAnalysis, theme: dict) -> str:
    """The colour of each main character, used in every chart on the page."""
    colors = charts.character_colors(analysis, theme)
    rows = "".join(f'<li><i style="background:{colors[c.id]}"></i>{escape(c.name)}</li>'
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
    return """<section class="ba-hero">
      <div class="ba-kicker">📖 Book Analyzer</div>
      <h1>Turn a novel into pictures.</h1>
      <p class="ba-lede">Give it a book and AI models running on this computer read every sentence: who appears,
      who meets whom, where the story goes, and how the mood and emotions rise and fall. The words become a
      road through the story, a constellation, a crystal and a dozen charts you can dive into.</p>
      <p class="ba-lede"><b>Start in the sidebar:</b> upload an English novel as a <code>.txt</code> file, or try
      the sample book.</p>
    </section>"""


# --- KPI cards ------------------------------------------------------------------------------


def kpis(analysis: BookAnalysis, events: list, theme: dict) -> list[dict]:
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
    by_name = sum(m.source == "name" for m in analysis.mentions)
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
             art=_faces(ranked[:8], colors)),
        dict(icon="💬", label="Mentions", value=f"{len(analysis.mentions):,}",
             note=f"{by_name / max(len(analysis.mentions), 1):.0%} by name, the rest by pronoun",
             art=_stack([(by_name, theme["ink2"], "by name"),
                         (len(analysis.mentions) - by_name, theme["axis"], "by pronoun or description")])),
        dict(icon="👑", label="Main character", value=escape(main.name), small=True,
             note=f"{main.mentions:,} mentions · in {sum(1 for n in analysis.mentions_by_chapter[main.id] if n)} "
                  f"of {len(analysis.chapters)} chapters",
             art=_mini_bars(analysis.mentions_by_chapter[main.id], colors[main.id])),
        dict(icon="🌗", label="Overall mood", value=f"{book_tone:+.2f}",
             note="brighter than neutral" if book_tone > 0.02 else "darker than neutral" if book_tone < -0.02
             else "close to neutral",
             art=f'<div class="ba-gauge"><b style="left:{(max(-0.3, min(0.3, book_tone)) + 0.3) / 0.6:.1%}"></b></div>'),
    ]
    if shares:
        top = max(shares, key=shares.get)
        cards.append(dict(icon="🎭", label="Strongest emotion", value=charts.EMOTION_LABELS[top].split(" (")[0],
                          note=f"{shares[top]:.0%} of the emotional sentences",
                          art=_stack([(shares[e], theme["emotions"][e], f"{charts.EMOTION_LABELS[e]} {shares[e]:.0%}")
                                      for e in charts.EMOTION_ORDER])))
    else:
        cards.append(dict(icon="🎭", label="Strongest emotion", value="—", note="emotions were not detected", art=""))
    if analysis.relationships:
        pair = analysis.relationships[0]
        a, b = names[pair.source], names[pair.target]
        cards.append(dict(icon="💞", label="Closest pair", value=f"{escape(a.name)} &amp; {escape(b.name)}", small=True,
                          note=f"{pair.count} moments together · tone {pair.sentiment:+.2f}",
                          art=_faces([a, b], colors)))
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
