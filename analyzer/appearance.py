"""Read what the book says a character looks like, for drawing their avatar.

Clues come only from sentences that mention one character and nobody else,
so "her grey hair" can't be credited to the wrong person. Common words
("young", "old") count only when they are clearly more frequent around this
character than in the book as a whole. What the book doesn't say is filled in
from the story: the title (Mr./Miss) or pronouns give the gender, the book's
world (19th-century or fantasy) sets the clothes, the mood sets the expression.
"""

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .models import BookAnalysis

HAIR_WORDS = {
    "black": "black", "dark": "dark", "brown": "brown", "fair": "fair", "light": "fair", "flaxen": "fair",
    "golden": "golden", "yellow": "golden", "red": "red", "auburn": "auburn", "sandy": "sandy",
    "grey": "grey", "gray": "grey", "white": "white", "silver": "white",
}
_COLOUR = "|".join(HAIR_WORDS)
HAIR = re.compile(rf"\b({_COLOUR})[- ]haired\b|\b({_COLOUR}) (?:\w+ )?(?:hair|curls|locks|ringlets)\b", re.IGNORECASE)
AGE = {
    "old": re.compile(r"\b(old|elderly|aged|wrinkled|venerable|grey-haired|white-haired)\b", re.IGNORECASE),
    "young": re.compile(r"\b(boy|girl|child|lad|youth|youngster)\b", re.IGNORECASE),
}
FEATURES = {
    "bride": re.compile(r"\b(bride|bridal|wedding[- ]dress|veil)\b", re.IGNORECASE),
    "glasses": re.compile(r"\b(spectacles|eye-?glass(?:es)?)\b", re.IGNORECASE),
    "beard": re.compile(r"\b(beard|bearded)\b", re.IGNORECASE),
    "whiskers": re.compile(r"\b(whiskers|moustache|mustache|side-?burns)\b", re.IGNORECASE),
}
# job or kind of being -> the outfit that draws it; the gender a role implies in these books
ROLES = {
    "blacksmith": "blacksmith", "smith": "blacksmith", "forge": "blacksmith", "lawyer": "lawyer",
    "attorney": "lawyer", "clerk": "clerk", "convict": "convict", "prisoner": "convict", "soldier": "soldier",
    "sergeant": "soldier", "officer": "soldier", "colonel": "soldier", "clergyman": "clergy", "parson": "clergy",
    "vicar": "clergy", "curate": "clergy", "doctor": "doctor", "physician": "doctor", "maid": "maid",
    "housekeeper": "maid", "servant": "servant", "sailor": "sailor", "schoolmistress": "teacher",
    "governess": "teacher", "teacher": "teacher", "king": "royal", "queen": "royal", "prince": "royal",
    "princess": "royal", "wizard": "wizard", "hobbit": "hobbit", "elf": "elf", "elves": "elf", "dwarf": "dwarf",
    "ranger": "ranger",
}
# a crown is a loud mistake (an actor playing a king), so royalty needs more proof
MIN_CHAPTERS = {"royal": 3}
MALE_ROLES = {"blacksmith", "soldier", "clergy", "convict", "wizard", "dwarf", "ranger", "sailor"}
FEMALE_ROLES = {"maid"}
MALE_TITLES = {"Mr.", "Sir", "Lord", "Colonel", "Captain", "Uncle", "Rev.", "Dr.", "Professor"}
FEMALE_TITLES = {"Mrs.", "Miss", "Ms.", "Lady", "Aunt"}
FANTASY_WORDS = re.compile(r"\b(hobbits?|elves|elf|elvish|wizards?|dwarf|dwarves|orcs?|goblins?|dragons?|sorcer\w+|"
                           r"enchant\w+|magic)\b", re.IGNORECASE)
MODERN_WORDS = re.compile(r"\b(telephone|phone|car|cars|computer|television|radio|airplane|taxi|email)\b", re.IGNORECASE)


@dataclass
class Appearance:
    gender: str = "?"  # "m", "f" or "?"
    age: str = "adult"  # "young", "adult" or "old"
    hair: str | None = None  # a HAIR_WORDS colour the book gives, else None (the drawing improvises)
    role: str | None = None  # a ROLES outfit, else None
    features: set[str] = field(default_factory=set)  # bride, glasses, beard, whiskers
    mood: float = 0.0  # the character's average tone, for the expression
    world: str = "period"  # "period" (classic novel), "fantasy" or "modern"
    evidence: list[str] = field(default_factory=list)  # what the book said, e.g. "bride ×8"


def book_world(analysis: BookAnalysis) -> str:
    """Which world the book is set in, from how often tell-tale words appear."""
    text = " ".join(s.text for s in analysis.sentences)
    words = max(1, len(text.split()))
    if len(FANTASY_WORDS.findall(text)) / words > 0.0015:
        return "fantasy"
    if len(MODERN_WORDS.findall(text)) / words > 0.0008:
        return "modern"
    return "period"


def describe(analysis: BookAnalysis, top: int = 12) -> dict[int, Appearance]:
    """{character id: Appearance} for the `top` most mentioned characters."""
    world = book_world(analysis)
    people = sorted(analysis.characters, key=lambda c: -c.mentions)[:top]
    in_sentence: dict[int, set[int]] = defaultdict(set)
    pronouns: dict[int, Counter] = defaultdict(Counter)
    for m in analysis.mentions:
        in_sentence[m.sentence_index].add(m.character_id)
        word = m.text.lower()
        if word in ("he", "him", "his", "himself"):
            pronouns[m.character_id]["m"] += 1
        elif word in ("she", "her", "hers", "herself"):
            pronouns[m.character_id]["f"] += 1
    # how often the age words appear per sentence in the whole book (the baseline)
    total = max(1, len(analysis.sentences))
    base = {k: sum(bool(p.search(s.text)) for s in analysis.sentences) / total for k, p in AGE.items()}
    role_base = Counter(ROLES[w.lower()] for s in analysis.sentences
                        for w in re.findall(r"[A-Za-z]+", s.text) if w.lower() in ROLES)

    looks = {}
    for c in people:
        solo_sentences = [s for s in analysis.sentences if in_sentence.get(s.index) == {c.id}]
        solo = [s.text for s in solo_sentences]
        look = Appearance(world=world, evidence=[])
        tones = [t for t in analysis.sentiment_by_chapter[c.id] if t is not None]
        look.mood = sum(tones) / len(tones) if tones else 0.0

        hair = Counter(HAIR_WORDS[(m.group(1) or m.group(2)).lower()] for t in solo for m in HAIR.finditer(t))
        if hair:
            colour, n = hair.most_common(1)[0]
            # one mention is enough for a plain colour, but grey/white (which also makes them old) needs two
            if n >= 2 or (len(hair) == 1 and colour not in ("grey", "white")):
                look.hair = colour
                look.evidence.append(f"{colour} hair ×{n}")

        for feature, pattern in FEATURES.items():
            n = sum(len(pattern.findall(t)) for t in solo)
            if n >= 2:
                look.features.add(feature)
                look.evidence.append(f"{feature} ×{n}")

        roles, role_chapters = Counter(), defaultdict(set)
        for s in solo_sentences:
            for w in re.findall(r"[A-Za-z]+", s.text):
                if w.lower() in ROLES:
                    roles[ROLES[w.lower()]] += 1
                    role_chapters[ROLES[w.lower()]].add(s.chapter)
        # a role is *theirs* when it comes up around them in several chapters (one scene with
        # soldiers doesn't make Joe a soldier) and is a good share of all the book's uses of it
        theirs = [(len(role_chapters[r]), n / max(role_base[r], 1), n, r) for r, n in roles.items()
                  if n >= 2 and len(role_chapters[r]) >= MIN_CHAPTERS.get(r, 2) and n / max(role_base[r], 1) >= 0.15]
        if theirs:
            chapters, _, n, role = max(theirs)
            look.role = role
            look.evidence.append(f"{role} ×{n} in {chapters} chapters")

        if solo:
            rate = {k: sum(bool(p.search(t)) for t in solo) / len(solo) for k, p in AGE.items()}
            lift = {k: rate[k] / max(base[k], 1e-6) for k in AGE}
            if any(a.lower().startswith(("young ", "little ", "master ")) for a in c.aliases):
                look.age = "young"
            elif any(a.lower().startswith("old ") for a in c.aliases):
                look.age = "old"
            elif lift["old"] >= 1.6 and rate["old"] >= 0.04 and lift["old"] > lift["young"]:
                look.age = "old"
            elif lift["young"] >= 1.8 and rate["young"] >= 0.04:
                look.age = "young"
        if look.hair in ("grey", "white") and look.age != "young":
            look.age = "old"

        look.gender = _gender(c.aliases, pronouns[c.id], look.role)
        looks[c.id] = look
    return looks


def _gender(aliases: list[str], pronouns: Counter, role: str | None) -> str:
    titles = {a.split()[0] for a in aliases if " " in a}
    male, female = bool(titles & MALE_TITLES), bool(titles & FEMALE_TITLES)
    bare = any(" " not in a for a in aliases)  # also called by a plain name
    if male != female and not (bare and role):
        return "m" if male else "f"
    # titles disagree, or a plain name with a known job: the job decides, then the pronouns
    if role in MALE_ROLES:
        return "m"
    if role in FEMALE_ROLES:
        return "f"
    if male != female:
        return "m" if male else "f"
    if pronouns["m"] > 2 * pronouns["f"]:
        return "m"
    if pronouns["f"] > 2 * pronouns["m"]:
        return "f"
    return "?"
