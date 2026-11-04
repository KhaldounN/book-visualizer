"""What part each main character plays in the story, read from the analysis (no model, instant).

Short labels for the cast cards, each backed by numbers the page also shows:
"Main character", "Closest to Elizabeth", "Darker scenes with Elizabeth", "Bennet family",
"Ends happier" / "Ends darker".
"""

from collections import defaultdict

from .models import BookAnalysis, Character

TITLES = {"Mr.", "Mrs.", "Miss", "Ms.", "Dr.", "Sir", "Lady", "Lord", "Captain", "Colonel", "Rev.", "Professor",
          "Aunt", "Uncle", "Master", "Mister", "Madame", "Monsieur"}
MIN_SHARED = 15  # a pair needs this many moments together before we call them close or clashing
CLASH_GAP = 0.08  # their shared tone must be this much below the main character's average pairing
ARC_CHANGE = 0.08  # mood change from the first to the last third that counts as an arc


def surname(c: Character) -> str | None:
    """The family name, from the longest way the book names them: "Mrs. Bennet" -> "Bennet",
    "Jane Bennet" -> "Bennet". None for a single name ("Wickham" might be a first name or a surname)."""
    for alias in sorted(c.aliases, key=lambda a: -len(a.split())):
        words = alias.split()
        if len(words) >= 2 and words[-1][:1].isupper() and words[-1] not in TITLES:
            return words[-1]
    return None


def _mood_by_third(analysis: BookAnalysis, character_id: int) -> tuple[float | None, float | None]:
    """Their average chapter mood in the first and last third of the book."""
    tones = analysis.sentiment_by_chapter[character_id] if character_id < len(analysis.sentiment_by_chapter) else []
    third = max(1, len(tones) // 3)
    first = [t for t in tones[:third] if t is not None]
    last = [t for t in tones[-third:] if t is not None]
    avg = lambda xs: sum(xs) / len(xs) if len(xs) >= 2 else None  # noqa: E731
    return avg(first), avg(last)


def story_roles(analysis: BookAnalysis, top: int = 8) -> dict[int, list[str]]:
    """{character id: up to two labels} for the `top` most mentioned characters."""
    cast = sorted(analysis.characters, key=lambda c: -c.mentions)[:top]
    if not cast:
        return {}
    main = cast[0]
    roles: dict[int, list[str]] = defaultdict(list)
    roles[main.id].append("Main character")

    # the main character's pairs: closest (most moments), clashing (clearly darker than their others)
    pairs = {(r.target if r.source == main.id else r.source): r for r in analysis.relationships
             if main.id in (r.source, r.target) and r.count >= MIN_SHARED}
    in_cast = {c.id for c in cast}
    if pairs:
        closest = max(pairs, key=lambda i: pairs[i].count)
        if closest in in_cast:
            roles[closest].append(f"Closest to {main.name}")
        typical = sum(r.sentiment * r.count for r in pairs.values()) / sum(r.count for r in pairs.values())
        darkest = min(pairs, key=lambda i: pairs[i].sentiment)
        if darkest in in_cast and pairs[darkest].sentiment < typical - CLASH_GAP and darkest != closest:
            roles[darkest].append(f"Darker scenes with {main.name}")

    # families: two or more of the cast sharing a surname
    families = defaultdict(list)
    for c in cast:
        if name := surname(c):
            families[name].append(c.id)
    for name, members in families.items():
        if len(members) >= 2:
            for i in members:
                roles[i].append(f"{name} family")

    # arcs: does their mood end clearly brighter or darker than it began?
    for c in cast:
        start, end = _mood_by_third(analysis, c.id)
        if start is not None and end is not None and abs(end - start) >= ARC_CHANGE:
            roles[c.id].append("Ends happier" if end > start else "Ends darker")
    return {i: labels[:2] for i, labels in roles.items()}
