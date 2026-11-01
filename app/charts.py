"""Plotly charts for the analysis. Colors come from a palette checked for
colour-blind safety in both light and dark mode."""

import math

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from analyzer.models import BookAnalysis, Relationship

THEMES = {
    "light": {
        "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
        "grid": "#e1e0d9", "axis": "#c3c2b7",
        "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
        # sequential (one hue, light -> dark) for counts
        "sequential": ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"],
        # diverging for sentiment: red (negative) - gray - blue (positive)
        "diverging": ["#e34948", "#c3c2b7", "#2a78d6"],
        "emotions": {"love": "#e87ba4", "joy": "#eda100", "surprise": "#1baf7a", "shame": "#eb6834",
                     "sadness": "#2a78d6", "anger": "#e34948", "fear": "#6250d6", "disapproval": "#008300",
                     "neutral": "#898781"},
    },
    "dark": {
        "surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
        "grid": "#2c2c2a", "axis": "#383835",
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
        "sequential": ["#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#cde2fb"],
        "diverging": ["#e66767", "#52514e", "#3987e5"],
        "emotions": {"love": "#d55181", "joy": "#c98500", "surprise": "#199e70", "shame": "#d95926",
                     "sadness": "#3987e5", "anger": "#e66767", "fear": "#9085e9", "disapproval": "#008300",
                     "neutral": "#898781"},
    },
}
# The 8 emotion families (analyzer/emotions.py), warm ones first. Colours in
# this order passed the dataviz validator as stacked neighbours in light and
# dark mode (worst colour-blind difference 8.4, target >= 8): re-run it if you
# reorder them.
EMOTION_ORDER = ["love", "joy", "surprise", "shame", "sadness", "anger", "fear", "disapproval"]
WARM_EMOTIONS = {"love", "joy", "surprise"}
# legends use the part before " (" ; hovers and tables show the whole label
EMOTION_LABELS = {
    "love": "Love (caring, admiration, gratitude, trust)", "joy": "Joy (amusement, excitement, relief, pride)",
    "surprise": "Surprise (and curiosity)", "shame": "Shame (guilt, embarrassment)",
    "sadness": "Sadness (grief, despair, disappointment)", "anger": "Anger (annoyance, frustration)",
    "fear": "Fear (nervousness, doubt)", "disapproval": "Disapproval (disgust, envy, greed)", "neutral": "Neutral",
}


def short_label(emotion: str) -> str:
    return EMOTION_LABELS[emotion].split(" (")[0]
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'
TONE_RANGE = 0.3  # sentiment beyond +-0.3 gets the full colour (averages rarely go further)


def character_colors(analysis: BookAnalysis, theme: dict) -> dict[int, str]:
    """The 8 most mentioned characters get a fixed colour each, so a character
    has the same colour in every chart. Everyone else is gray."""
    ranked = sorted(analysis.characters, key=lambda c: -c.mentions)
    colors = {c.id: theme["muted"] for c in ranked}
    for c, color in zip(ranked, theme["series"]):
        colors[c.id] = color
    return colors


def name_tag(name: str, color: str) -> str:
    """A name with its character's colour dot in front, for axis labels."""
    return f"<span style='color:{color}'>●</span> {name}"


def top_characters(analysis: BookAnalysis, n: int):
    return sorted(analysis.characters, key=lambda c: -c.mentions)[:n]


def _layout(fig: go.Figure, theme: dict, height: int, **extra) -> go.Figure:
    axis = dict(gridcolor=theme["grid"], linecolor=theme["axis"], zeroline=False,
                tickfont=dict(color=theme["muted"]), title_font=dict(color=theme["ink2"]))
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor=theme["surface"], plot_bgcolor=theme["surface"],
        font=dict(family=FONT, color=theme["ink"], size=13),
        hoverlabel=dict(font_family=FONT),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=theme["ink2"])),
        **extra,
    )
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


def _smooth(values: list[float | None], window: int) -> list[float | None]:
    """Rolling average that skips missing chapters (None stays None)."""
    series = pd.Series(values, dtype="float64")
    smoothed = series.rolling(window, center=True, min_periods=1).mean()
    return [None if math.isnan(v) or math.isnan(s) else s for v, s in zip(series, smoothed)]


def _zero_line(fig: go.Figure, theme: dict) -> None:
    fig.add_hline(y=0, line=dict(color=theme["axis"], width=1))


def _tone_axis(fig: go.Figure, values: list[float | None]) -> None:
    present = [abs(v) for v in values if v is not None]
    limit = max([0.1] + present) * 1.15
    fig.update_yaxes(range=[-limit, limit], title="Tone (negative ↔ positive)", tickformat="+.2f")


# --- Mentions -------------------------------------------------------------

def mentions_bars(analysis: BookAnalysis, theme: dict, top: int = 15) -> go.Figure:
    characters = top_characters(analysis, top)[::-1]  # biggest at the top
    by_name = {c.id: 0 for c in characters}
    for m in analysis.mentions:
        if m.source == "name" and m.character_id in by_name:
            by_name[m.character_id] += 1
    colors = character_colors(analysis, theme)
    names = [c.name for c in characters]
    fig = go.Figure()
    for label, values, opacity in (
        ("By name (solid)", [by_name[c.id] for c in characters], 1.0),
        ("By pronoun or description (pale)", [c.mentions - by_name[c.id] for c in characters], 0.4),
    ):
        fig.add_bar(
            y=names, x=values, name=label, orientation="h",
            marker=dict(color=[colors[c.id] for c in characters], opacity=opacity,
                        line=dict(color=theme["surface"], width=2)),  # 2px gap between segments
            customdata=[label.split(" (")[0].lower()] * len(names),
            hovertemplate="%{y}: %{x:,} %{customdata}<extra></extra>",
        )
    fig.update_yaxes(tickvals=names, ticktext=[name_tag(c.name, colors[c.id]) for c in characters])
    fig.update_xaxes(title="Mentions")
    fig = _layout(fig, theme, height=60 + 28 * len(characters), barmode="stack", bargap=0.35)
    fig.update_layout(legend_traceorder="normal")  # "By name" first, like the bars
    return fig


# --- Sentiment over the story ----------------------------------------------

def _end_labels(fig: go.Figure, theme: dict, ends: list[tuple], y_range: tuple) -> None:
    """Name each line at its last point, nudging labels apart so they never overlap."""
    gap = (y_range[1] - y_range[0]) * 0.06  # about one line of text on a 440px chart
    placed: list[float] = []
    for x, y, label in sorted(ends, key=lambda e: e[1]):
        if placed and y < placed[-1] + gap:
            y = placed[-1] + gap
        placed.append(y)
        fig.add_annotation(x=x, y=y, text=label, showarrow=False, xanchor="left", xshift=6,
                           font=dict(color=theme["ink2"], size=12))

def story_sentiment(analysis: BookAnalysis, theme: dict, character_ids: list[int], smooth: int) -> go.Figure:
    chapters = list(range(1, len(analysis.chapters) + 1))
    titles = [c.title for c in analysis.chapters]
    colors = character_colors(analysis, theme)
    names = {c.id: c.name for c in analysis.characters}
    fig = go.Figure()
    lines = [("Whole book", analysis.chapter_sentiment, theme["ink2"], 2.5)]
    lines += [(names[i], analysis.sentiment_by_chapter[i], colors[i], 2) for i in character_ids]
    all_values, ends = [], []
    for label, values, color, width in lines:
        values = _smooth(values, smooth) if smooth > 1 else values
        all_values += values
        fig.add_scatter(
            x=chapters, y=values, name=label, mode="lines", line=dict(color=color, width=width),
            customdata=titles, hovertemplate=f"{label}: %{{y:+.2f}}<extra></extra>",
        )
        last = next(((x, y) for x, y in zip(chapters[::-1], values[::-1]) if y is not None), None)
        if last:
            ends.append((last[0], last[1], label))
    _zero_line(fig, theme)
    _tone_axis(fig, all_values)
    if len(lines) > 1:
        _end_labels(fig, theme, ends, fig.layout.yaxis.range)
    fig.update_xaxes(title="Chapter", range=[0.5, len(chapters) + (len(chapters) * 0.14 + 3 if len(lines) > 1 else 0.5)])
    return _layout(fig, theme, height=440, hovermode="x unified")


# --- Timeline --------------------------------------------------------------

def timeline_heatmap(analysis: BookAnalysis, theme: dict, top: int = 15) -> go.Figure:
    characters = top_characters(analysis, top)
    colors = character_colors(analysis, theme)
    fig = _heatmap(analysis, theme, [c.name for c in characters],
                   [analysis.mentions_by_chapter[c.id] for c in characters])
    fig.update_yaxes(tickvals=[c.name for c in characters],
                     ticktext=[name_tag(c.name, colors[c.id]) for c in characters])
    return fig


def places_heatmap(analysis: BookAnalysis, theme: dict, top: int = 15) -> go.Figure:
    places = [e for e in analysis.entities if e.kind == "place"][:top]
    return _heatmap(analysis, theme, [p.name for p in places], [p.chapter_counts for p in places])


def _heatmap(analysis: BookAnalysis, theme: dict, names: list[str], z: list[list[int]]) -> go.Figure:
    """Rows of names x chapters, darker = mentioned more in that chapter."""
    steps = theme["sequential"]
    # 0 mentions shows as the background; then light -> dark as mentions grow
    start = 0.001
    scale = [[0, theme["surface"]]] + [
        [start + (1 - start) * i / (len(steps) - 1), step] for i, step in enumerate(steps)
    ]
    fig = go.Figure(go.Heatmap(
        z=z, x=list(range(1, len(analysis.chapters) + 1)), y=names,
        colorscale=scale, zmin=0, xgap=2, ygap=2,
        customdata=[[t.title for t in analysis.chapters]] * len(names),
        hovertemplate="%{y}, %{customdata}: %{z} mentions<extra></extra>",
        colorbar=dict(title=dict(text="Mentions", font=dict(color=theme["ink2"])),
                      tickfont=dict(color=theme["muted"]), outlinewidth=0, thickness=12),
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(title="Chapter", showgrid=False)
    return _layout(fig, theme, height=80 + 26 * len(names))


def entity_bars(entities: list, theme: dict) -> go.Figure:
    """Most mentioned entities of one kind, biggest at the top."""
    entities = entities[::-1]
    fig = go.Figure(go.Bar(
        y=[e.name for e in entities], x=[e.count for e in entities], orientation="h",
        marker=dict(color=theme["ink2"], line=dict(color=theme["surface"], width=2)),
        hovertemplate="%{y}: %{x} mentions<extra></extra>",
    ))
    fig.update_xaxes(title="Mentions")
    return _layout(fig, theme, height=70 + 26 * len(entities), showlegend=False, bargap=0.35)


# --- Mood sentence by sentence -------------------------------------------------

def mood_arc(analysis: BookAnalysis, theme: dict, rolled: list[float], moments: tuple) -> go.Figure:
    """The rolling mood along the whole book: blue above zero, red below.
    `moments` = (dark, bright) key moments, marked on the line."""
    x = list(range(1, len(rolled) + 1))
    sentences = analysis.sentences
    hover = [f"{analysis.chapters[s.chapter].title}<br>{s.text[:90]}{'…' if len(s.text) > 90 else ''}"
             for s in sentences]
    negative, _, positive = theme["diverging"]
    fig = go.Figure()
    # two filled halves: above zero in blue, below zero in red
    for part, color in (([max(v, 0) for v in rolled], positive), ([min(v, 0) for v in rolled], negative)):
        fig.add_scatter(x=x, y=part, mode="lines", line=dict(color=color, width=1.5), fill="tozeroy",
                        fillcolor=color, opacity=0.55, hoverinfo="skip", showlegend=False)
    # an invisible line on top carries the hover text
    fig.add_scatter(x=x, y=rolled, mode="lines", line=dict(width=0, color="rgba(0,0,0,0)"), showlegend=False,
                    customdata=hover, hovertemplate="mood %{y:+.2f}<br>%{customdata}<extra></extra>")
    for moments_of_kind, symbol, label in ((moments[0], "triangle-down", "darkest"),
                                           (moments[1], "triangle-up", "brightest")):
        if moments_of_kind:
            middles = [(m.first + m.last) // 2 for m in moments_of_kind]
            fig.add_scatter(
                x=[i + 1 for i in middles], y=[rolled[i] for i in middles], mode="markers+text",
                text=[str(n) for n in range(1, len(middles) + 1)], textposition="bottom center"
                if symbol == "triangle-down" else "top center", textfont=dict(color=theme["ink2"]),
                marker=dict(symbol=symbol, size=12, color=theme["ink"], line=dict(color=theme["surface"], width=2)),
                name=f"{label} passages", hoverinfo="skip",
            )
    _zero_line(fig, theme)
    _tone_axis(fig, rolled)
    # chapter numbers along the bottom (about a dozen, so they stay readable)
    starts = [next((s.index + 1 for s in sentences if s.chapter == c.index), None) for c in analysis.chapters]
    step = max(1, len(starts) // 12)
    ticks = [(pos, c + 1) for c, pos in enumerate(starts) if pos is not None and c % step == 0]
    fig.update_xaxes(title="Chapter", tickvals=[t[0] for t in ticks], ticktext=[t[1] for t in ticks],
                     range=[1, len(x)])
    return _layout(fig, theme, height=380, hovermode="x")


# --- Story timeline --------------------------------------------------------------------

def chapter_details(analysis: BookAnalysis) -> list[dict]:
    """Per chapter: its two most mentioned characters and its most mentioned place."""
    places = [e for e in analysis.entities if e.kind == "place" and e.chapter_counts]
    details = []
    for ch in range(len(analysis.chapters)):
        present = [c for c in analysis.characters if analysis.mentions_by_chapter[c.id][ch]]
        people = sorted(present, key=lambda c: -analysis.mentions_by_chapter[c.id][ch])[:2]
        place = max(places, key=lambda e: e.chapter_counts[ch], default=None)
        details.append({"people": [c.name for c in people],
                        "place": place.name if place and place.chapter_counts[ch] else None})
    return details


def _chapter_hover(analysis: BookAnalysis, events: list, details: list[dict]) -> list[str]:
    hover = []
    for ch, (event, detail) in enumerate(zip(events, details)):
        where = f" · at {detail['place']}" if detail["place"] else ""
        hover.append(f"<b>{analysis.chapters[ch].title} · {event.theme}</b><br>{event.event}<br>"
                     f"{', '.join(detail['people'])}{where}<br>keywords: {', '.join(event.keywords)}")
    return hover


def story_timeline(analysis: BookAnalysis, theme: dict, events: list, labels: int) -> go.Figure:
    """Top: each chapter's mood with the clearest themes pinned above.
    Bottom: how the mix of emotions shifts. One shared chapter axis, two
    separate y-axes stacked (never two scales on one plot)."""
    from plotly.subplots import make_subplots

    chapters = list(range(1, len(analysis.chapters) + 1))
    hover = _chapter_hover(analysis, events, chapter_details(analysis))
    negative, middle, positive = theme["diverging"]
    colors = [positive if t >= 0.04 else negative if t <= -0.04 else middle for t in analysis.chapter_sentiment]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.62, 0.38], vertical_spacing=0.06)
    # the legend is for the emotions only; the mood axis title explains the bars
    fig.add_bar(x=chapters, y=analysis.chapter_sentiment, marker=dict(color=colors, line=dict(color=theme["surface"], width=1)),
                customdata=hover, hovertemplate="%{customdata}<br>mood %{y:+.2f}<extra></extra>", showlegend=False,
                row=1, col=1)
    fig.add_scatter(x=chapters, y=_smooth(analysis.chapter_sentiment, 5), mode="lines", hoverinfo="skip",
                    line=dict(color=theme["ink"], width=2), showlegend=False, row=1, col=1)
    if any(analysis.chapter_emotions):
        shares = [without_neutral(mix) for mix in analysis.chapter_emotions]
        for e in EMOTION_ORDER:
            fig.add_scatter(x=chapters, y=_smooth([s.get(e) if s else None for s in shares], 3), mode="lines",
                            stackgroup="mix", groupnorm="percent", name=short_label(e),
                            line=dict(width=1, color=theme["surface"]), fillcolor=theme["emotions"][e],
                            hovertemplate=f"{EMOTION_LABELS[e]} %{{y:.0f}}%<extra></extra>", row=2, col=1)
    # pin the clearest themes above their bars, alternating heights so labels don't collide
    clearest = sorted(sorted(range(len(events)), key=lambda c: -events[c].strength)[:labels])
    for k, ch in enumerate(clearest):
        tone = analysis.chapter_sentiment[ch]
        fig.add_annotation(x=ch + 1, y=tone, text=f"<b>{events[ch].theme}</b>", showarrow=True, arrowhead=0,
                           arrowcolor=theme["muted"], ax=0, ay=(-1 if tone >= 0 else 1) * (28 + (k % 3) * 22),
                           font=dict(size=12, color=theme["ink"]), bgcolor=theme["surface"],
                           bordercolor=theme["axis"], borderpad=3, row=1, col=1)
    fig.add_hline(y=0, line=dict(color=theme["axis"], width=1), row=1, col=1)
    limit = max(0.15, *(abs(t) for t in analysis.chapter_sentiment)) * 1.6
    fig.update_yaxes(title="Mood", tickformat="+.2f", range=[-limit, limit], row=1, col=1)
    fig.update_yaxes(title="Emotions", ticksuffix="%", range=[0, 100], row=2, col=1)
    fig.update_xaxes(title="Chapter", range=[0.4, len(chapters) + 0.6], row=2, col=1)
    fig = _layout(fig, theme, height=600, hovermode="x unified", showlegend=True)
    fig.update_layout(legend_traceorder="normal")
    return fig


def story_arc_chart(analysis: BookAnalysis, theme: dict, events: list,
                    arc: list[float], turning: list[tuple[int, str]], acts: list[tuple[int, int]]) -> go.Figure:
    """The smoothed mood of the book with its turning points and acts."""
    chapters = list(range(1, len(arc) + 1))
    hover = _chapter_hover(analysis, events, chapter_details(analysis))
    negative, _, positive = theme["diverging"]
    fig = go.Figure()
    for part, color in (([max(v, 0) for v in arc], positive), ([min(v, 0) for v in arc], negative)):
        fig.add_scatter(x=chapters, y=part, mode="lines", fill="tozeroy", line=dict(width=0, color=color),
                        fillcolor=color, opacity=0.35, hoverinfo="skip", showlegend=False)
    fig.add_scatter(x=chapters, y=arc, mode="lines", line=dict(color=theme["ink"], width=2.5, shape="spline"),
                    customdata=hover, hovertemplate="%{customdata}<br>smoothed mood %{y:+.2f}<extra></extra>",
                    showlegend=False)
    fig.add_scatter(x=[i + 1 for i, _ in turning], y=[arc[i] for i, _ in turning], mode="markers+text",
                    text=[events[i].theme for i, _ in turning], showlegend=False, hoverinfo="skip",
                    textposition=["top center" if kind == "high" else "bottom center" for _, kind in turning],
                    textfont=dict(color=theme["ink"], size=12),
                    marker=dict(size=11, color=theme["ink"], line=dict(color=theme["surface"], width=2)))
    for k, (first, last) in enumerate(acts):
        if k % 2:
            fig.add_vrect(x0=first + 0.5, x1=last + 1.5, fillcolor=theme["grid"], opacity=0.5, line_width=0, layer="below")
        fig.add_annotation(x=(first + last) / 2 + 1, y=1, yref="paper", yanchor="top", showarrow=False,
                           text=f"Act {k + 1}", font=dict(size=12, color=theme["muted"]))
    fig.add_hline(y=0, line=dict(color=theme["axis"], width=1))
    _tone_axis(fig, arc)
    fig.update_yaxes(title="Mood (smoothed)")
    fig.update_xaxes(title="Chapter", range=[0.5, len(arc) + 0.5])
    return _layout(fig, theme, height=420, hovermode="closest")


# --- Emotions ---------------------------------------------------------------------

def without_neutral(mix: dict[str, float]) -> dict[str, float]:
    """Share of each emotion among the non-neutral ones (adds up to 1)."""
    total = sum(mix.get(e, 0) for e in EMOTION_ORDER)
    return {e: mix.get(e, 0) / total for e in EMOTION_ORDER} if total else {}


def emotion_bars(theme: dict, mix: dict[str, float], compare: dict[str, float] | None = None,
                 name: str = "", compare_name: str = "Whole book") -> go.Figure:
    """The emotion mix (neutral left out), biggest first. With `compare`,
    a gray bar next to each one shows the book average for reference."""
    shares = without_neutral(mix)
    order = sorted(shares, key=shares.get)  # biggest at the top
    labels = [short_label(e) for e in order]  # the full label (with its fine emotions) is in the hover
    full = [EMOTION_LABELS[e] for e in order]
    fig = go.Figure()
    if compare:
        reference = without_neutral(compare)
        fig.add_bar(y=labels, x=[reference.get(e, 0) for e in order], name=compare_name, orientation="h",
                    marker=dict(color=theme["axis"], line=dict(color=theme["surface"], width=2)), customdata=full,
                    hovertemplate=f"{compare_name}: %{{customdata}} %{{x:.0%}}<extra></extra>")
    fig.add_bar(y=labels, x=[shares[e] for e in order], name=name or "Share", orientation="h", customdata=full,
                marker=dict(color=[theme["emotions"][e] for e in order], line=dict(color=theme["surface"], width=2)),
                hovertemplate=f"{name + ': ' if name else ''}%{{customdata}} %{{x:.0%}}<extra></extra>")
    fig.update_xaxes(title="Share of the emotional content", tickformat=".0%")
    # No legend: the coloured bars have one colour per emotion, so a legend
    # swatch for them would be misleading; the page caption says gray = book
    return _layout(fig, theme, height=90 + 34 * len(order) * (2 if compare else 1),
                   barmode="group", bargap=0.3, showlegend=False)


def fine_bars(theme: dict, fine: dict[str, float], top: int = 15) -> go.Figure:
    """The most common fine emotions (e.g. curiosity, grief, guilt), each bar in
    its family's colour. Values are average scores per sentence."""
    from analyzer.emotions import FAMILY_OF  # calm feelings have no family: gray
    ranked = sorted(fine, key=fine.get, reverse=True)[:top][::-1]  # biggest at the top
    families = [FAMILY_OF.get(e) for e in ranked]
    fig = go.Figure(go.Bar(
        y=ranked, x=[fine[e] for e in ranked], orientation="h",
        marker=dict(color=[theme["emotions"][f] if f else theme["muted"] for f in families],
                    line=dict(color=theme["surface"], width=2)),
        customdata=[short_label(f) if f else "Calm (no family)" for f in families],
        hovertemplate="%{y} (%{customdata}): %{x:.3f}<extra></extra>",
    ))
    fig.update_xaxes(title="Average strength per sentence")
    return _layout(fig, theme, height=70 + 26 * len(ranked), showlegend=False, bargap=0.3)


def emotion_journey(analysis: BookAnalysis, theme: dict, smooth: int) -> go.Figure:
    """How the mix of (non-neutral) emotions changes chapter by chapter."""
    chapters = list(range(1, len(analysis.chapters) + 1))
    shares = [without_neutral(mix) for mix in analysis.chapter_emotions]
    titles = [c.title for c in analysis.chapters]
    fig = go.Figure()
    for e in EMOTION_ORDER:
        values = [s.get(e) if s else None for s in shares]
        values = _smooth(values, smooth) if smooth > 1 else values
        fig.add_scatter(
            x=chapters, y=values, name=short_label(e), mode="lines", stackgroup="mix", groupnorm="percent",
            line=dict(width=2, color=theme["surface"]),  # 2px gap between the coloured bands
            fillcolor=theme["emotions"][e], customdata=titles,
            hovertemplate=f"{EMOTION_LABELS[e]}: %{{y:.0f}}%<extra></extra>",
        )
    fig.update_xaxes(title="Chapter", range=[1, len(chapters)])
    fig.update_yaxes(title="Share of the emotional content", ticksuffix="%", range=[0, 100])
    fig = _layout(fig, theme, height=440, hovermode="x unified")
    fig.update_layout(legend_traceorder="normal")  # Love ... Disapproval, like the other emotion charts
    return fig


def pair_emotions(theme: dict, r: Relationship) -> go.Figure:
    """A pair's emotion mix in the early, middle and late book."""
    parts = ["Early", "Middle", "Late"]
    shares = [without_neutral(mix) for mix in r.emotions_by_part]
    fig = go.Figure()
    for e in EMOTION_ORDER:
        fig.add_bar(y=parts, x=[s.get(e, 0) if s else 0 for s in shares], name=short_label(e),
                    orientation="h", marker=dict(color=theme["emotions"][e],
                                                 line=dict(color=theme["surface"], width=2)),
                    hovertemplate=f"%{{y}}: {EMOTION_LABELS[e]} %{{x:.0%}}<extra></extra>")
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Share of the emotional content of their shared moments", tickformat=".0%",
                     range=[0, 1])
    fig = _layout(fig, theme, height=260, barmode="stack", bargap=0.35)
    fig.update_layout(legend_traceorder="normal")  # legend in the same order as the bar segments
    return fig


# --- Relationships ---------------------------------------------------------

def _tone_color(theme: dict, tone: float) -> str:
    position = (max(-TONE_RANGE, min(TONE_RANGE, tone)) + TONE_RANGE) / (2 * TONE_RANGE)
    return sample_colorscale(theme["diverging"], [position])[0]


def _network_layout(characters: dict, links: list[Relationship]) -> dict:
    """Positions where characters who share more moments sit closer together.
    Uses every link (not only the visible ones) so dots don't move when the
    filter slider changes. The log keeps a pair with 478 moments from being
    pulled on top of each other: it is only a few times "closer" than one with 10."""
    graph = nx.Graph()
    graph.add_nodes_from(characters)
    for r in links:
        graph.add_edge(r.source, r.target, distance=1 / (1 + math.log(r.count)))
    if graph.number_of_edges() == 0:
        return nx.circular_layout(graph)
    # characters with no links at all are placed by the layout as far away as allowed
    return nx.kamada_kawai_layout(graph, weight="distance")


def relationship_network(analysis: BookAnalysis, theme: dict, top: int, min_count: int) -> go.Figure:
    characters = {c.id: c for c in top_characters(analysis, top)}
    all_links = [r for r in analysis.relationships if r.source in characters and r.target in characters]
    links = [r for r in all_links if r.count >= min_count]
    pos = _network_layout(characters, all_links)

    fig = go.Figure()
    biggest = max([r.count for r in links] + [1])
    names = {i: c.name for i, c in characters.items()}
    for r in sorted(links, key=lambda r: r.count):
        (x0, y0), (x1, y1) = pos[r.source], pos[r.target]
        fig.add_scatter(x=[x0, x1], y=[y0, y1], mode="lines", hoverinfo="skip", showlegend=False,
                        line=dict(color=_tone_color(theme, r.sentiment), width=1 + 9 * r.count / biggest))
    # invisible points in the middle of each line carry the hover text
    fig.add_scatter(
        x=[(pos[r.source][0] + pos[r.target][0]) / 2 for r in links],
        y=[(pos[r.source][1] + pos[r.target][1]) / 2 for r in links],
        mode="markers", marker=dict(size=18, color="rgba(0,0,0,0)"), showlegend=False,
        hovertext=[f"{names[r.source]} & {names[r.target]}<br>{r.count} moments together"
                   f"<br>average tone {r.sentiment:+.2f}" for r in links],
        hoverinfo="text",
    )
    colors = character_colors(analysis, theme)
    biggest_node = max(c.mentions for c in characters.values())
    fig.add_scatter(
        x=[pos[i][0] for i in characters], y=[pos[i][1] for i in characters],
        mode="markers+text", text=[c.name for c in characters.values()], textposition="top center",
        textfont=dict(color=theme["ink2"], size=12), showlegend=False,
        marker=dict(size=[10 + 30 * math.sqrt(c.mentions / biggest_node) for c in characters.values()],
                    color=[colors[i] for i in characters],
                    line=dict(color=theme["surface"], width=2)),  # 2px ring where marks overlap
        hovertext=[f"{c.name}<br>{c.mentions:,} mentions" for c in characters.values()], hoverinfo="text",
    )
    # colour legend for the lines
    fig.add_scatter(
        x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
        marker=dict(colorscale=theme["diverging"], cmin=-TONE_RANGE, cmax=TONE_RANGE, color=[0],
                    colorbar=dict(title=dict(text="Tone", font=dict(color=theme["ink2"])), thickness=12,
                                  tickvals=[-TONE_RANGE, 0, TONE_RANGE],
                                  ticktext=["negative", "neutral", "positive"],
                                  tickfont=dict(color=theme["muted"]), outlinewidth=0)),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x")
    return _layout(fig, theme, height=620)


def pair_tone(analysis: BookAnalysis, theme: dict, r: Relationship, smooth: int) -> go.Figure:
    chapters = list(range(1, len(analysis.chapters) + 1))
    values = _smooth(r.chapter_sentiment, smooth) if smooth > 1 else r.chapter_sentiment
    fig = go.Figure(go.Scatter(
        x=chapters, y=values, mode="lines+markers",  # the line breaks where they never meet
        line=dict(color=theme["axis"], width=2),
        marker=dict(size=9, color=[theme["surface"] if v is None else _tone_color(theme, v) for v in values],
                    line=dict(color=theme["surface"], width=1.5)),  # each dot coloured by its tone
        customdata=[c.title for c in analysis.chapters],
        hovertemplate="%{customdata}: tone %{y:+.2f}<extra></extra>",
    ))
    _zero_line(fig, theme)
    _tone_axis(fig, values)
    fig.update_xaxes(title="Chapter", range=[0.5, len(chapters) + 0.5])
    return _layout(fig, theme, height=320, showlegend=False)


def pair_moments(analysis: BookAnalysis, theme: dict, r: Relationship) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=list(range(1, len(analysis.chapters) + 1)), y=r.chapter_counts,
        marker=dict(color=theme["ink2"], line=dict(color=theme["surface"], width=2)),
        customdata=[c.title for c in analysis.chapters],
        hovertemplate="%{customdata}: %{y} moments together<extra></extra>",
    ))
    fig.update_xaxes(title="Chapter", range=[0.5, len(analysis.chapters) + 0.5])
    fig.update_yaxes(title="Moments together")
    return _layout(fig, theme, height=220, showlegend=False, bargap=0.1)
