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
    },
    "dark": {
        "surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
        "grid": "#2c2c2a", "axis": "#383835",
        "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"],
        "sequential": ["#104281", "#1c5cab", "#2a78d6", "#5598e7", "#86b6ef", "#cde2fb"],
        "diverging": ["#e66767", "#52514e", "#3987e5"],
    },
}
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
    names = [c.name for c in characters]
    fig = go.Figure()
    for label, values, color in (
        ("By name", [by_name[c.id] for c in characters], theme["series"][0]),
        ("By pronoun or description", [c.mentions - by_name[c.id] for c in characters], theme["series"][1]),
    ):
        fig.add_bar(
            y=names, x=values, name=label, orientation="h", marker_color=color,
            marker_line=dict(color=theme["surface"], width=2),  # 2px gap between segments
            hovertemplate="%{y}: %{x:,} " + label.lower() + "<extra></extra>",
        )
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
    fig.update_xaxes(title="Chapter", range=[0.5, len(chapters) + (6 if len(lines) > 1 else 0.5)])
    return _layout(fig, theme, height=440, hovermode="x unified")


# --- Timeline --------------------------------------------------------------

def timeline_heatmap(analysis: BookAnalysis, theme: dict, top: int = 15) -> go.Figure:
    characters = top_characters(analysis, top)
    z = [analysis.mentions_by_chapter[c.id] for c in characters]
    steps = theme["sequential"]
    # 0 mentions shows as the background; then light -> dark as mentions grow
    start = 0.001
    scale = [[0, theme["surface"]]] + [
        [start + (1 - start) * i / (len(steps) - 1), step] for i, step in enumerate(steps)
    ]
    fig = go.Figure(go.Heatmap(
        z=z, x=list(range(1, len(analysis.chapters) + 1)), y=[c.name for c in characters],
        colorscale=scale, zmin=0, xgap=2, ygap=2,
        customdata=[[t.title for t in analysis.chapters]] * len(characters),
        hovertemplate="%{y}, %{customdata}: %{z} mentions<extra></extra>",
        colorbar=dict(title=dict(text="Mentions", font=dict(color=theme["ink2"])),
                      tickfont=dict(color=theme["muted"]), outlinewidth=0, thickness=12),
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(title="Chapter", showgrid=False)
    return _layout(fig, theme, height=80 + 26 * len(characters))


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
        line=dict(color=theme["series"][0], width=2), marker=dict(size=8),
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
        marker=dict(color=theme["series"][0], line=dict(color=theme["surface"], width=2)),
        customdata=[c.title for c in analysis.chapters],
        hovertemplate="%{customdata}: %{y} moments together<extra></extra>",
    ))
    fig.update_xaxes(title="Chapter", range=[0.5, len(analysis.chapters) + 0.5])
    fig.update_yaxes(title="Moments together")
    return _layout(fig, theme, height=220, showlegend=False, bargap=0.1)
