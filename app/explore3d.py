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
}
TOP_CHARACTERS = 14  # more stars than this crowd the scenes
MIN_LINK = 10  # relationships with fewer shared moments are left out
EMOTION_SCENES = {"crystal"}
# Pictures on the Story road. One visual rule: themes are objects, feelings are faces.
# A picture for each chapter theme (analyzer/chapter_events.THEMES)...
THEME_ICONS = {
    "Ball": "💃", "Proposal": "💍", "Engagement": "💑", "Wedding": "💒", "Letter": "📜", "Journey": "🐎",
    "Visit": "🚪", "Argument": "💢", "Gossip": "💬", "Revelation": "🔍", "Scandal": "📰", "Betrayal": "🐍",
    "Confrontation": "🥊", "Reconciliation": "🤝", "Romance": "🌹", "Illness": "🩺", "Death": "🪦",
    "Battle": "⚔️", "Danger": "⚠️", "Adventure": "🧭", "Celebration": "🎉", "Sadness": "🥀", "Family": "🏠",
    "Money": "💰",
}
NO_ICON = "📖"  # keyword-only themes (analyses made before chapter themes existed)
# ...and a face for each emotion family (analyzer/emotions.FAMILIES)
EMOTION_ICONS = {"love": "🥰", "joy": "😄", "surprise": "😲", "shame": "😳", "sadness": "😢", "anger": "😠",
                 "fear": "😨", "disapproval": "😒"}
# Only the important chapters get a picture, spaced apart, so the road stays calm
KEY_THEMES = 9  # turning points first, then the clearest themes
KEY_FEELINGS = 8
MIN_GAP = 3  # chapters between two pictures of the same kind
FEELING_LIFT = 1.3  # a chapter's feeling must be at least this many times its share in the whole book


def _spaced(candidates: list[int], taken: list[int], limit: int) -> list[int]:
    """Up to `limit` of the candidates (best first), each MIN_GAP chapters from the others."""
    picked: list[int] = []
    for i in candidates:
        if len(picked) >= limit:
            break
        if all(abs(i - j) >= MIN_GAP for j in taken + picked):
            picked.append(i)
    return picked


def key_themes(events: list, turning: list[tuple[int, str]]) -> list[int]:
    """The chapters whose theme gets a badge: every turning point, then the
    clearest themes (highest strength). Keyword-only themes get none."""
    if not any(e.theme in THEME_ICONS for e in events):
        return []
    turns = [i for i, _ in turning]
    rest = sorted((i for i, e in enumerate(events) if e.theme in THEME_ICONS and i not in turns),
                  key=lambda i: -events[i].strength)
    return sorted(turns + _spaced(rest, turns, KEY_THEMES - len(turns)))


def key_feelings(analysis: BookAnalysis) -> list[dict]:
    """The chapters where one feeling clearly stands out: [{"i": chapter, "emotion": family}].
    For each chapter, the family most above its share in the whole book."""
    book = charts.without_neutral(average_emotions([s.emotions for s in analysis.sentences]))
    if not book:
        return []
    best = {}
    for i, mix in enumerate(analysis.chapter_emotions):
        shares = charts.without_neutral(mix)
        lifts = {e: shares.get(e, 0) / book[e] for e in charts.EMOTION_ORDER if book.get(e)}
        if lifts:
            e = max(lifts, key=lifts.get)
            if lifts[e] >= FEELING_LIFT:
                best[i] = (lifts[e], e)
    chosen = _spaced(sorted(best, key=lambda i: -best[i][0]), [], KEY_FEELINGS)
    return [{"i": i, "emotion": best[i][1]} for i in sorted(chosen)]  # scenes that need emotions to say anything


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


def presence(by_chapter: list[list[int]], smooth: int = 1) -> list[list[float]]:
    """[character][chapter] -> how much of the chapter is about them: their share of the
    mentions of these characters in it, as a moving average over `smooth` chapters on each
    side (so a character doesn't blink out for one quiet chapter). Drives who walks the road."""
    chapters = len(by_chapter[0]) if by_chapter else 0
    totals = [sum(row[ch] for row in by_chapter) for ch in range(chapters)]
    shares = [[row[ch] / totals[ch] if totals[ch] else 0.0 for ch in range(chapters)] for row in by_chapter]
    return [[round(sum(row[max(0, ch - smooth):ch + smooth + 1]) / len(row[max(0, ch - smooth):ch + smooth + 1]), 3)
             for ch in range(chapters)] for row in shares]


def scene_data(analysis: BookAnalysis, avatars: dict | None = None) -> dict:
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
            "avatar": (avatars or {}).get(c.id),  # a data: URI, or None for minor characters
            "mentions": c.mentions,
            "emotions": _shares(analysis.character_emotions[c.id] if analysis.character_emotions else {}),
            # the fine emotions most above the book's average, e.g. ["guilt", "gratitude"]
            "standOut": stand_out(analysis.character_fine[c.id], book_fine) if analysis.character_fine else [],
            "sentiment": round(sum(tones) / len(tones), 3) if tones else 0.0,
            "byChapter": analysis.mentions_by_chapter[c.id],
            "toneByChapter": [_round(t) for t in analysis.sentiment_by_chapter[c.id]],
        })
    links = [
        {"a": index[r.source], "b": index[r.target], "count": r.count, "tone": round(r.sentiment, 3)}
        for r in analysis.relationships
        if r.source in index and r.target in index and r.count >= MIN_LINK
    ]
    for person, share in zip(people, presence([p["byChapter"] for p in people])):
        person["presence"] = share
    arc, turning, acts = story_arc(analysis.chapter_sentiment)  # turning points and acts
    events = events_of(analysis)
    return {
        "keyThemes": key_themes(events, turning),
        "keyFeelings": key_feelings(analysis),
        "emotionIcons": EMOTION_ICONS,
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
                          for e in events],
        "chapterDetails": charts.chapter_details(analysis),
        "characters": people,
        "links": links,
    }


def scene_html(analysis: BookAnalysis, scene: str, avatars: dict | None = None) -> str:
    """The complete page for one scene."""
    if scene not in SCENES:
        raise ValueError(f"Unknown scene: {scene}")
    # "</" inside the data could end the <script> tag early, so escape it
    data = json.dumps(scene_data(analysis, avatars), separators=(",", ":")).replace("</", "<\\/")
    # fill in the scene first, so text inside the data can never be mistaken for a placeholder
    return TEMPLATE.read_text(encoding="utf-8").replace("__SCENE__", scene).replace("__DATA__", data)
