"""Draw a portrait avatar for a character, as a small SVG picture.

The look comes from analyzer.appearance (what the book says, plus what the
story implies). Anything still unknown (skin tone, hair colour, coat colour,
a hat or bonnet) is picked from period-appropriate options using the
character's name as the seed, so a character always looks the same.
The avatar sits on a dark round badge with a ring in the character's colour.
"""

import base64
import hashlib

import charts
from analyzer.appearance import Appearance, describe
from analyzer.models import BookAnalysis

SKIN = ["#f3d3b8", "#eac1a0", "#dcaa86", "#c98f6a"]
HAIR = {"black": "#2a2220", "dark": "#3d2b22", "brown": "#6b4a32", "fair": "#d6b06e", "golden": "#dfae45",
        "red": "#a5452a", "auburn": "#8a3a22", "sandy": "#c39a60", "grey": "#9c9a95", "white": "#e7e3da"}
YOUTHFUL_HAIR = ["dark", "brown", "black", "fair", "auburn", "brown", "dark"]
COATS = ["#2c3e5c", "#2f4a3a", "#5a3f2c", "#23262c", "#5b2733"]  # navy, bottle green, brown, black, claret
DRESSES = ["#a9636b", "#6b4a6e", "#3f6f73", "#a98439", "#5f7fa8"]  # rose, plum, teal, mustard, blue
CLOAKS = ["#4a5a3a", "#5a4a36", "#3e4a56", "#5b3a3a"]
INK = "#2a211c"


def _pick(seed: int, options: list, salt: int = 0):
    return options[(seed // (salt * 7 + 1)) % len(options)]


SKIN_BY_COMPLEXION = {"pale": "#f6e0cf", "ruddy": "#eab69a", "dark": "#b47b56"}
IRIS = {"blue": "#4f86c6", "grey": "#8c97a3", "green": "#5d8f5a", "hazel": "#8f7a3c", "brown": "#6b4630",
        "dark": "#3b2a20", "black": "#231a15"}
# eye colours that go with each hair colour, for when the book doesn't say
LIKELY_EYES = {"fair": ["blue", "grey", "blue"], "golden": ["blue", "blue", "green"], "sandy": ["blue", "grey", "hazel"],
               "red": ["green", "hazel", "blue"], "auburn": ["hazel", "green", "brown"]}


def _face_width(look: Appearance) -> float:
    return {"stout": 22, "thin": 17.5}.get(look.build or "", 19.5)


def _expression(look: Appearance, lips: str, brow: str, iris: str, skin: str) -> str:
    """Eyes, brows and mouth set by the emotion that stands out around the character
    (else by their overall mood): the face tells the reader how the book treats them."""
    feel = look.emotion or ("joy" if look.mood > 0.08 else "sadness" if look.mood < -0.05 else "")
    out = []
    # eyes: white, iris in the book's colour, pupil; wide for fear and surprise, cast down for shame
    wide = feel in ("fear", "surprise")
    down = 1.2 if feel == "shame" else 0
    ry = 3.2 if wide else 2.6
    for x in (52, 68):
        out.append(f'<ellipse cx="{x}" cy="50" rx="3.4" ry="{ry}" fill="#fbf8f2"/>'
                   f'<circle cx="{x}" cy="{50 + down:.1f}" r="2.1" fill="{iris}"/>'
                   f'<circle cx="{x}" cy="{50 + down:.1f}" r="1" fill="{INK}"/>'
                   f'<circle cx="{x + .7:.1f}" cy="{49.3 + down:.1f}" r=".55" fill="#fff"/>')
        if feel == "joy":  # smiling eyes: the lower lid pushes up
            out.append(f'<path d="M{x - 3.6} 52.4 Q{x} 50.2 {x + 3.6} 52.4 L{x + 3.6} 54 L{x - 3.6} 54 Z" fill="{skin}"/>')
        if feel == "shame" or feel == "sadness":  # heavy upper lids
            out.append(f'<path d="M{x - 3.6} 47 L{x + 3.6} 47 L{x + 3.6} 49 Q{x} 47.6 {x - 3.6} 49 Z" fill="{skin}"/>')
    # brows: (inner end y, outer end y) for each side
    left, right = {
        "sadness": ((41.5, 44.5), (41.5, 44.5)), "fear": ((41, 43.5), (41, 43.5)),
        "anger": ((46.5, 42.5), (46.5, 42.5)), "surprise": ((40.5, 41.5), (40.5, 41.5)),
        "disapproval": ((44.5, 44.5), (41.5, 40.5)), "shame": ((43, 45), (43, 45)),
    }.get(feel, ((44, 44.5), (44, 44.5)))
    width = 2.6 if look.gender != "f" else 1.8
    out.append(f'<path d="M47 {left[1]} Q51.5 {min(left) - .8} 56 {left[0]}" fill="none" stroke="{brow}" '
               f'stroke-width="{width}" stroke-linecap="round"/>'
               f'<path d="M64 {right[0]} Q68.5 {min(right) - .8} 73 {right[1]}" fill="none" stroke="{brow}" '
               f'stroke-width="{width}" stroke-linecap="round"/>')
    # mouth
    mouths = {
        "joy": "M52.5 64.5 Q60 72.5 67.5 64.5", "love": "M54 65.5 Q60 70 66 65.5",
        "sadness": "M54 68.5 Q60 64 66 68.5", "anger": "M54.5 67 L65.5 67", "shame": "M55 67.5 Q60 66 65 67.5",
        "disapproval": "M54.5 67.5 Q60 67.5 66 64.8",
    }
    if feel == "surprise":
        out.append(f'<ellipse cx="60" cy="67" rx="3.2" ry="3.8" fill="#5a2a2a" stroke="{lips}" stroke-width="1.2"/>')
    elif feel == "fear":  # worry, not shock: a tight, uneven mouth under raised brows
        out.append(f'<path d="M54.5 67.5 Q57 66 60 67.3 Q63 68.6 65.5 67" fill="none" stroke="{lips}" '
                   f'stroke-width="2" stroke-linecap="round"/>')
    else:
        out.append(f'<path d="{mouths.get(feel, "M54.5 66.5 Q60 68 65.5 66.5")}" fill="none" stroke="{lips}" '
                   f'stroke-width="2.2" stroke-linecap="round"/>')
    if feel in ("love", "shame") or look.complexion == "ruddy":  # a blush
        out.append('<circle cx="48" cy="59.5" r="4.6" fill="#e0606a" opacity=".3"/>'
                   '<circle cx="72" cy="59.5" r="4.6" fill="#e0606a" opacity=".3"/>')
    return "".join(out)


def _nose(seed: int) -> str:
    """One of three noses, by name: a small curve, a straight nose, a rounder one."""
    return _pick(seed, [
        '<path d="M60 52 Q57.5 59 61 60.5" fill="none" stroke="#000" stroke-opacity=".28" stroke-width="1.4" stroke-linecap="round"/>',
        '<path d="M60.5 51 L58.6 59.6 L61.8 60.2" fill="none" stroke="#000" stroke-opacity=".28" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>',
        '<path d="M57 59.5 Q60 62.5 63 59.5" fill="none" stroke="#000" stroke-opacity=".28" stroke-width="1.5" stroke-linecap="round"/>',
    ], 5)


def avatar_svg(name: str, look: Appearance, ring: str) -> str:
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    woman, old, young = look.gender == "f", look.age == "old", look.age == "young"
    role, world = look.role, look.world
    skin = SKIN_BY_COMPLEXION.get(look.complexion or "", _pick(seed, SKIN))
    hair_name = look.hair or (_pick(seed, ["grey", "white", "grey"], 1) if old else _pick(seed, YOUTHFUL_HAIR, 2))
    if role == "wizard":
        hair_name = look.hair or "grey"
    hair = HAIR[hair_name]
    iris = IRIS[look.eyes or _pick(seed, LIKELY_EYES.get(hair_name, ["brown", "dark", "brown", "grey"]), 4)]
    face_rx = _face_width(look) + (1 if role == "hobbit" else 0)
    parts: list[str] = []
    add = parts.append

    # --- behind the head: long hair, veil
    if "bride" in look.features:
        add('<path d="M30 44 Q60 4 90 44 L104 120 L16 120 Z" fill="#f4f1ea" opacity=".55"/>')
    if woman or role == "elf" or (look.hairstyle == "long" and not woman):
        add(f'<path d="M36 50 Q34 18 60 18 Q86 18 84 50 Q88 74 80 86 L40 86 Q32 74 36 50 Z" fill="{hair}"/>')
        if woman and world == "period" and not old and look.hairstyle != "long":  # 19th-century ringlets
            for y in (62, 70, 78):
                add(f'<circle cx="38" cy="{y}" r="4.2" fill="{hair}"/><circle cx="82" cy="{y}" r="4.2" fill="{hair}"/>')

    # --- clothes
    add(_clothes(seed, look))

    # --- neck and head
    add(f'<rect x="52" y="64" width="16" height="20" rx="6" fill="{skin}"/>'
        f'<rect x="52" y="64" width="16" height="9" fill="#000" opacity=".08"/>')
    if role == "elf":
        add(f'<path d="M40 50 L30 38 L42 56 Z M80 50 L90 38 L78 56 Z" fill="{skin}"/>')
    else:
        ear = 60 - face_rx - .2
        add(f'<ellipse cx="{ear:.1f}" cy="54" rx="4" ry="6" fill="{skin}"/>'
            f'<ellipse cx="{120 - ear:.1f}" cy="54" rx="4" ry="6" fill="{skin}"/>')
    add(f'<ellipse cx="60" cy="50" rx="{face_rx}" ry="{22 if role == "hobbit" else 24}" fill="{skin}"/>')
    if look.build == "stout":  # a fuller jaw
        add(f'<path d="M48 70 Q60 78 72 70" fill="none" stroke="#000" stroke-opacity=".12" stroke-width="1.4"/>')
    elif look.build == "thin":  # cheekbones
        add('<path d="M45 57 Q47 63 50 64 M75 57 Q73 63 70 64" fill="none" stroke="#000" stroke-opacity=".13" stroke-width="1.2"/>')

    # --- face: freckles, eyes, brows, nose, mouth
    if "freckles" in look.features:
        add("".join(f'<circle cx="{x}" cy="{y}" r=".7" fill="#a0583a" opacity=".55"/>'
                    for x, y in ((47, 57), (50, 58.5), (48.5, 60), (73, 57), (70, 58.5), (71.5, 60), (57, 56), (63, 56))))
    lips = "#b4535c" if woman else "#8f4c42"
    brow = HAIR["grey"] if old else (hair if hair_name not in ("fair", "golden", "white") else "#8a6a48")
    add(_expression(look, lips, brow, iris, skin))
    add(_nose(seed))
    if old:
        add('<path d="M50 38 Q60 35 70 38 M52 41.5 Q60 39.5 68 41.5 M45 56 Q46 60 48 61 M75 56 Q74 60 72 61" '
            'fill="none" stroke="#000" stroke-opacity=".16" stroke-width="1"/>')
    if "scar" in look.features:
        add('<path d="M70 53 L76 61 M71.5 55.5 L73.5 54.5 M73 58 L75 57" stroke="#9b4a43" stroke-width="1.1" '
            'stroke-linecap="round" opacity=".8"/>')

    # --- facial hair (men): wizard beard, beard, whiskers, moustache, or a period moustache by chance
    if not woman:
        beard = role in ("wizard", "dwarf") or "beard" in look.features
        if beard:
            long = role == "wizard"
            add(f'<path d="M41 54 Q42 {96 if long else 80} 60 {108 if long else 84} Q78 {96 if long else 80} 79 54 '
                f'Q74 70 60 70 Q46 70 41 54 Z" fill="{hair}"/>'
                f'<path d="M53 66 Q60 63 67 66" fill="none" stroke="{lips}" stroke-width="2" stroke-linecap="round"/>')
        elif "whiskers" in look.features or (world == "period" and not young and not look.features & {"moustache"}
                                             and seed % 3 == 0):
            add(f'<path d="M40 48 Q38 64 46 70 L48 60 Q44 56 44 48 Z M80 48 Q82 64 74 70 L72 60 Q76 56 76 48 Z" fill="{hair}"/>')
        if "moustache" in look.features and not beard:
            add(f'<path d="M52.5 63.5 Q56 60.5 60 62.5 Q64 60.5 67.5 63.5 Q64 63.8 60 64 Q56 63.8 52.5 63.5 Z" fill="{hair}"/>')

    # --- hair on top
    add(_top_hair(seed, look, hair, woman, old, young))

    # --- accessories
    if "glasses" in look.features:
        add(f'<circle cx="52" cy="50" r="5.5" fill="none" stroke="#c9a54a" stroke-width="1.4"/>'
            f'<circle cx="68" cy="50" r="5.5" fill="none" stroke="#c9a54a" stroke-width="1.4"/>'
            '<path d="M57.5 50 L62.5 50" stroke="#c9a54a" stroke-width="1.4"/>')
    if "eyepatch" in look.features:
        add(f'<path d="M40 41 L80 56" stroke="{INK}" stroke-width="1.2"/>'
            f'<ellipse cx="68" cy="50" rx="5.2" ry="4.6" fill="{INK}"/>')
    if "pipe" in look.features:
        add('<path d="M64 67 L76 71" stroke="#4a2f1f" stroke-width="2.2" stroke-linecap="round"/>'
            '<path d="M74 66 L80 66 L79 74 Q77 76 75 74 Z" fill="#5a3a26"/>'
            '<path d="M77 63 Q75 60 78 57 Q81 54 78 51" fill="none" stroke="#d8d4cc" stroke-width="1.2" opacity=".6"/>')
    add(_headwear(seed, look, woman, young))

    body = "".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="240" height="240">'
            f'<defs><clipPath id="c"><circle cx="60" cy="60" r="55"/></clipPath></defs>'
            f'<circle cx="60" cy="60" r="58" fill="#1a2130"/>'
            f'<g clip-path="url(#c)"><g transform="translate(60 66) scale(1.12) translate(-60 -60)">{body}</g></g>'
            f'<circle cx="60" cy="60" r="56.5" fill="none" stroke="{ring}" stroke-width="5"/></svg>')


def _clothes(seed: int, look: Appearance) -> str:
    role, woman, world = look.role, look.gender == "f", look.world
    w = {"stout": 8, "thin": -6}.get(look.build or "", 0)  # broader or narrower shoulders
    shoulders = f"M{12 - w} 120 C{14 - w} 94 {34 - w / 2} 84 60 84 C{86 + w / 2} 84 {106 + w} 94 {108 + w} 120 Z"
    if "bride" in look.features:
        return (f'<path d="{shoulders}" fill="#efe9dc"/>'
                '<path d="M40 88 Q60 102 80 88" fill="none" stroke="#fff" stroke-width="3" stroke-dasharray="2 2"/>')
    if role == "wizard":
        return f'<path d="{shoulders}" fill="#7b8088"/><path d="M60 84 L60 120" stroke="#5c6168" stroke-width="2"/>'
    if role in ("elf", "royal"):
        robe = "#6d7f74" if role == "elf" else "#5b2f6e"
        return (f'<path d="{shoulders}" fill="{robe}"/>'
                '<path d="M44 86 Q60 98 76 86" fill="none" stroke="#d8c27a" stroke-width="2.5"/>')
    if role == "hobbit":
        return (f'<path d="{shoulders}" fill="#4f6b3a"/><path d="M48 86 L60 120 L72 86 Z" fill="#c9a24a"/>'
                '<circle cx="60" cy="102" r="1.6" fill="#7a5a20"/><circle cx="60" cy="110" r="1.6" fill="#7a5a20"/>')
    if role == "dwarf":
        return f'<path d="{shoulders}" fill="#6a4a30"/><path d="M30 104 L90 104" stroke="#3a2a1c" stroke-width="5"/>'
    if role == "ranger" or (world == "fantasy" and not role):
        cloak = _pick(seed, CLOAKS)
        return (f'<path d="{shoulders}" fill="{cloak}"/><circle cx="60" cy="90" r="3.5" fill="#c9a54a"/>'
                f'<path d="M48 86 L60 90 L72 86" fill="none" stroke="#000" stroke-opacity=".25" stroke-width="2"/>')
    if role == "blacksmith":
        return (f'<path d="{shoulders}" fill="#e8e1d2"/>'
                '<path d="M40 94 L80 94 L86 120 L34 120 Z" fill="#5c3b25"/>'
                '<path d="M44 94 L52 84 M76 94 L68 84" stroke="#5c3b25" stroke-width="3"/>')
    if role == "soldier":
        return (f'<path d="{shoulders}" fill="#a3262a"/>'
                '<ellipse cx="30" cy="94" rx="9" ry="3.5" fill="#d9b44a"/><ellipse cx="90" cy="94" rx="9" ry="3.5" fill="#d9b44a"/>'
                '<circle cx="60" cy="98" r="1.8" fill="#d9b44a"/><circle cx="60" cy="108" r="1.8" fill="#d9b44a"/>')
    if role == "clergy":
        return f'<path d="{shoulders}" fill="#1f2227"/><rect x="54" y="82" width="12" height="6" rx="2" fill="#f1efe9"/>'
    if role == "convict":
        return (f'<path d="{shoulders}" fill="#7a7a74"/>'
                '<path d="M30 100 L90 100 M26 110 L94 110" stroke="#5f5f5a" stroke-width="3"/>')
    if role in ("maid", "servant") and woman:
        return (f'<path d="{shoulders}" fill="#33343a"/><path d="M46 90 L74 90 L76 120 L44 120 Z" fill="#f1efe9"/>')
    if woman:
        dress = "#3d3f4a" if role == "teacher" else _pick(seed, DRESSES, 3)
        return (f'<path d="{shoulders}" fill="{dress}"/>'
                '<path d="M42 88 Q60 101 78 88" fill="none" stroke="#f4efe4" stroke-width="2.5" stroke-dasharray="3 1.5"/>')
    if world == "modern":
        return f'<path d="{shoulders}" fill="{_pick(seed, COATS, 3)}"/><path d="M50 84 L60 94 L70 84" fill="#e8e6e0"/>'
    coat = "#23262c" if role in ("lawyer", "clerk", "doctor") else _pick(seed, COATS, 3)
    # a period gentleman: dark coat, lapels, white cravat
    return (f'<path d="{shoulders}" fill="{coat}"/>'
            '<path d="M48 84 L60 104 L72 84 Z" fill="#f1efe9"/>'
            '<path d="M56 86 Q60 92 64 86 L62 96 L58 96 Z" fill="#e2ddd0"/>'
            '<path d="M46 86 L56 106 M74 86 L64 106" stroke="#000" stroke-opacity=".35" stroke-width="2"/>')


def _top_hair(seed: int, look: Appearance, hair: str, woman: bool, old: bool, young: bool) -> str:
    role = look.role
    if role in ("wizard", "dwarf"):
        return ""  # covered by the hat or helmet
    if woman or role == "elf":  # parted in the middle, smooth over the top
        return (f'<path d="M40 48 Q38 24 60 24 Q82 24 80 48 Q74 34 60 32 Q46 34 40 48 Z" fill="{hair}"/>'
                '<path d="M60 25 L60 33" stroke="#000" stroke-opacity=".2" stroke-width="1.2"/>')
    if role == "hobbit":  # curls
        return "".join(f'<circle cx="{x}" cy="{y}" r="5.5" fill="{hair}"/>'
                       for x, y in ((44, 34), (52, 28), (60, 26), (68, 28), (76, 34), (41, 42), (79, 42)))
    if look.hairstyle == "bald" or (old and seed % 2 == 0):  # bald or receding: hair only at the sides
        return f'<path d="M40 50 Q39 36 46 34 L46 46 Z M80 50 Q81 36 74 34 L74 46 Z" fill="{hair}"/>'
    if look.hairstyle == "curly":  # a head of curls
        return "".join(f'<circle cx="{x}" cy="{y}" r="5.8" fill="{hair}"/>'
                       for x, y in ((42, 40), (46, 31), (54, 26), (62, 25), (70, 27), (77, 33), (79, 42), (50, 32), (66, 31)))
    if young:  # a boyish fringe
        return f'<path d="M40 46 Q40 22 60 23 Q80 22 80 46 L74 36 L68 40 L62 34 L56 40 L50 35 L44 42 Z" fill="{hair}"/>'
    return f'<path d="M40 48 Q39 24 60 24 Q81 24 80 46 Q78 34 64 33 Q52 33 46 38 Q42 41 40 48 Z" fill="{hair}"/>'


def _headwear(seed: int, look: Appearance, woman: bool, young: bool) -> str:
    role, world = look.role, look.world
    if role == "wizard":
        return ('<path d="M60 2 L82 34 L38 34 Z" fill="#6d727a"/>'
                '<ellipse cx="60" cy="34" rx="34" ry="6" fill="#5c6168"/>')
    if role == "dwarf":
        return '<path d="M38 40 Q38 18 60 18 Q82 18 82 40 Z" fill="#8a8f96"/><rect x="38" y="38" width="44" height="4" fill="#6c7178"/>'
    if role == "royal":
        return '<path d="M42 30 L42 18 L50 24 L60 14 L70 24 L78 18 L78 30 Z" fill="#d9b44a"/>'
    if role == "ranger":
        return '<path d="M34 54 Q32 14 60 14 Q88 14 86 54 L80 54 Q80 24 60 24 Q40 24 40 54 Z" fill="#3a4a32"/>'
    if role in ("maid", "servant") and woman:
        return '<ellipse cx="60" cy="27" rx="17" ry="6" fill="#f1efe9"/>'
    if world != "period" or young or "bride" in look.features:
        return ""
    if woman and seed % 3 == 0:  # a bonnet
        return ('<path d="M34 52 Q30 16 60 16 Q90 16 86 52 L80 50 Q80 26 60 26 Q40 26 40 50 Z" fill="#c9b48a"/>'
                # the ribbon follows the jaw and ties under the chin (never across the face)
                '<path d="M39.5 52 Q42 72 60 76 Q78 72 80.5 52" fill="none" stroke="#a8433f" stroke-width="2"/>'
                '<path d="M60 76 L55 81 M60 76 L65 81" stroke="#a8433f" stroke-width="2" stroke-linecap="round"/>')
    if not woman and look.hairstyle != "bald" and (seed % 3 == 1 or role in ("lawyer", "doctor")):  # a top hat
        return ('<rect x="45" y="11" width="30" height="19" rx="2" fill="#1d1f24"/>'
                '<rect x="45" y="25" width="30" height="3.5" fill="#5b2733"/>'
                '<ellipse cx="60" cy="30" rx="24" ry="4.2" fill="#1d1f24"/>')
    return ""


ROLE_WORDS = {
    "blacksmith": "Blacksmith", "lawyer": "Lawyer", "clerk": "Clerk", "convict": "Convict", "soldier": "Soldier",
    "clergy": "Clergyman", "doctor": "Doctor", "maid": "Maid", "servant": "Servant", "sailor": "Sailor",
    "teacher": "Teacher", "royal": "Royalty", "wizard": "Wizard", "hobbit": "Hobbit", "elf": "Elf", "dwarf": "Dwarf",
    "ranger": "Ranger",
}
FEATURE_WORDS = {"bride": "bridal veil", "glasses": "spectacles", "beard": "beard", "whiskers": "whiskers",
                 "moustache": "moustache", "freckles": "freckles", "scar": "a scar", "eyepatch": "an eye patch",
                 "pipe": "a pipe"}


def look_in_words(look: Appearance) -> str:
    """e.g. "Old · grey hair · bridal veil" (what the avatar shows, in words)."""
    words = []
    if look.role:
        words.append(ROLE_WORDS.get(look.role, look.role.title()))
    if look.age != "adult":
        words.append(look.age.title() if not words else look.age)
    if look.hair:
        words.append(f"{look.hair} hair")
    if look.years:
        words.append(f"about {look.years}")
    if look.build:
        words.append(look.build)
    if look.complexion:
        words.append(f"{look.complexion} complexion")
    if look.hairstyle:
        words.append(f"{look.hairstyle} hair" if not look.hair else "")
        if look.hair:  # "curly fair hair" in one
            words[words.index(f"{look.hair} hair")] = f"{look.hairstyle} {look.hair} hair"
    if look.eyes:
        words.append(f"{look.eyes} eyes")
    words = [w for w in words if w]
    words += [FEATURE_WORDS.get(f, f) for f in sorted(look.features)]
    if words:
        return " · ".join(words)
    # nothing from the book: say what the drawing assumed from the story's world
    who = {"m": "gentleman", "f": "lady"}.get(look.gender, "figure")
    if look.world == "fantasy":
        who = {"m": "traveller", "f": "lady"}.get(look.gender, "traveller")
    return f"{'Young ' if look.age == 'young' else ''}{'Period ' if look.world == 'period' else ''}{who}".capitalize()


def cast_avatars(analysis: BookAnalysis, theme: dict) -> tuple[dict[int, Appearance], dict[int, str]]:
    """The main characters' looks and avatars ({id: data URI}), rings in this theme's colours."""
    looks = describe(analysis)
    colors = charts.character_colors(analysis, theme)
    names = {c.id: c.name for c in analysis.characters}
    return looks, {cid: avatar_uri(names[cid], look, colors[cid]) for cid, look in looks.items()}


def avatar_uri(name: str, look: Appearance, ring: str) -> str:
    """The avatar as a data: URI, usable in <img src>, Plotly images and 3D textures."""
    return "data:image/svg+xml;base64," + base64.b64encode(avatar_svg(name, look, ring).encode()).decode()
