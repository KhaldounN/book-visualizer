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


def avatar_svg(name: str, look: Appearance, ring: str) -> str:
    seed = int(hashlib.md5(name.encode()).hexdigest()[:8], 16)
    woman, old, young = look.gender == "f", look.age == "old", look.age == "young"
    role, world = look.role, look.world
    skin = _pick(seed, SKIN)
    hair_name = look.hair or (_pick(seed, ["grey", "white", "grey"], 1) if old else _pick(seed, YOUTHFUL_HAIR, 2))
    if role == "wizard":
        hair_name = look.hair or "grey"
    hair = HAIR[hair_name]
    parts: list[str] = []
    add = parts.append

    # --- behind the head: long hair, veil
    if "bride" in look.features:
        add('<path d="M30 44 Q60 4 90 44 L104 120 L16 120 Z" fill="#f4f1ea" opacity=".55"/>')
    if woman or role == "elf":
        add(f'<path d="M36 50 Q34 18 60 18 Q86 18 84 50 Q88 74 80 86 L40 86 Q32 74 36 50 Z" fill="{hair}"/>')
        if world == "period" and not old:  # 19th-century ringlets at the sides
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
        add(f'<ellipse cx="39.5" cy="54" rx="4" ry="6" fill="{skin}"/><ellipse cx="80.5" cy="54" rx="4" ry="6" fill="{skin}"/>')
    face_ry = 22 if role == "hobbit" else 24
    add(f'<ellipse cx="60" cy="50" rx="{20.5 if role == "hobbit" else 19.5}" ry="{face_ry}" fill="{skin}"/>')

    # --- face
    mood = look.mood
    if woman or young:
        add('<circle cx="49" cy="60" r="4" fill="#e0707a" opacity=".22"/><circle cx="71" cy="60" r="4" fill="#e0707a" opacity=".22"/>')
    add(f'<ellipse cx="52" cy="50" rx="2.3" ry="2.7" fill="{INK}"/><ellipse cx="68" cy="50" rx="2.3" ry="2.7" fill="{INK}"/>'
        '<circle cx="52.8" cy="49.2" r=".8" fill="#fff"/><circle cx="68.8" cy="49.2" r=".8" fill="#fff"/>')
    brow = HAIR["grey"] if old else (hair if hair_name not in ("fair", "golden", "white") else "#8a6a48")
    # inner ends of the brows raised = sad or worried (a dark character); relaxed otherwise
    lift = 2.4 if mood < -0.05 else 0.6 if mood > 0.08 else 0
    add(f'<path d="M47 44 L56 {44 - lift}" stroke="{brow}" stroke-width="2" stroke-linecap="round"/>'
        f'<path d="M64 {44 - lift} L73 44" stroke="{brow}" stroke-width="2" stroke-linecap="round"/>')
    add('<path d="M60 52 Q57.5 59 61 60.5" fill="none" stroke="#000" stroke-opacity=".28" stroke-width="1.4" stroke-linecap="round"/>')
    lips = "#b4535c" if woman else "#8f4c42"
    if mood > 0.05:
        mouth = "M53 65 Q60 71 67 65"
    elif mood < -0.05:
        mouth = "M54 68 Q60 64.5 66 68"
    else:
        mouth = "M54.5 66.5 Q60 68 65.5 66.5"
    add(f'<path d="{mouth}" fill="none" stroke="{lips}" stroke-width="2.2" stroke-linecap="round"/>')
    if old:
        add('<path d="M50 38 Q60 35 70 38 M52 41.5 Q60 39.5 68 41.5 M45 56 Q46 60 48 61 M75 56 Q74 60 72 61" '
            'fill="none" stroke="#000" stroke-opacity=".16" stroke-width="1"/>')

    # --- facial hair (men): wizard beard, beard, whiskers, or a period moustache by chance
    if not woman:
        beard = role in ("wizard", "dwarf") or "beard" in look.features
        if beard:
            long = role == "wizard"
            add(f'<path d="M41 54 Q42 {96 if long else 80} 60 {108 if long else 84} Q78 {96 if long else 80} 79 54 '
                f'Q74 70 60 70 Q46 70 41 54 Z" fill="{hair}"/>'
                f'<path d="M53 66 Q60 63 67 66" fill="none" stroke="{lips}" stroke-width="2" stroke-linecap="round"/>')
        elif "whiskers" in look.features or (world == "period" and not young and seed % 3 == 0):
            add(f'<path d="M40 48 Q38 64 46 70 L48 60 Q44 56 44 48 Z M80 48 Q82 64 74 70 L72 60 Q76 56 76 48 Z" fill="{hair}"/>')

    # --- hair on top
    add(_top_hair(seed, look, hair, woman, old, young))

    # --- accessories
    if "glasses" in look.features:
        add(f'<circle cx="52" cy="50" r="5.5" fill="none" stroke="#c9a54a" stroke-width="1.4"/>'
            f'<circle cx="68" cy="50" r="5.5" fill="none" stroke="#c9a54a" stroke-width="1.4"/>'
            '<path d="M57.5 50 L62.5 50" stroke="#c9a54a" stroke-width="1.4"/>')
    add(_headwear(seed, look, woman, young))

    body = "".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="240" height="240">'
            f'<defs><clipPath id="c"><circle cx="60" cy="60" r="55"/></clipPath></defs>'
            f'<circle cx="60" cy="60" r="58" fill="#1a2130"/>'
            f'<g clip-path="url(#c)"><g transform="translate(60 66) scale(1.12) translate(-60 -60)">{body}</g></g>'
            f'<circle cx="60" cy="60" r="56.5" fill="none" stroke="{ring}" stroke-width="5"/></svg>')


def _clothes(seed: int, look: Appearance) -> str:
    role, woman, world = look.role, look.gender == "f", look.world
    shoulders = "M12 120 C14 94 34 84 60 84 C86 84 106 94 108 120 Z"
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
    if old and seed % 2 == 0:  # receding: hair only at the sides
        return f'<path d="M40 50 Q39 36 46 34 L46 46 Z M80 50 Q81 36 74 34 L74 46 Z" fill="{hair}"/>'
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
                '<path d="M40 54 Q60 70 80 54" fill="none" stroke="#a8433f" stroke-width="2"/>')
    if not woman and (seed % 3 == 1 or role in ("lawyer", "doctor")):  # a top hat
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
FEATURE_WORDS = {"bride": "bridal veil", "glasses": "spectacles", "beard": "beard", "whiskers": "whiskers"}


def look_in_words(look: Appearance) -> str:
    """e.g. "Old · grey hair · bridal veil" (what the avatar shows, in words)."""
    words = []
    if look.role:
        words.append(ROLE_WORDS.get(look.role, look.role.title()))
    if look.age != "adult":
        words.append(look.age.title() if not words else look.age)
    if look.hair:
        words.append(f"{look.hair} hair")
    words += [FEATURE_WORDS[f] for f in sorted(look.features)]
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
