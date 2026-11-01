"""Interactive 3D scenes (Three.js) for the "Explore in 3D" tab.

Python prepares a small JSON summary of the analysis; explore3d.html draws
it in the browser. Only one scene runs at a time, so the page keeps a
single 3D canvas.
"""

import json
from pathlib import Path

import charts
from analyzer.chapter_events import name_chapters
from analyzer.emotions import average_emotions
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
EMOTION_SCENES = {"crystal"}  # scenes that need emotions to say anything


def _shares(mix: dict[str, float]) -> list[float]:
    """The six emotions' shares (neutral left out), in charts.EMOTION_ORDER."""
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
    people = []
    for c in characters:
        tones = [t for t in analysis.sentiment_by_chapter[c.id] if t is not None]
        people.append({
            "name": c.name,
            "color": colors[c.id],
            "mentions": c.mentions,
            "emotions": _shares(analysis.character_emotions[c.id] if analysis.character_emotions else {}),
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
        # the stage is always dark, so it uses the dark-mode emotion colours
        "emotionColors": {e: charts.THEMES["dark"]["emotions"][e] for e in charts.EMOTION_ORDER},
        "emotionLabels": {e: charts.EMOTION_LABELS[e].split(" (")[0] for e in charts.EMOTION_ORDER},
        "chapters": len(analysis.chapters),
        "chapterTitles": [c.title for c in analysis.chapters],
        "chapterTone": [round(t, 3) for t in analysis.chapter_sentiment],
        "chapterEmotions": [_shares(mix) for mix in analysis.chapter_emotions] or [[0.0] * 6] * len(analysis.chapters),
        "bookEmotions": _shares(average_emotions([s.emotions for s in analysis.sentences])),
        "chapterNeutral": [round(mix.get("neutral", 0.0), 3) for mix in analysis.chapter_emotions]
                          or [1.0] * len(analysis.chapters),
        "chapterEvents": [{"theme": e.theme, "event": e.event, "keywords": e.keywords, "strength": e.strength}
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
