"""Interactive 3D scenes (Three.js) for the "Explore in 3D" tab.

Python prepares a small JSON summary of the analysis; explore3d.html draws
it in the browser. Only one scene runs at a time, so the page keeps a
single 3D canvas.
"""

import json
from pathlib import Path

import charts
from analyzer.chapter_events import name_chapters
from analyzer.emotions import average_emotions, stand_out
from analyzer.models import BookAnalysis
from analyzer.progression import story_arc

TEMPLATE = Path(__file__).with_name("explore3d.html")
SCENES = {
    "road": "Story road",
    "constellation": "Character constellation",
    "crystal": "Emotion crystal",
    "dna": "Relationship DNA",
}
TOP_CHARACTERS = 14  # more stars than this crowd the scenes
MIN_LINK = 10  # relationships with fewer shared moments are left out
EMOTION_SCENES = {"crystal"}
# a picture for each chapter theme (analyzer/chapter_events.THEMES), shown on the Story road
THEME_ICONS = {
    "Ball": "💃", "Proposal": "💍", "Engagement": "💑", "Wedding": "💒", "Letter": "📜", "Journey": "🐎",
    "Visit": "🚪", "Argument": "💢", "Gossip": "💬", "Revelation": "🔍", "Scandal": "📰", "Betrayal": "🐍",
    "Confrontation": "😠", "Reconciliation": "🤝", "Romance": "🌹", "Illness": "🤒", "Death": "🪦",
    "Battle": "⚔️", "Danger": "⚠️", "Adventure": "🧭", "Celebration": "🎉", "Sadness": "😢", "Family": "🏠",
    "Money": "💰",
}
NO_ICON = "📖"  # keyword-only themes (analyses made before chapter themes existed)  # scenes that need emotions to say anything


def _shares(mix: dict[str, float]) -> list[float]:
    """The emotion families' shares (neutral left out), in charts.EMOTION_ORDER."""
    shares = charts.without_neutral(mix)
    return [round(shares.get(e, 0.0), 3) for e in charts.EMOTION_ORDER]


def events_of(analysis: BookAnalysis) -> list:
    """The analysis's chapter events; analyses saved before themes existed
    get keyword-only events (instant, no model)."""
    return analysis.chapter_events or name_chapters(
        analysis.sentences, analysis.characters, len(analysis.chapters), embed=None)


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 3)


def scene_data(analysis: BookAnalysis) -> dict:
    characters = charts.top_characters(analysis, TOP_CHARACTERS)
    index = {c.id: i for i, c in enumerate(characters)}
    # the stage is always dark, so characters keep their dark-mode chart colour
    colors = charts.character_colors(analysis, charts.THEMES["dark"])
    book_fine = average_emotions([s.fine for s in analysis.sentences])
    people = []
    for c in characters:
        tones = [t for t in analysis.sentiment_by_chapter[c.id] if t is not None]
        people.append({
            "name": c.name,
            "color": colors[c.id],
            "mentions": c.mentions,
            "emotions": _shares(analysis.character_emotions[c.id] if analysis.character_emotions else {}),
            # the fine emotions most above the book's average, e.g. ["guilt", "gratitude"]
            "standOut": stand_out(analysis.character_fine[c.id], book_fine) if analysis.character_fine else [],
            "sentiment": round(sum(tones) / len(tones), 3) if tones else 0.0,
            "byChapter": analysis.mentions_by_chapter[c.id],
            "toneByChapter": [_round(t) for t in analysis.sentiment_by_chapter[c.id]],
        })
    links = [
        {"a": index[r.source], "b": index[r.target], "count": r.count, "tone": round(r.sentiment, 3),
         "byChapter": r.chapter_counts}
        for r in analysis.relationships
        if r.source in index and r.target in index and r.count >= MIN_LINK
    ]
    arc, turning, acts = story_arc(analysis.chapter_sentiment)  # the same shape as the 2D Story arc chart
    return {
        "arc": [round(v, 4) for v in arc],
        "turning": [{"i": i, "kind": kind} for i, kind in turning],
        "acts": acts,
        "emotions": charts.EMOTION_ORDER,
        "warm": [e for e in charts.EMOTION_ORDER if e in charts.WARM_EMOTIONS],
        # the stage is always dark, so it uses the dark-mode emotion colours
        "emotionColors": {e: charts.THEMES["dark"]["emotions"][e] for e in charts.EMOTION_ORDER},
        "emotionLabels": {e: charts.short_label(e) for e in charts.EMOTION_ORDER},
        "chapters": len(analysis.chapters),
        "chapterTitles": [c.title for c in analysis.chapters],
        "chapterTone": [round(t, 3) for t in analysis.chapter_sentiment],
        "chapterEmotions": [_shares(mix) for mix in analysis.chapter_emotions]
                           or [[0.0] * len(charts.EMOTION_ORDER)] * len(analysis.chapters),
        "chapterStandOut": [stand_out(mix, book_fine) for mix in analysis.chapter_fine]
                           or [[] for _ in analysis.chapters],
        "bookEmotions": _shares(average_emotions([s.emotions for s in analysis.sentences])),
        "chapterNeutral": [round(mix.get("neutral", 0.0), 3) for mix in analysis.chapter_emotions]
                          or [1.0] * len(analysis.chapters),
        "chapterEvents": [{"theme": e.theme, "event": e.event, "keywords": e.keywords, "strength": e.strength,
                           "icon": THEME_ICONS.get(e.theme, NO_ICON)}
                          for e in events_of(analysis)],
        "chapterDetails": charts.chapter_details(analysis),
        "characters": people,
        "links": links,
    }


def scene_html(analysis: BookAnalysis, scene: str) -> str:
    """The complete page for one scene."""
    if scene not in SCENES:
        raise ValueError(f"Unknown scene: {scene}")
    # "</" inside the data could end the <script> tag early, so escape it
    data = json.dumps(scene_data(analysis), separators=(",", ":")).replace("</", "<\\/")
    # fill in the scene first, so text inside the data can never be mistaken for a placeholder
    return TEMPLATE.read_text(encoding="utf-8").replace("__SCENE__", scene).replace("__DATA__", data)
