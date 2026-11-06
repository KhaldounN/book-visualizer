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


# --- The working raccoon's story: a 20-second loop in five acts -----------------------------------
# Each act fills a 4-second window: looking at words, reading sentences, thinking about meanings,
# drawing the charts, and feeling the story (it cries, then smiles). Layers fade in and out with
# `window` keyframes; the raccoon's face and paws change with the act. Each analysis step starts the
# loop at its own act (a negative animation delay, --d), so the scene fits what is happening.
CYCLE = 20  # seconds
ACTS = ["looking at words", "reading sentences", "thinking about meanings", "drawing the charts",
        "feeling the story"]
STEP_ACT = {"Reading sentences": 1, "Finding characters": 0, "Linking pronouns": 0, "Scoring sentiment": 2,
            "Detecting emotions": 4, "Naming chapters": 2, "Finding relationships": 3}

STORY_STYLE = """
.w1, .w2, .w3, .w4, .w5, .cry, .smile, .calm, .hold, .chin, .paint { animation-duration: 20s;
  animation-iteration-count: infinite; animation-delay: var(--d, 0s); }
.w1 { animation-name: w1; } .w2 { animation-name: w2; } .w3 { animation-name: w3; } .w4 { animation-name: w4; }
.w5 { animation-name: w5; } .cry { animation-name: cry; } .smile { animation-name: smile; } .calm { animation-name: calm; }
.hold { animation-name: hold; } .chin { animation-name: w3; } .paint { animation-name: w4; }
@keyframes w1 { 0% { opacity: 0; } 1.5%, 18.5% { opacity: 1; } 20%, 100% { opacity: 0; } }
@keyframes w2 { 0%, 20% { opacity: 0; } 21.5%, 38.5% { opacity: 1; } 40%, 100% { opacity: 0; } }
@keyframes w3 { 0%, 40% { opacity: 0; } 41.5%, 58.5% { opacity: 1; } 60%, 100% { opacity: 0; } }
@keyframes w4 { 0%, 60% { opacity: 0; } 61.5%, 78.5% { opacity: 1; } 80%, 100% { opacity: 0; } }
@keyframes w5 { 0%, 80% { opacity: 0; } 81.5%, 98.5% { opacity: 1; } 100% { opacity: 0; } }
@keyframes cry { 0%, 80% { opacity: 0; } 81%, 89% { opacity: 1; } 90%, 100% { opacity: 0; } }
@keyframes smile { 0%, 90% { opacity: 0; } 91%, 99% { opacity: 1; } 100% { opacity: 0; } }
@keyframes calm { 0%, 79.5% { opacity: 1; } 80.5%, 99.5% { opacity: 0; } 100% { opacity: 1; } }
@keyframes hold { 0%, 39.5% { opacity: 1; } 40.5%, 79.5% { opacity: 0; } 80.5%, 100% { opacity: 1; } }
/* motions inside an act repeat every 4 s, in step with the act windows */
.sweep { animation: sweep 4s ease-in-out infinite; animation-delay: var(--d, 0s); }
.hl1, .hl2, .hl3 { transform-box: fill-box; transform-origin: left; transform: scaleX(0);
  animation: hl 4s linear infinite; animation-delay: var(--d, 0s); }
.hl2 { animation-name: hl2; } .hl3 { animation-name: hl3; }
.bulb { animation: bulb 4s ease-in-out infinite; animation-delay: var(--d, 0s); }
.query { animation: query 4s ease-in-out infinite; animation-delay: var(--d, 0s); }
.grow1, .grow2, .grow3 { transform-box: fill-box; transform-origin: bottom; animation: grow 4s ease-out infinite;
  animation-delay: var(--d, 0s); }
.grow2 { animation-name: grow2; } .grow3 { animation-name: grow3; }
.trace { stroke-dasharray: 90; stroke-dashoffset: 90; animation: trace 4s ease-in-out infinite; animation-delay: var(--d, 0s); }
.brush { transform-box: fill-box; transform-origin: top; animation: brush .7s ease-in-out infinite alternate; }
.drop { animation: drop 1.1s ease-in infinite; } .drop2 { animation: drop 1.1s ease-in .55s infinite; }
.heart1, .heart2 { animation: heart 2s ease-out infinite; } .heart2 { animation-delay: 1s; }
.chip-pop1, .chip-pop2, .chip-pop3 { transform-box: fill-box; transform-origin: center; animation: chip 4s infinite;
  animation-delay: var(--d, 0s); }
.chip-pop2 { animation-name: chip2; } .chip-pop3 { animation-name: chip3; }
@keyframes sweep { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(6px, 52px); } }
@keyframes hl { 0% { transform: scaleX(0); } 30%, 100% { transform: scaleX(1); } }
@keyframes hl2 { 0%, 30% { transform: scaleX(0); } 62%, 100% { transform: scaleX(1); } }
@keyframes hl3 { 0%, 62% { transform: scaleX(0); } 95%, 100% { transform: scaleX(1); } }
@keyframes query { 0%, 45% { opacity: 1; } 55%, 100% { opacity: 0; } }
@keyframes bulb { 0%, 45% { opacity: 0; } 55%, 100% { opacity: 1; } }
@keyframes grow { 0% { transform: scaleY(0); } 30%, 100% { transform: scaleY(1); } }
@keyframes grow2 { 0%, 20% { transform: scaleY(0); } 50%, 100% { transform: scaleY(1); } }
@keyframes grow3 { 0%, 40% { transform: scaleY(0); } 70%, 100% { transform: scaleY(1); } }
@keyframes trace { 0%, 55% { stroke-dashoffset: 90; } 95%, 100% { stroke-dashoffset: 0; } }
@keyframes brush { from { transform: rotate(-8deg); } to { transform: rotate(8deg); } }
@keyframes drop { 0% { opacity: 0; transform: translateY(0); } 15% { opacity: 1; } 100% { opacity: 0; transform: translateY(22px); } }
@keyframes heart { 0% { opacity: 0; transform: translateY(0) scale(.6); } 20% { opacity: 1; } 100% { opacity: 0; transform: translateY(-34px) scale(1.1); } }
@keyframes chip { 0%, 5% { transform: scale(0); } 15%, 100% { transform: scale(1); } }
@keyframes chip2 { 0%, 25% { transform: scale(0); } 35%, 100% { transform: scale(1); } }
@keyframes chip3 { 0%, 45% { transform: scale(0); } 55%, 100% { transform: scale(1); } }
@media (prefers-reduced-motion: reduce) { .w2, .w3, .w4, .w5, .cry, .smile, .chin, .paint { display: none; } }
"""

SERIF = "Georgia, 'Times New Roman', serif"
SANS = "Segoe UI, Inter, Arial, sans-serif"


def _head_base() -> str:
    """Ears, head, brow fur, mask, muzzle, nose and headphones: what stays the same in every mood."""
    return (f'<circle cx="127" cy="54" r="14" fill="{FUR}"/><circle cx="193" cy="54" r="14" fill="{FUR}"/>'
            f'<circle cx="127" cy="55" r="7" fill="{MASK}"/><circle cx="193" cy="55" r="7" fill="{MASK}"/>'
            f'<circle cx="160" cy="88" r="41" fill="{FUR}"/>'
            f'<ellipse cx="160" cy="70" rx="24" ry="9" fill="{LIGHT}"/>'
            f'<ellipse cx="143" cy="88" rx="16" ry="11" fill="{MASK}"/><ellipse cx="177" cy="88" rx="16" ry="11" fill="{MASK}"/>'
            f'<ellipse cx="160" cy="106" rx="19" ry="13" fill="{LIGHT}"/>'
            f'<ellipse cx="160" cy="99" rx="6.5" ry="4.5" fill="{INK}"/>'
            f'<path d="M117 86 A44 44 0 0 1 203 86" fill="none" stroke="{INK}" stroke-width="7" stroke-linecap="round"/>'
            f'<rect x="109" y="76" width="15" height="28" rx="6" fill="{INK}" stroke="{ACCENT}" stroke-width="2.5"/>'
            f'<rect x="196" y="76" width="15" height="28" rx="6" fill="{INK}" stroke="{ACCENT}" stroke-width="2.5"/>')


def _faces() -> str:
    """Three faces that take turns: calm (open eyes, small smile), crying, smiling."""
    calm = (f'<g class="calm"><g class="scan"><g class="blink"><circle cx="144" cy="87" r="5.5" fill="#0d0d10"/>'
            f'<circle cx="176" cy="87" r="5.5" fill="#0d0d10"/></g>'
            f'<circle cx="146" cy="85" r="1.8" fill="#fff"/><circle cx="178" cy="85" r="1.8" fill="#fff"/></g>'
            f'<path d="M154 109 Q160 114 166 109" fill="none" stroke="{INK}" stroke-width="2" stroke-linecap="round"/></g>')
    cry = (f'<g class="cry"><circle cx="144" cy="89" r="5" fill="#0d0d10"/><circle cx="176" cy="89" r="5" fill="#0d0d10"/>'
           f'<circle cx="145.5" cy="87" r="1.8" fill="#bfe4ff"/><circle cx="177.5" cy="87" r="1.8" fill="#bfe4ff"/>'
           f'<path d="M134 79 L150 75 M186 79 L170 75" stroke="{LIGHT}" stroke-width="2.6" stroke-linecap="round"/>'
           f'<path d="M153 114 Q160 107 167 114" fill="none" stroke="{INK}" stroke-width="2.2" stroke-linecap="round"/>'
           f'<path class="drop" d="M140 96 q3 5 0 7 q-3 -2 0 -7 Z" fill="#8fd0ff"/>'
           f'<path class="drop2" d="M180 96 q3 5 0 7 q-3 -2 0 -7 Z" fill="#8fd0ff"/></g>')
    smile = (f'<g class="smile"><path d="M137 89 Q144 81 151 89 M169 89 Q176 81 183 89" fill="none" stroke="{LIGHT}" '
             f'stroke-width="2.8" stroke-linecap="round"/>'
             f'<path d="M150 106 Q160 121 170 106 Z" fill="#6e2b2e" stroke="{INK}" stroke-width="1.5" stroke-linejoin="round"/>'
             f'<ellipse cx="160" cy="113.5" rx="4.5" ry="2.4" fill="#f27d8f"/>'
             f'<circle cx="139" cy="103" r="4.5" fill="#f59aaa" opacity=".6"/><circle cx="181" cy="103" r="4.5" fill="#f59aaa" opacity=".6"/></g>')
    return calm + cry + smile


def _arm(x: float, y: float, rot: float, extra: str = "") -> str:
    return (f'<g transform="translate({x} {y}) rotate({rot})"><rect x="-9" y="0" width="18" height="38" rx="9" '
            f'fill="{FUR_DARK}"/><ellipse cx="0" cy="38" rx="9" ry="6" fill="{MASK}"/>{extra}</g>')


def _paws() -> str:
    """The paws for each act: holding the book, a paw on the chin (thinking), a paintbrush (drawing)."""
    hold = f'<g class="hold">{_arm(130, 134, 40)}{_arm(190, 134, -40)}</g>'
    chin = (f'<g class="chin">{_arm(190, 134, -40)}'
            f'<path d="M126 150 C126 138 136 126 150 124" fill="none" stroke="{FUR_DARK}" stroke-width="17" stroke-linecap="round"/>'
            f'<ellipse cx="152" cy="123" rx="9" ry="6.5" fill="{MASK}"/></g>')
    brush = (f'<g class="brush"><path d="M0 40 L0 62" stroke="#b07a3a" stroke-width="4" stroke-linecap="round"/>'
             f'<path d="M-3 62 L3 62 L1 72 L-1 72 Z" fill="#c0392b"/></g>')
    paint = f'<g class="paint">{_arm(190, 134, -40)}{_arm(128, 132, 128, brush)}</g>'
    return hold + chin + paint


def _caption(k: int, text: str) -> str:
    cls = f"w{k + 1}"
    width = 12 + len(text) * 6.1
    return (f'<g class="{cls}"><rect x="10" y="196" width="{width:.0f}" height="18" rx="9" fill="#000" opacity=".35"/>'
            f'<text x="{10 + width / 2:.0f}" y="209" font-size="10.5" text-anchor="middle" fill="#f4efe2" '
            f'font-family="{SANS}" font-weight="600" letter-spacing=".4">{text}</text></g>')


def _act_words() -> str:
    chips = ((16, 28, "Estella", "#f4efe2", 1), (40, 54, "she", "#ffe08a", 2), (20, 80, "storm", "#bfe3ff", 3))
    out = "".join(f'<g class="chip-pop{n}"><rect x="{x}" y="{y}" width="{len(w) * 9 + 14}" height="20" rx="10" fill="{c}"/>'
                  f'<text x="{x + 7}" y="{y + 14.5}" font-size="13" font-family="{SERIF}" fill="#3b3326">{w}</text></g>'
                  for x, y, w, c, n in chips)
    lens = (f'<g class="sweep"><circle cx="34" cy="36" r="13" fill="#bfe3ff" fill-opacity=".35" stroke="{INK}" '
            f'stroke-width="3.5"/><path d="M43 45 L54 56" stroke="{INK}" stroke-width="5" stroke-linecap="round"/></g>')
    return f'<g class="w1">{out}{lens}</g>'


def _act_sentences() -> str:
    lines = "".join(f'<path d="M22 {44 + k * 14} h{80 - (k == 3) * 30}" stroke="#9c917a" stroke-width="3" '
                    f'stroke-linecap="round"/>' for k in range(4))
    marks = "".join(f'<rect class="hl{k + 1}" x="20" y="{38 + k * 14}" width="84" height="11" rx="3" fill="#ffe14d" '
                    f'opacity=".55"/>' for k in range(3))
    return (f'<g class="w2"><rect x="12" y="22" width="100" height="84" rx="6" fill="{PAPER}"/>'
            f'<text x="22" y="35" font-size="9" font-family="{SERIF}" fill="#7a6a4a" font-style="italic">It was a dark and…</text>'
            f'{marks}{lines}</g>')


def _act_thinking() -> str:
    bubble = ('<g fill="#f4efe2"><circle cx="214" cy="98" r="4"/><circle cx="224" cy="86" r="6"/>'
              '<ellipse cx="262" cy="50" rx="44" ry="30"/><circle cx="236" cy="40" r="20"/><circle cx="288" cy="40" r="18"/></g>')
    query = f'<text class="query" x="262" y="62" font-size="36" text-anchor="middle" font-family="{SERIF}" font-weight="bold" fill="#a8433f">?</text>'
    bulb = ('<g class="bulb"><circle cx="262" cy="46" r="13" fill="#ffd84a"/>'
            '<circle cx="262" cy="46" r="20" fill="#ffd84a" opacity=".25"/>'
            '<rect x="256" y="58" width="12" height="9" rx="2" fill="#8d8d96"/>'
            '<path d="M257 46 l3 4 l4 -7" fill="none" stroke="#b07a1a" stroke-width="1.8"/></g>')
    return f'<g class="w3">{bubble}{query}{bulb}<text x="262" y="72" font-size="8.5" text-anchor="middle" font-family="{SANS}" fill="#7a6a4a">what does it mean?</text></g>'


def _act_drawing() -> str:
    easel = ('<path d="M30 112 L18 176 M98 112 L110 176 M64 112 L64 176" stroke="#8a5a32" stroke-width="4" stroke-linecap="round"/>'
             f'<rect x="16" y="26" width="96" height="86" rx="3" fill="#fffaf0" stroke="#8a5a32" stroke-width="3"/>')
    bars = "".join(f'<rect class="grow{k + 1}" x="{30 + k * 22}" y="{100 - h}" width="14" height="{h}" rx="2" fill="{c}"/>'
                   for k, (h, c) in enumerate(((26, "#3987e5"), (46, "#d95926"), (36, "#199e70"))))
    line = '<path class="trace" d="M26 80 C44 60 58 76 72 52 S96 40 104 36" fill="none" stroke="#a8433f" stroke-width="2.5" stroke-linecap="round"/>'
    return f'<g class="w4">{easel}{bars}{line}<path d="M16 104 h96" stroke="#c9bfa8" stroke-width="1.2"/></g>'


def _act_feeling() -> str:
    cloud = ('<g class="cry"><ellipse cx="262" cy="44" rx="30" ry="14" fill="#8d97a6"/><circle cx="248" cy="36" r="12" fill="#8d97a6"/>'
             '<circle cx="270" cy="32" r="14" fill="#8d97a6"/>'
             '<path class="drop" d="M250 60 q2 4 0 6 q-2 -2 0 -6Z M266 60 q2 4 0 6 q-2 -2 0 -6Z M280 60 q2 4 0 6 q-2 -2 0 -6Z" fill="#8fd0ff"/>'
             f'<text x="262" y="16" font-size="9" text-anchor="middle" font-family="{SANS}" fill="#cfd6e2">such a sad chapter…</text></g>')
    heart = lambda x, y, cls: (f'<path class="{cls}" d="M{x} {y} c-4 -5 -11 -1 -7 5 l7 7 l7 -7 c4 -6 -3 -10 -7 -5 Z" '  # noqa: E731
                               f'fill="#ff6b8b"/>')
    joy = (f'<g class="smile">{heart(250, 60, "heart1")}{heart(276, 48, "heart2")}{heart(232, 40, "heart2")}'
           f'<text x="262" y="16" font-size="9" text-anchor="middle" font-family="{SANS}" fill="#ffe6ec">what a happy ending!</text></g>')
    return f'<g class="w5">{cloud}{joy}</g>'


def _story(start_act: int) -> str:
    """The whole loop, started at one act."""
    tail = (f'<g transform="translate(205 150)"><g class="wag">'
            f'<path d="M0 0 C30 -10 52 -40 48 -72 C46 -84 36 -86 34 -74 C34 -46 18 -22 -4 -12 Z" fill="{FUR}"/>'
            + "".join(f'<path d="M{x} {y} l12 -5" stroke="{MASK}" stroke-width="7" stroke-linecap="round"/>'
                      for x, y in ((14, -12), (28, -26), (37, -44), (40, -62)))
            + '</g></g>')
    body = (f'<ellipse cx="160" cy="150" rx="47" ry="40" fill="{FUR}"/>'
            f'<ellipse cx="160" cy="158" rx="28" ry="26" fill="{LIGHT}" opacity=".85"/>')
    head = f'<g class="bob">{_head_base()}{_faces()}</g>'
    desk = _desk(_book(120, 172, flip=True))
    captions = "".join(_caption(k, text) for k, text in enumerate(ACTS))
    acts = _act_words() + _act_sentences() + _act_thinking() + _act_drawing() + _act_feeling()
    return f'<g style="--d:-{start_act * CYCLE // len(ACTS)}s">{acts}{tail}{body}{head}{desk}{_paws()}{captions}</g>'


# every analysis step gets the story, started at the act that fits it (tests check each step has one)
SCENES = {step: (lambda act=act: _story(act)) for step, act in STEP_ACT.items()}
DEFAULT = lambda: _story(0)  # noqa: E731  getting started


def scene_svg(step: str) -> str:
    """The animated scene for an analysis step (the story from its start for anything else)."""
    art = SCENES.get(step, DEFAULT)()
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 220" width="320" height="220">'
            f'<style>{STYLE}{STORY_STYLE}</style>'
            f'<rect width="320" height="220" rx="18" fill="#1b2230"/>{art}</svg>')


def scene_uri(step: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(scene_svg(step).encode()).decode()
