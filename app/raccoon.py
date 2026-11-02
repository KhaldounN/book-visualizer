"""Animated cartoon raccoon scenes, shown while a book is analyzed.

The raccoon (modelled on the owner's mascot photo: grey fur, black mask, ringed
tail, black headphones with orange cups) does something different at each
analysis step. Each scene is one SVG with CSS animations, so it plays like a
GIF inside an <img> without any image files or downloads.
"""

import base64

FUR, FUR_DARK, LIGHT, MASK, INK = "#8f9098", "#6e6f77", "#ecebf0", "#2a2a31", "#1d1d22"
DESK, PAPER, ACCENT = "#5b3f2b", "#f4efe2", "#ff8a2a"

STYLE = """
.wag { transform-origin: 0 0; animation: wag 1.6s ease-in-out infinite; }
.blink { transform-box: fill-box; transform-origin: center; animation: blink 4s infinite; }
.bob { animation: bob 1.8s ease-in-out infinite; }
.tap { transform-box: fill-box; transform-origin: top; animation: tap .5s ease-in-out infinite alternate; }
.tap2 { transform-box: fill-box; transform-origin: top; animation: tap .5s ease-in-out .25s infinite alternate; }
.scan { animation: scan 2.4s ease-in-out infinite; }
.flip { transform-box: fill-box; transform-origin: left; animation: flip 2.4s ease-in-out infinite; }
.pop1, .pop2, .pop3, .pop4 { transform-box: fill-box; transform-origin: center; opacity: 0; animation: pop 4s infinite; }
.pop2 { animation-delay: 1s; } .pop3 { animation-delay: 2s; } .pop4 { animation-delay: 3s; }
.write { animation: write 1s ease-in-out infinite; }
.lens { animation: lens 3s ease-in-out infinite; }
.arrow { stroke-dasharray: 60; animation: draw 3s ease-in-out infinite; }
.tilt { transform-origin: 268px 100px; animation: tilt 3s ease-in-out infinite; }
.rise1, .rise2, .rise3, .rise4 { opacity: 0; animation: rise 4s ease-in infinite; }
.rise2 { animation-delay: 1s; } .rise3 { animation-delay: 2s; } .rise4 { animation-delay: 3s; }
.tear { animation: tear 2s ease-in infinite; }
.stamp { animation: stamp 1.6s ease-in-out infinite; }
.ink1, .ink2, .ink3 { opacity: 0; animation: ink 4.8s infinite; }
.ink2 { animation-delay: 1.6s; } .ink3 { animation-delay: 3.2s; }
.thread1, .thread2, .thread3 { stroke-dasharray: 120; stroke-dashoffset: 120; animation: thread 4.5s ease-in-out infinite; }
.thread2 { animation-delay: 1.5s; } .thread3 { animation-delay: 3s; }
.glow { animation: glow 1.2s ease-in-out infinite alternate; }
@keyframes wag { 0%, 100% { transform: rotate(-10deg); } 50% { transform: rotate(10deg); } }
@keyframes blink { 0%, 94%, 100% { transform: scaleY(1); } 96% { transform: scaleY(.1); } }
@keyframes bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-3px); } }
@keyframes tap { from { transform: translateY(0); } to { transform: translateY(4px); } }
@keyframes scan { 0%, 100% { transform: translateX(-3px); } 50% { transform: translateX(3px); } }
@keyframes flip { 0%, 70% { transform: scaleX(1); } 85% { transform: scaleX(-1); } 100% { transform: scaleX(-1); } }
@keyframes pop { 0%, 8% { opacity: 0; transform: scale(.3); } 14%, 80% { opacity: 1; transform: scale(1); } 90%, 100% { opacity: 0; transform: scale(1); } }
@keyframes write { 0%, 100% { transform: translate(0, 0); } 25% { transform: translate(6px, -2px); } 50% { transform: translate(12px, 1px); } 75% { transform: translate(5px, 2px); } }
@keyframes lens { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(52px, 0); } }
@keyframes draw { 0%, 30% { stroke-dashoffset: 60; } 60%, 100% { stroke-dashoffset: 0; } }
@keyframes tilt { 0%, 100% { transform: rotate(-9deg); } 50% { transform: rotate(9deg); } }
@keyframes rise { 0% { opacity: 0; transform: translateY(0); } 15% { opacity: 1; } 100% { opacity: 0; transform: translateY(-70px); } }
@keyframes tear { 0%, 40% { opacity: 0; transform: translateY(0); } 50% { opacity: 1; } 100% { opacity: 0; transform: translateY(14px); } }
@keyframes stamp { 0%, 40%, 100% { transform: translateY(-14px); } 55%, 65% { transform: translateY(0); } }
@keyframes ink { 0%, 30% { opacity: 0; } 36%, 90% { opacity: 1; } 100% { opacity: 0; } }
@keyframes thread { 0% { stroke-dashoffset: 120; } 40%, 85% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: 120; } }
@keyframes glow { from { opacity: .35; } to { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; opacity: 1 !important; } }
"""


def _raccoon(arms: str = "type", eyes: str = "") -> str:
    """The raccoon at its desk. `arms`: type | write | hold | rest. `eyes`: an extra class (e.g. scan)."""
    tail = (f'<g transform="translate(205 150)"><g class="wag">'
            f'<path d="M0 0 C30 -10 52 -40 48 -72 C46 -84 36 -86 34 -74 C34 -46 18 -22 -4 -12 Z" fill="{FUR}"/>'
            + "".join(f'<path d="M{x} {y} l12 -5" stroke="{MASK}" stroke-width="7" stroke-linecap="round"/>'
                      for x, y in ((14, -12), (28, -26), (37, -44), (40, -62)))
            + '</g></g>')
    body = (f'<ellipse cx="160" cy="150" rx="47" ry="40" fill="{FUR}"/>'
            f'<ellipse cx="160" cy="158" rx="28" ry="26" fill="{LIGHT}" opacity=".85"/>')
    head = (f'<g class="bob">'
            f'<circle cx="127" cy="54" r="14" fill="{FUR}"/><circle cx="193" cy="54" r="14" fill="{FUR}"/>'
            f'<circle cx="127" cy="55" r="7" fill="{MASK}"/><circle cx="193" cy="55" r="7" fill="{MASK}"/>'
            f'<circle cx="160" cy="88" r="41" fill="{FUR}"/>'
            f'<ellipse cx="160" cy="70" rx="24" ry="9" fill="{LIGHT}"/>'
            f'<ellipse cx="143" cy="88" rx="16" ry="11" fill="{MASK}"/><ellipse cx="177" cy="88" rx="16" ry="11" fill="{MASK}"/>'
            f'<g class="{eyes}"><g class="blink"><circle cx="144" cy="87" r="5.5" fill="#0d0d10"/>'
            f'<circle cx="176" cy="87" r="5.5" fill="#0d0d10"/></g>'
            f'<circle cx="146" cy="85" r="1.8" fill="#fff"/><circle cx="178" cy="85" r="1.8" fill="#fff"/></g>'
            f'<ellipse cx="160" cy="106" rx="19" ry="13" fill="{LIGHT}"/>'
            f'<ellipse cx="160" cy="99" rx="6.5" ry="4.5" fill="{INK}"/>'
            f'<path d="M154 109 Q160 114 166 109" fill="none" stroke="{INK}" stroke-width="2" stroke-linecap="round"/>'
            # the mascot's headphones: black band, orange-rimmed cups
            f'<path d="M117 86 A44 44 0 0 1 203 86" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
            f'<rect x="109" y="76" width="15" height="28" rx="6" fill="{INK}" stroke="{ACCENT}" stroke-width="2.5"/>'
            f'<rect x="196" y="76" width="15" height="28" rx="6" fill="{INK}" stroke="{ACCENT}" stroke-width="2.5"/>'
            f'</g>')
    arm = lambda x, rot, cls: (f'<g transform="translate({x} 134) rotate({rot})"><g class="{cls}">'  # noqa: E731
                               f'<rect x="-9" y="0" width="18" height="38" rx="9" fill="{FUR_DARK}"/>'
                               f'<ellipse cx="0" cy="38" rx="9" ry="6" fill="{MASK}"/></g></g>')
    if arms == "type":
        hands = arm(132, 18, "tap") + arm(188, -18, "tap2")
    elif arms == "write":
        hands = arm(132, 18, "") + f'<g class="write">{arm(186, -30, "")}</g>'
    elif arms == "hold":
        hands = arm(130, 40, "") + arm(190, -40, "")
    else:
        hands = arm(132, 10, "") + arm(188, -10, "")
    return tail + body + head + hands


def _desk(extra: str = "") -> str:
    return (f'<rect x="0" y="176" width="320" height="44" fill="{DESK}"/>'
            f'<rect x="0" y="176" width="320" height="5" fill="#000" opacity=".2"/>{extra}')


def _keyboard() -> str:
    keys = "".join(f'<rect x="{112 + i * 12}" y="{182 + r * 8}" width="9" height="6" rx="1.5" fill="#3a3a44"/>'
                   for r in range(2) for i in range(8))
    return (f'<rect x="106" y="178" width="108" height="24" rx="4" fill="{INK}"/>{keys}'
            f'<rect x="112" y="190" width="96" height="3" rx="1.5" fill="{ACCENT}" class="glow"/>')


def _book(x: int = 120, y: int = 172, flip: bool = True) -> str:
    page = (f'<path class="flip" d="M{x + 40} {y - 22} L{x + 78} {y - 26} L{x + 78} {y + 2} L{x + 40} {y + 4} Z" '
            f'fill="#fffaf0" stroke="#d8cfb8"/>') if flip else ""
    lines = "".join(f'<path d="M{x + 6} {y - 18 + k * 5} L{x + 34} {y - 19 + k * 5}" stroke="#b9ad92" stroke-width="1.5"/>'
                    for k in range(4))
    return (f'<path d="M{x} {y - 26} L{x + 40} {y - 22} L{x + 80} {y - 26} L{x + 80} {y + 4} L{x + 40} {y + 8} L{x} {y + 4} Z" '
            f'fill="#7a2f2f"/>'
            f'<path d="M{x + 2} {y - 24} L{x + 40} {y - 20} L{x + 40} {y + 4} L{x + 2} {y + 1} Z" fill="{PAPER}"/>'
            f'<path d="M{x + 40} {y - 20} L{x + 78} {y - 24} L{x + 78} {y + 1} L{x + 40} {y + 4} Z" fill="{PAPER}"/>'
            f'{lines}{page}')


def _emoji(x: float, y: float, glyph: str, size: int = 22, cls: str = "") -> str:
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="middle" class="{cls}" '
            f'font-family="Segoe UI Emoji, Apple Color Emoji, Noto Color Emoji, sans-serif">{glyph}</text>')


def _note(x: int, y: int, cls: str, color: str = "#f7d74a") -> str:
    return (f'<g class="{cls}"><rect x="{x}" y="{y}" width="34" height="30" rx="2" fill="{color}"/>'
            f'<path d="M{x + 5} {y + 10} h20 M{x + 5} {y + 17} h14" stroke="#7a6420" stroke-width="2"/></g>')


SCENES = {
    # Reading sentences: eyes scan an open book, a page flips, snacks nearby
    "Reading sentences": lambda: (
        _raccoon("hold", "scan") + _desk(_book() + '<ellipse cx="262" cy="182" rx="26" ry="8" fill="#3a2a20"/>'
                                         + "".join(f'<circle cx="{250 + i * 7}" cy="{177 - (i % 2) * 3}" r="4.5" fill="#e0a43a"/>'
                                                   for i in range(4)))),
    # Finding characters: writing names on sticky notes that pop onto the wall
    "Finding characters": lambda: (
        _note(18, 26, "pop1") + _note(58, 44, "pop2", "#9fd36a") + _note(232, 28, "pop3", "#f59ab4")
        + _note(268, 52, "pop4", "#8cc8f0") + _raccoon("write")
        + _desk(f'<rect x="170" y="166" width="58" height="14" rx="2" fill="{PAPER}" transform="rotate(-4 199 173)"/>')),
    # Linking pronouns: a magnifying glass sweeps over "she?" and an arrow finds the name
    "Linking pronouns": lambda: (
        f'<rect x="16" y="22" width="112" height="56" rx="8" fill="{PAPER}"/>'
        f'<text x="30" y="46" font-size="15" font-family="Georgia, serif" fill="#3b3326">“she said…”</text>'
        f'<text x="30" y="68" font-size="15" font-family="Georgia, serif" fill="#a8433f" font-weight="bold">Estella</text>'
        f'<path class="arrow" d="M58 50 C40 54 40 58 50 60" fill="none" stroke="#a8433f" stroke-width="2.5"/>'
        f'<g class="lens"><circle cx="40" cy="44" r="13" fill="#bfe3ff" fill-opacity=".35" stroke="{INK}" stroke-width="3.5"/>'
        f'<path d="M49 53 L60 64" stroke="{INK}" stroke-width="5" stroke-linecap="round"/></g>'
        + _emoji(262, 54, "❓", 30, "bob") + _raccoon("rest", "scan") + _desk()),
    # Scoring sentiment: a balance scale tips between sun and rain
    "Scoring sentiment": lambda: (
        _raccoon("rest", "scan") + _desk(
            '<rect x="265" y="104" width="6" height="74" fill="#b38b4a"/><rect x="250" y="174" width="36" height="6" rx="2" fill="#b38b4a"/>'
            '<g class="tilt"><rect x="226" y="98" width="84" height="5" rx="2.5" fill="#c9a24a"/>'
            '<path d="M230 103 L222 124 M238 103 L246 124 M298 103 L290 124 M306 103 L314 124" stroke="#c9a24a" stroke-width="1.6"/>'
            '<path d="M218 124 h32 a16 6 0 0 1 -32 0 Z M286 124 h32 a16 6 0 0 1 -32 0 Z" fill="#c9a24a"/>'
            + _emoji(234, 121, "☀️", 17) + _emoji(302, 121, "🌧️", 17) + '</g>')),
    # Detecting emotions: feelings float up out of the book; one makes the raccoon cry a little
    "Detecting emotions": lambda: (
        _raccoon("hold") + f'<ellipse class="tear" cx="134" cy="100" rx="3" ry="4.5" fill="#7fc4ff"/>'
        + _desk(_book(120, 172, flip=False))
        # feelings float up out of the book, beside the raccoon (not across its face)
        + _emoji(62, 168, "😢", 24, "rise1") + _emoji(92, 168, "😄", 24, "rise2")
        + _emoji(228, 168, "😨", 24, "rise3") + _emoji(256, 150, "🥰", 24, "rise4")
        + f'<rect x="246" y="150" width="46" height="28" rx="3" fill="#8cc8f0"/>'
        f'<path d="M262 150 q7 -18 14 0" fill="#fff"/>'),
    # Naming chapters: stamping a theme on each chapter card
    "Naming chapters": lambda: (
        _raccoon("rest") + _desk(
            "".join(f'<rect x="{60 + i * 72}" y="150" width="56" height="34" rx="3" fill="{PAPER}"/>'
                    f'<path d="M{66 + i * 72} 176 h30" stroke="#b9ad92" stroke-width="2"/>' for i in range(3))
            + _emoji(88, 172, "⚔️", 18, "ink1") + _emoji(160, 172, "💍", 18, "ink2") + _emoji(232, 172, "🪦", 18, "ink3")
            + f'<g class="stamp"><rect x="196" y="116" width="14" height="22" rx="3" fill="#7a4a2a"/>'
              f'<rect x="188" y="136" width="30" height="10" rx="2" fill="#a8433f"/></g>')),
    # Finding relationships: red thread between portraits on a corkboard
    "Finding relationships": lambda: (
        f'<rect x="14" y="14" width="292" height="66" rx="6" fill="#b48a5a"/>'
        + "".join(f'<circle cx="{x}" cy="{y}" r="13" fill="{c}" stroke="#fff" stroke-width="2.5"/>'
                  for x, y, c in ((44, 38, "#3987e5"), (120, 58, "#d95926"), (200, 32, "#d55181"), (276, 56, "#199e70")))
        + f'<path class="thread1" d="M44 38 Q82 70 120 58" fill="none" stroke="#c0262d" stroke-width="2.5"/>'
          f'<path class="thread2" d="M120 58 Q160 20 200 32" fill="none" stroke="#c0262d" stroke-width="2.5"/>'
          f'<path class="thread3" d="M200 32 Q240 70 276 56" fill="none" stroke="#c0262d" stroke-width="2.5"/>'
        + _raccoon("type") + _desk(_keyboard())),
}
DEFAULT = lambda: _raccoon("type") + _desk(_keyboard())  # noqa: E731  getting started: typing away


def scene_svg(step: str) -> str:
    """The animated scene for an analysis step (the typing raccoon for anything else)."""
    art = SCENES.get(step, DEFAULT)()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 220" width="320" height="220">'
            f'<style>{STYLE}</style>'
            f'<rect width="320" height="220" rx="18" fill="#1b2230"/>{art}</svg>')


def scene_uri(step: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(scene_svg(step).encode()).decode()
