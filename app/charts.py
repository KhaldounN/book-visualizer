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
        "surface": "#ffffff", "ink": "#1b1a17", "ink2": "#4d4a43", "muted": "#807a6e",
        "grid": "#ece8df", "axis": "#d3ccbf",
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
        "surface": "#1a1a19", "ink": "#ece8df", "ink2": "#c3c2b7", "muted": "#898781",
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
FONT = 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif'  # the page's own text font
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
    axis = dict(gridcolor=theme["grid"], linecolor=theme["axis"], zeroline=False, ticks="", gridwidth=1,
                tickfont=dict(color=theme["muted"], size=12), title_font=dict(color=theme["ink2"], size=12),
                title_standoff=10)
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor=theme["surface"], plot_bgcolor=theme["surface"],
        font=dict(family=FONT, color=theme["ink"], size=13),
        # tooltips as small cards in the page's own colours, not Plotly's coloured boxes
        hoverlabel=dict(bgcolor=theme["surface"], bordercolor=theme["axis"], align="left",
                        font=dict(family=FONT, color=theme["ink"], size=13)),
        barcornerradius=3,  # softly rounded bar ends
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=theme["ink2"])),
        # a drag scrolls the page instead of zooming the chart (on a phone, a finger drag must scroll);
        # hovering and tapping still show the details
        dragmode=False,
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

def mentions_bars(analysis: BookAnalysis, theme: dict, top: int = 15, avatars: dict | None = None) -> go.Figure:
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
    if avatars:  # each character's avatar at the end of their bar
        longest = max(c.mentions for c in characters) or 1
        for c in characters:
            if c.id in avatars:
                fig.add_layout_image(source=avatars[c.id], xref="x", yref="y", x=c.mentions + longest * 0.012,
                                     y=c.name, sizex=longest * 0.2, sizey=0.95, xanchor="left", yanchor="middle",
                                     sizing="contain", layer="above")
        fig.update_xaxes(range=[0, longest * 1.18])  # room for the avatar after the longest bar
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
    # the story's acts (a new one starts at each low turning point, progression.story_arc) as faint bands
    from analyzer.progression import story_arc
    if len(analysis.chapter_sentiment) >= 8:
        _, _, acts = story_arc(analysis.chapter_sentiment)
        numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
        for k, (first, last) in enumerate(acts[:len(numerals)]):
            if k % 2 == 0:
                fig.add_vrect(x0=first + 0.5, x1=last + 1.5, fillcolor=theme["grid"], opacity=0.55, line_width=0,
                              layer="below")
            fig.add_annotation(x=(first + last) / 2 + 1, y=0.99, yref="paper", yanchor="top", showarrow=False,
                               text=f"Act {numerals[k]}", font=dict(color=theme["muted"], size=11))
    # the book's darkest and brightest chapters, labelled on its line
    raw = analysis.chapter_sentiment
    whole = _smooth(raw, smooth) if smooth > 1 else raw
    if len(raw) >= 3:
        for index, label, shift in ((min(range(len(raw)), key=raw.__getitem__), "darkest", 1),
                                    (max(range(len(raw)), key=raw.__getitem__), "brightest", -1)):
            if whole[index] is not None:
                fig.add_annotation(x=index + 1, y=whole[index], text=f"{label}: {titles[index].split(':')[0]}",
                                   showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=theme["muted"],
                                   ax=0, ay=34 * shift, font=dict(color=theme["ink2"], size=11),
                                   bgcolor=theme["surface"])
    fig.update_traces(line_shape="spline", line_smoothing=0.6, selector=dict(type="scatter"))
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
    fig.update_traces(line_shape="spline", line_smoothing=0.6, selector=dict(type="scatter"))  # smooth trend
    return fig


def stage_label(analysis: BookAnalysis, stage: dict) -> str:
    """'Ch. 3–7' (or 'Ch. 5' when the stage sits inside one chapter)."""
    first, last = stage["first_chapter"] + 1, stage["last_chapter"] + 1
    return f"Ch. {first}" if first == last else f"Ch. {first}–{last}"


def character_journey(analysis: BookAnalysis, theme: dict, journey: list[dict], name: str, color: str,
                      turns: dict | None) -> go.Figure:
    """One character through the book, stage by stage: their mood next to the
    whole book's (top) and their emotion mix (bottom, 100% stacked bars).
    Stages with too few sentences about them are left empty, not guessed."""
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.55, 0.45],
                        subplot_titles=["Mood", "Emotions"])
    x = list(range(1, len(journey) + 1))
    labels = [stage_label(analysis, s) for s in journey]
    counts = [s["count"] for s in journey]
    fig.add_scatter(x=x, y=[s["book_mood"] for s in journey], name="Whole book", mode="lines",
                    line=dict(color=theme["axis"], width=2, dash="dot"), customdata=labels,
                    hovertemplate="Whole book: %{y:+.2f}<extra></extra>", row=1, col=1)
    moods = [s["mood"] for s in journey]
    fig.add_scatter(x=x, y=moods, name=name, mode="lines+markers", connectgaps=False,  # absent: a gap
                    line=dict(color=color, width=3), marker=dict(size=7, color=color),
                    customdata=list(zip(labels, counts)),
                    hovertemplate=f"{name}: %{{y:+.2f}} (%{{customdata[1]}} sentences)<extra></extra>", row=1, col=1)
    if turns:
        for key, symbol, shift in (("low", "triangle-down", -14), ("high", "triangle-up", 14)):
            i = turns[key]
            fig.add_scatter(x=[i + 1], y=[moods[i]], mode="markers", showlegend=False, hoverinfo="skip",
                            marker=dict(symbol=symbol, size=14, color=theme["ink"],
                                        line=dict(color=theme["surface"], width=2)), row=1, col=1)
    fig.add_hline(y=0, line=dict(color=theme["axis"], width=1), row=1, col=1)
    present = [abs(v) for v in moods + [s["book_mood"] for s in journey] if v is not None]
    limit = max([0.1] + present) * 1.2
    fig.update_yaxes(range=[-limit, limit], tickformat="+.2f", title="Tone", row=1, col=1)

    shares = [without_neutral(s["emotions"]) for s in journey]
    for e in EMOTION_ORDER:
        fig.add_bar(x=x, y=[sh.get(e, 0) if sh else None for sh in shares], name=short_label(e),
                    marker=dict(color=theme["emotions"][e], line=dict(color=theme["surface"], width=1)),
                    customdata=labels, legendgroup="emotions",
                    hovertemplate=f"{EMOTION_LABELS[e]} %{{y:.0%}}<extra></extra>", row=2, col=1)
    fig.update_yaxes(tickformat=".0%", range=[0, 1], title="Share", row=2, col=1)
    fig.update_xaxes(tickvals=x, ticktext=labels, row=2, col=1)
    fig.update_xaxes(title="How far through the book", row=2, col=1)
    fig.update_annotations(font=dict(size=12, color=theme["ink2"]), x=0, xanchor="left")
    fig = _layout(fig, theme, height=600, barmode="stack", bargap=0.25, hovermode="x unified")
    fig.update_layout(legend_traceorder="normal", margin=dict(l=10, r=10, t=60, b=10))
    fig.update_traces(line_shape="spline", line_smoothing=0.6, selector=dict(type="scatter"))  # smooth trend
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
        # never closer than 0.45: the main characters share moments with everyone and would knot together
        graph.add_edge(r.source, r.target, distance=0.45 + 0.55 / (1 + math.log(r.count)))
    if graph.number_of_edges() == 0:
        return nx.circular_layout(graph)
    # characters with no links at all are placed by the layout as far away as allowed
    return nx.kamada_kawai_layout(graph, weight="distance")


def _spread(pos: dict, radius: dict, rounds: int = 80) -> dict:
    """Push apart any two characters whose portraits would overlap (radius = half a portrait), a
    little at a time, so the layout keeps its shape but every face can be seen."""
    pos = {i: [float(p[0]), float(p[1])] for i, p in pos.items()}
    ids = list(pos)
    for _ in range(rounds):
        moved = False
        for a_index, a in enumerate(ids):
            for b in ids[a_index + 1:]:
                dx, dy = pos[b][0] - pos[a][0], pos[b][1] - pos[a][1]
                dist = math.hypot(dx, dy) or 1e-6
                need = radius[a] + radius[b]
                if dist < need:
                    push = (need - dist) / 2 / dist
                    pos[a][0] -= dx * push; pos[a][1] -= dy * push
                    pos[b][0] += dx * push; pos[b][1] += dy * push
                    moved = True
        if not moved:
            break
    return pos


def relationship_network(analysis: BookAnalysis, theme: dict, top: int, min_count: int,
                         avatars: dict | None = None) -> go.Figure:
    characters = {c.id: c for c in top_characters(analysis, top)}
    all_links = [r for r in analysis.relationships if r.source in characters and r.target in characters]
    links = [r for r in all_links if r.count >= min_count]
    pos = _network_layout(characters, all_links)
    biggest_node = max(c.mentions for c in characters.values())
    xs = [p[0] for p in pos.values()]
    span = (max(xs) - min(xs)) or 1
    portrait = {i: span * (0.05 + 0.08 * math.sqrt(c.mentions / biggest_node)) for i, c in characters.items()}
    pos = _spread(pos, {i: size / 2 + span * 0.015 for i, size in portrait.items()})

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
    fig.add_scatter(
        x=[pos[i][0] for i in characters], y=[pos[i][1] for i in characters],
        # names of characters drawn as portraits go under the portrait (below), the rest above the dot
        mode="markers+text", text=[c.name if not (avatars and i in avatars) else "" for i, c in characters.items()],
        textposition="top center",
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
    if avatars:  # characters with an avatar are drawn as their portrait, as big as their dot
        for i, c in characters.items():
            if i in avatars:
                size = portrait[i]
                fig.add_annotation(x=pos[i][0], y=pos[i][1] - size / 2, text=c.name, showarrow=False, yanchor="top",
                                   font=dict(color=theme["ink2"], size=12), bgcolor=theme["surface"], borderpad=1)
                fig.add_layout_image(source=avatars[i], xref="x", yref="y", x=pos[i][0], y=pos[i][1],
                                     sizex=size, sizey=size, xanchor="center", yanchor="middle", layer="above")
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
    fig.update_traces(line_shape="spline", line_smoothing=0.6, selector=dict(type="scatter"))  # smooth trend
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


# --- Dialogue -------------------------------------------------------------

def talk_bars(analysis: BookAnalysis, theme: dict, words: list[int], top: int = 12) -> go.Figure:
    """How many words each character says, most talkative at the top."""
    ranked = sorted((c for c in analysis.characters if words[c.id]), key=lambda c: -words[c.id])[:top][::-1]
    colors = character_colors(analysis, theme)
    fig = go.Figure(go.Bar(
        y=[c.name for c in ranked], x=[words[c.id] for c in ranked], orientation="h",
        marker=dict(color=[colors[c.id] for c in ranked], line=dict(color=theme["surface"], width=2)),
        hovertemplate="%{y} says %{x:,} words<extra></extra>",
    ))
    fig.update_yaxes(tickvals=[c.name for c in ranked], ticktext=[name_tag(c.name, colors[c.id]) for c in ranked])
    fig.update_xaxes(title="Words spoken")
    return _layout(fig, theme, height=60 + 28 * len(ranked), bargap=0.35)


def word_by_chapter(analysis: BookAnalysis, theme: dict, counts: list[int], tones: list[float | None],
                    word: str) -> go.Figure:
    """Where a searched word appears: one bar per chapter, as tall as how many sentences contain it,
    coloured by the mood of those sentences (red darker, gray neutral, blue brighter)."""
    x = list(range(1, len(counts) + 1))
    fig = go.Figure(go.Bar(
        x=x, y=counts, marker=dict(color=[_tone_color(theme, t) if t is not None else theme["grid"] for t in tones],
                                   line=dict(color=theme["surface"], width=1)),
        customdata=[[c.title, "" if t is None else f"{t:+.2f}"] for c, t in zip(analysis.chapters, tones)],
        hovertemplate=f"%{{customdata[0]}}<br>“{word}” in %{{y}} sentences · mood %{{customdata[1]}}<extra></extra>",
    ))
    fig.update_xaxes(title="Chapter")
    fig.update_yaxes(title="Sentences", rangemode="tozero")
    return _layout(fig, theme, height=320, showlegend=False, bargap=0.15)


def talk_by_chapter(analysis: BookAnalysis, theme: dict, counts: list[list[int]], unknown: list[int] | None = None,
                    share: bool = False) -> go.Figure:
    """One stacked bar per chapter: the words each main character speaks there, in their own colour
    (the coloured characters who speak at all), then everyone else (gray) and unknown speakers (pale).
    With share=True every bar is 100%: who holds the floor in each chapter."""
    colors = character_colors(analysis, theme)
    main = [c for c in top_characters(analysis, len(theme["series"])) if any(counts[c.id])]
    others = [sum(counts[c.id][ch] for c in analysis.characters if c.id not in {m.id for m in main})
              for ch in range(len(analysis.chapters))]
    groups = [(c.name, [counts[c.id][ch] for ch in range(len(analysis.chapters))], colors[c.id]) for c in main]
    groups.append(("Everyone else", others, theme["muted"]))
    if unknown:  # left out unless asked for: in most books it would dwarf the characters
        groups.append(("Speaker unknown", unknown, theme["axis"]))
    totals = [sum(g[1][ch] for g in groups) for ch in range(len(analysis.chapters))]
    x = list(range(1, len(analysis.chapters) + 1))
    titles = [c.title for c in analysis.chapters]
    fig = go.Figure()
    for name, values, color in groups:
        if not any(values):
            continue
        y = [v / t if t else 0 for v, t in zip(values, totals)] if share else values
        fig.add_bar(x=x, y=y, name=name, marker=dict(color=color, line=dict(color=theme["surface"], width=0.5)),
                    customdata=[[t, v] for t, v in zip(titles, values)],
                    hovertemplate=f"%{{customdata[0]}}<br>{name}: %{{customdata[1]:,}} words"
                                  + (" (%{y:.0%})" if share else "") + "<extra></extra>")
    fig.update_xaxes(title="Chapter")
    fig.update_yaxes(title="Share of the chapter's dialogue" if share else "Words spoken",
                     tickformat=".0%" if share else ",")
    return _layout(fig, theme, height=440, barmode="stack", bargap=0.15, legend_traceorder="normal")


def talk_matrix(analysis: BookAnalysis, theme: dict, counts: list[list[int]], top: int = 8) -> go.Figure:
    """Speakers (rows) x listeners (columns): how many lines one says to the other."""
    busiest = sorted(range(len(counts)), key=lambda i: -(sum(counts[i]) + sum(row[i] for row in counts)))[:top]
    busiest = [i for i in busiest if sum(counts[i]) + sum(row[i] for row in counts)]
    names = [analysis.characters[i].name for i in busiest]
    z = [[counts[s][t] if s != t else None for t in busiest] for s in busiest]
    steps = theme["sequential"]
    scale = [[0, theme["surface"]]] + [[0.001 + 0.999 * i / (len(steps) - 1), step] for i, step in enumerate(steps)]
    fig = go.Figure(go.Heatmap(
        z=z, x=names, y=names, colorscale=scale, zmin=0, xgap=2, ygap=2,
        hovertemplate="%{y} → %{x}: %{z} lines<extra></extra>",
        colorbar=dict(title=dict(text="Lines", font=dict(color=theme["ink2"])),
                      tickfont=dict(color=theme["muted"]), outlinewidth=0, thickness=12),
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False, title="Speaker")
    fig.update_xaxes(showgrid=False, title="Speaking to", side="top", tickangle=-30)
    return _layout(fig, theme, height=120 + 34 * len(names))


# --- Pace -----------------------------------------------------------------

PACE_ROWS = (  # (field, row title, hover format)
    ("pace", "Pace (faster ↑ · slower ↓, vs. the book's usual)", "%{y:+.2f}"),
    ("sentence_length", "Words per sentence", "%{y:.1f} words"),
    ("dialogue", "Share of words in dialogue", "%{y:.0%}"),
    ("action", "Action: verbs per verb + adjective", "%{y:.0%}"),
)


def pace_chapters(analysis: BookAnalysis, theme: dict, paces: list, scores: list[float]) -> go.Figure:
    """Small multiples, one measure per row, chapters along the bottom (one shared x axis,
    each row its own y axis: never two scales on one axis)."""
    from plotly.subplots import make_subplots

    rows = [r for r in PACE_ROWS if r[0] != "action" or all(p.action is not None for p in paces)]
    fig = make_subplots(rows=len(rows), cols=1, shared_xaxes=True, vertical_spacing=0.07,
                        subplot_titles=[title for _, title, _ in rows])
    x = list(range(1, len(paces) + 1))
    titles = [c.title for c in analysis.chapters]
    for r, (field, _, fmt) in enumerate(rows, start=1):
        values = scores if field == "pace" else [getattr(p, field) for p in paces]
        color = ([theme["ink2"] if v >= 0 else theme["muted"] for v in values] if field == "pace"
                 else theme["ink2"])
        fig.add_bar(x=x, y=values, row=r, col=1, marker=dict(color=color, line=dict(width=0)),
                    customdata=titles, hovertemplate=f"%{{customdata}}: {fmt}<extra></extra>", showlegend=False)
        if field in ("dialogue", "action"):
            fig.update_yaxes(tickformat=".0%", row=r, col=1)
    fig.update_annotations(font=dict(size=12, color=theme["ink2"]), x=0, xanchor="left")
    fig.update_xaxes(title="Chapter", row=len(rows), col=1)
    fig = _layout(fig, theme, height=110 + 135 * len(rows), bargap=0.2)
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    return fig


LIBRARY_ROWS = (  # (key, label, hover format)
    ("hours", "Reading time (hours)", ".1f"),
    ("grade", "Reading level (school grade)", ".1f"),
    ("sentence_length", "Words per sentence", ".1f"),
    ("dialogue", "Dialogue", ".0%"),
    ("richness", "Vocabulary (different words per 100)", ".0%"),
)


def library_strip(theme: dict, books: list[dict], current: dict) -> go.Figure:
    """One row per measure: a dot for each famous book, this book in strong ink and
    labelled, so you can see where it sits. Each row has its own scale (hover for values)."""
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=len(LIBRARY_ROWS), cols=1, vertical_spacing=0.16,
                        subplot_titles=[label for _, label, _ in LIBRARY_ROWS])
    for r, (key, _, fmt) in enumerate(LIBRARY_ROWS, start=1):
        fig.add_scatter(x=[b[key] for b in books], y=[0] * len(books), row=r, col=1, mode="markers",
                        marker=dict(size=11, color=theme["muted"], opacity=0.55,
                                    line=dict(color=theme["surface"], width=2)),
                        customdata=[b["title"] for b in books],
                        hovertemplate=f"%{{customdata}}: %{{x:{fmt}}}<extra></extra>", showlegend=False)
        fig.add_scatter(x=[current[key]], y=[0], row=r, col=1, mode="markers+text", text=["this book"],
                        textposition="top center", textfont=dict(color=theme["ink"], size=11),
                        marker=dict(size=15, color=theme["ink"], line=dict(color=theme["surface"], width=2)),
                        customdata=[current["title"]],
                        hovertemplate=f"%{{customdata}}: %{{x:{fmt}}}<extra></extra>", showlegend=False)
        fig.update_yaxes(visible=False, range=[-0.6, 1.1], row=r, col=1)
        fig.update_xaxes(tickformat=fmt, showgrid=False, row=r, col=1)
    fig.update_annotations(font=dict(size=12, color=theme["ink2"]), x=0, xanchor="left")
    return _layout(fig, theme, height=105 * len(LIBRARY_ROWS) + 30)
