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

from .emotions import average_emotions
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
    eyes: str | None = None  # blue, grey, dark, black, brown, green, hazel
    build: str | None = None  # tall, short, stout, thin
    complexion: str | None = None  # pale, ruddy, dark
    hairstyle: str | None = None  # curly, bald, long
    years: int | None = None  # an age the book gives ("a man of fifty")
    emotion: str | None = None  # the emotion family that stands out around them (the expression)
    unsure_marks: dict[str, int] = field(default_factory=dict, repr=False)  # marks known only from pronouns
    mark_scores: dict[str, int] = field(default_factory=dict, repr=False)  # 2 x sure + unsure clues, per mark


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

        add_traits(look, _attached(analysis, c.id), solo)
        if look.hairstyle == "bald" and look.age == "young":  # a bald child is a misreading
            look.hairstyle = None
            look.evidence = [e for e in look.evidence if not e.startswith("bald")]
        look.emotion = standout_emotion(analysis, c.id)
        look.gender = _gender(c.name, c.aliases, pronouns[c.id], look.role)
        # a job that contradicts the gender was read from the wrong person ("maid" near Mr. Darcy)
        if (look.gender == "m" and look.role in FEMALE_ROLES) or (look.gender == "f" and look.role in MALE_ROLES):
            look.evidence = [e for e in look.evidence if not e.startswith(look.role)]
            look.role = None
        looks[c.id] = look
    # a mark known only from linked pronouns ("his pipe") goes to the character with the most such
    # clues: a wrongly linked pronoun must not hand the narrator everyone else's pipe
    for look in looks.values():
        for mark, n in list(look.unsure_marks.items()):
            # someone else has it for sure ("Joe's pipe"), or more clues point to them
            if any(other is not look and ((mark in other.features and mark not in other.unsure_marks)
                                          or other.mark_scores.get(mark, 0) > look.mark_scores[mark])
                   for other in looks.values()):
                look.features.discard(mark)
                look.evidence = [e for e in look.evidence if not e.startswith(f"{mark} ×")]
    return looks


# Common first names in English-language classics, for when no title says it
MALE_NAMES = set("""abel abraham adam albert alexander alfred algernon allan ambrose andrew anthony archibald arthur
august augustus ben benjamin bernard bertram bill bob caleb charles charley christopher clarence cuthbert daniel
david dick dorian edgar edmund edward edwin ernest felix fitzwilliam francis frank fred frederick gabriel geoffrey
george gerald gilbert godfrey gregory guy harold harry henry herbert horace hugh humphrey isaac jack jacob james
jasper jem jim joe john jonathan joseph joshua julian lawrence leonard lewis louis luke mark martin matthew michael
nathaniel ned nicholas noah oliver oscar owen patrick paul percy peter philip pip ralph reginald richard robert
robin roger rupert samuel sam silas simon stephen sydney theodore thomas tim timothy tom toby victor walter will
william""".split())
FEMALE_NAMES = set("""ada adela agnes alice amelia amy ann anna anne annie arabella barbara beatrice bella beth betsy
biddy caroline catherine cathy cecilia cecily charlotte clara clarissa constance cora dora dorothea dorothy edith
eleanor elinor eliza elizabeth ella ellen emily emma esther estella eva evelyn fanny florence frances georgiana
grace hannah harriet helen henrietta hester isabel isabella jane janet jenny jo joan josephine judith julia kate
kitty laura lavinia lizzy lizzie louisa lucy lydia mabel margaret maria marian marianne martha mary matilda maud meg
mina miriam molly nancy nell nelly olivia peggy phoebe polly rachel rebecca rosa rosamond rose ruth sally sarah
sophia sophy susan sybil teresa wendy""".split())


def _gender(name: str, aliases: list[str], pronouns: Counter, role: str | None) -> str:
    """m, f or ?: the title of the main name (Mr. Darcy), else a known first name (Jonathan),
    else the other names' titles and the job, else the pronouns linked to them."""
    first = name.split()[0]
    if first in MALE_TITLES or first in FEMALE_TITLES:
        return "m" if first in MALE_TITLES else "f"
    given = first.lower().strip(".,")
    if given in MALE_NAMES or given in FEMALE_NAMES:
        return "m" if given in MALE_NAMES else "f"
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


# --- More traits, read from the words attached to a character ------------------------------------
# A description belongs to a character when it hangs off them in the sentence: right after their
# possessive ("his grey eyes", "Darcy's tall figure", a pronoun the coreference step linked to them)
# or right after their name ("Mr. Hurst, a stout man", "Jane was pale"). That works even when other
# people are named in the same sentence, unlike the "only this character" sentences used above.
WINDOW_WORDS = 7  # how many words after the possessive or name are read

EYES = re.compile(r"\b(blue|grey|gray|dark|black|brown|green|hazel)(?:[- ]\w+)?[ -]eyes?\b|"
                  r"\beyes (?:were |of )?(?:a )?(?:\w+ )?(blue|grey|gray|dark|black|brown|green|hazel)\b", re.IGNORECASE)
EYE_COLOUR = {"gray": "grey"}
BUILD_WORDS = {
    "tall": "tall", "towering": "tall", "lanky": "thin", "gaunt": "thin", "thin": "thin", "slender": "thin",
    "slim": "thin", "lean": "thin", "spare": "thin", "stout": "stout", "fat": "stout", "plump": "stout",
    "portly": "stout", "corpulent": "stout", "burly": "stout", "stocky": "stout", "short": "short",
    "small": "short", "little": "short", "diminutive": "short",
}
PERSON_NOUN = r"(?:man|woman|lady|gentleman|girl|boy|fellow|figure|person|creature|child|youth)"
BUILD_NEAR_NOUN = re.compile(rf"\b({'|'.join(BUILD_WORDS)})(?:,? \w+)? {PERSON_NOUN}\b", re.IGNORECASE)
BODY_NOUN = r"(?:figure|frame|form|person|stature|body|shape|build)"
FACE_NOUN = r"(?:face|cheeks?|skin|complexion|countenance|features)"
# after a possessive the adjective must describe the body ("his tall figure"), not a thing
# ("her little sister", "his thin hands"); after the name it describes the person ("X was tall"),
# except "little" and "small", which need a person noun ("a little man")
BUILD_BODY = re.compile(rf"\b({'|'.join(BUILD_WORDS)})(?:,? \w+)? {BODY_NOUN}\b", re.IGNORECASE)
BUILD = re.compile(rf"\b({'|'.join(w for w in BUILD_WORDS if w not in ('little', 'small'))})\b", re.IGNORECASE)
COMPLEXION = {
    "pale": re.compile(r"\b(pale|pallid|sallow|wan|white-faced|ashen)\b", re.IGNORECASE),
    "ruddy": re.compile(r"\b(ruddy|red-faced|florid|rosy|weather-beaten)\b", re.IGNORECASE),
    "dark": re.compile(r"\b(swarthy|tanned|sunburnt|sun-burnt|brown-skinned|dark-skinned|dark complexion)\b",
                       re.IGNORECASE),
}
HAIRSTYLE = {
    "curly": re.compile(r"\b(curly|curling|curls|ringlets|frizzled)\b", re.IGNORECASE),
    "bald": re.compile(r"\b(bald|bald-headed|baldness)\b", re.IGNORECASE),
    "long": re.compile(r"\blong (?:\w+ )?(?:hair|locks|tresses)\b", re.IGNORECASE),
}
MARKS = {
    "scar": re.compile(r"\b(scar|scarred)\b", re.IGNORECASE),
    "eyepatch": re.compile(r"\b(eye-?patch|patch over (?:his|her|one) eye|one-eyed)\b", re.IGNORECASE),
    "pipe": re.compile(r"\b(pipe)\b", re.IGNORECASE),
    "moustache": re.compile(r"\b(moustache|mustache|moustaches)\b", re.IGNORECASE),
    "freckles": re.compile(r"\b(freckled|freckles)\b", re.IGNORECASE),
}
_AGE_NUMBERS = {"ten": 10, "twelve": 12, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
                "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
                "eighty": 80, "ninety": 90}
YEARS_OLD = re.compile(rf"\b(?:of|aged|about|nearly|past|over) (\d{{1,2}}|{'|'.join(_AGE_NUMBERS)})\b"
                       rf"|\b(\d{{1,2}}|{'|'.join(_AGE_NUMBERS)})(?:[- ]\w+)? years? (?:old|of age)\b", re.IGNORECASE)
POSSESSIVE = {"his", "her", "their"}
LINK = re.compile(r"^\s*(?:,\s*(?:a|an|the)\s|\s+(?:was|is|looked|seemed|appeared|grew|became|had)\s)", re.IGNORECASE)


@dataclass
class Clues:
    """The words attached to one character, by how sure we are that they are about them."""
    by_name: list[str] = field(default_factory=list)  # after "Darcy's" (sure)
    by_pronoun: list[str] = field(default_factory=list)  # after a linked "his"/"her" (right ~3 times in 4)
    named: list[str] = field(default_factory=list)  # after the name, describing them: "Collins was tall" (sure)


def _attached(analysis: BookAnalysis, character_id: int) -> Clues:
    """The few words that hang off each mention of the character: after a possessive
    ("his ...", "her ...", "Darcy's ..."), or after the name when it is described ("X, a ...",
    "X was ..."). Short windows, so a description of someone else later in the sentence is not read."""
    clues = Clues()
    for m in analysis.mentions:
        if m.character_id != character_id:
            continue
        s = analysis.sentences[m.sentence_index]
        after = s.text[max(0, m.end - s.start):]
        by_pronoun = m.text.lower() in POSSESSIVE
        by_name = after.startswith(("'s", "’s"))
        if not (by_pronoun or by_name or (m.source == "name" and LINK.match(after))):
            continue
        words = after.removeprefix("'s").removeprefix("’s").split()[:WINDOW_WORDS]
        # stop at the next person: "her sister's blue eyes" are the sister's
        cut = next((i for i, w in enumerate(words) if w.lower().rstrip(",.;") in ("and", "but") or "'s" in w), None)
        window = " ".join(words[:cut])
        (clues.by_pronoun if by_pronoun else clues.by_name if by_name else clues.named).append(window)
    return clues


def _vote(sure: Counter, unsure: Counter, need: int = 2) -> tuple[str, int] | None:
    """The winning value: one sure clue or `need` unsure ones, and clearly ahead of the rest
    (a sure clue weighs twice as much as an unsure one)."""
    total = unsure + sure + sure
    if not total:
        return None
    (best, n), *rest = total.most_common()
    if (sure[best] or unsure[best] >= need) and (not rest or n >= 2 * rest[0][1]):
        return best, sure[best] + unsure[best]
    return None


def _tally(pattern_or_map, texts: list[str], key=None) -> Counter:
    """How often each value is found in the texts (a {value: pattern} map, or one pattern + key)."""
    found = Counter()
    for t in texts:
        if isinstance(pattern_or_map, dict):
            found.update(name for name, p in pattern_or_map.items() if p.search(t))
        else:
            found.update(key(m) for m in pattern_or_map.finditer(t))
    return found


def add_traits(look: "Appearance", clues: Clues, solo: list[str]) -> None:
    """Eyes, build, complexion, hair style, marks and age in years. Sure clues: words attached to
    the character's name. Unsure clues: words after a linked pronoun, and sentences about them alone."""
    owned_sure, owned_unsure = clues.by_name, clues.by_pronoun
    sure, unsure = owned_sure + clues.named, owned_unsure + solo

    eye = lambda m: EYE_COLOUR.get((m.group(1) or m.group(2)).lower(), (m.group(1) or m.group(2)).lower())
    if vote := _vote(_tally(EYES, sure, eye), _tally(EYES, unsure, eye)):
        look.eyes = vote[0]
        look.evidence.append(f"{vote[0]} eyes ×{vote[1]}")

    build = lambda m: BUILD_WORDS[m.group(1).lower()]
    if vote := _vote(_tally(BUILD_BODY, owned_sure, build) + _tally(BUILD, clues.named, build)
                     + _tally(BUILD_NEAR_NOUN, clues.named, build),
                     _tally(BUILD_BODY, owned_unsure, build) + _tally(BUILD_NEAR_NOUN, solo, build)):
        look.build = vote[0]
        look.evidence.append(f"{vote[0]} ×{vote[1]}")

    on_face = {k: re.compile(p.pattern + rf"(?: \w+)? {FACE_NOUN}", re.IGNORECASE) for k, p in COMPLEXION.items()}
    if vote := _vote(_tally(on_face, owned_sure) + _tally(COMPLEXION, clues.named),
                     _tally(on_face, owned_unsure + solo)):
        look.complexion = vote[0]
        look.evidence.append(f"{vote[0]} complexion ×{vote[1]}")

    if vote := _vote(_tally(HAIRSTYLE, sure), _tally(HAIRSTYLE, unsure)):
        look.hairstyle = vote[0]
        look.evidence.append(f"{vote[0]} hair ×{vote[1]}")

    # marks and belongings are read only from attached words ("his pipe"), never from whole
    # sentences (a pipe smoked by someone else in the room): one sure clue or three unsure ones
    sure_marks, unsure_marks = _tally(MARKS, sure), _tally(MARKS, owned_unsure)
    for mark in sure_marks | unsure_marks:
        look.mark_scores[mark] = 2 * sure_marks[mark] + unsure_marks[mark]
        if sure_marks[mark] or unsure_marks[mark] >= 3:
            look.features.add(mark)
            look.evidence.append(f"{mark} ×{sure_marks[mark] + unsure_marks[mark]}")
            if not sure_marks[mark]:
                look.unsure_marks[mark] = unsure_marks[mark]

    years = [int(v) if v.isdigit() else _AGE_NUMBERS[v.lower()]
             for t in sure + owned_unsure for m in YEARS_OLD.finditer(t) for v in m.groups() if v]
    if years:
        age = sorted(years)[len(years) // 2]
        look.years = age
        # a teenager mentioned once may grow up in the book (Heathcliff "aged 16"): only a child is drawn young
        look.age = "young" if age < 16 else "old" if age >= 55 else look.age
        look.evidence.append(f"aged {age}")


def standout_emotion(analysis: BookAnalysis, character_id: int, lift: float = 1.15) -> str | None:
    """The emotion family that is most above the book's average around this character (for the
    face's expression), or None when none clearly is."""
    if not analysis.character_emotions or character_id >= len(analysis.character_emotions):
        return None
    theirs = {e: v for e, v in analysis.character_emotions[character_id].items() if e != "neutral"}
    book = average_emotions([s.emotions for s in analysis.sentences])
    ratios = {e: v / max(book.get(e, 0.0), 1e-6) for e, v in theirs.items() if v >= 0.02}
    if not ratios:
        return None
    best = max(ratios, key=ratios.get)
    return best if ratios[best] >= lift else None
