"""The page's look: light, dark or fun.

Light and dark are Streamlit's own themes (.streamlit/config.toml). Streamlit reads the
chosen one from the browser's localStorage when the page loads, so switching needs one
reload: `switch_script` saves the choice there and reloads (the open book survives in
the address, see streamlit_app.py).

Fun keeps the light or dark colours and adds a playful skin (rounded headings, confetti,
bouncy cards) and a raccoon buddy in the corner. The buddy's eyes follow the mouse, it
switches between little acts (waving, snacking, napping, juggling…), says things about
the book, and now and then peeks over the edge of a chart. Charts keep their colours:
those carry meaning (characters, emotions, mood), so fun never changes them.
"""

import json
from html import escape

import raccoon

LOOKS = {"light": "☀️ Light", "dark": "🌙 Dark", "fun": "🦝 Fun"}
FUN_ORANGE = "#ff8a2a"  # the raccoon's headphones


def switch_script(base: str) -> str:
    """Save Streamlit's light/dark choice in the browser and reload the page once.
    (A reload that didn't change the theme isn't repeated for 10 seconds, so it can't loop.)"""
    want = json.dumps("Dark" if base == "dark" else "Light")
    return f"""<script>
    const p = window.parent, last = +(p.sessionStorage.getItem("ba-theme-switch") || 0);
    if (Date.now() - last > 10000) {{
      p.sessionStorage.setItem("ba-theme-switch", String(Date.now()));
      p.localStorage.setItem(`stActiveTheme-${{p.location.pathname}}-v2`, JSON.stringify({want}));
      setTimeout(() => p.location.reload(), 150);  // let the address update first
    }}
    </script>"""


def fun_css(mode: str) -> str:
    """The playful skin on top of the light or dark page."""
    dots = "rgba(255,138,42,.10)" if mode == "light" else "rgba(255,138,42,.07)"
    dots2 = "rgba(46,196,182,.10)" if mode == "light" else "rgba(46,196,182,.07)"
    return f"""<style>
    @import url("https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600;700&display=swap");
    :root {{ --ba-gold: {FUN_ORANGE}; }}
    .stApp {{ background-image: radial-gradient({dots} 2px, transparent 2.5px),
                                radial-gradient({dots2} 2px, transparent 2.5px);
              background-size: 46px 46px, 46px 46px; background-position: 0 0, 23px 23px; }}
    .stMainBlockContainer [data-testid="stHeading"] h2, .stMainBlockContainer h4, .ba-hero h1, .ba-shape h3, .ba-about h2 {{
        font-family: "Fredoka", system-ui, sans-serif !important; letter-spacing: 0 !important; }}
    .stMainBlockContainer [data-testid="stHeading"] h2 {{
        background: linear-gradient(90deg, #ff5e8a, {FUN_ORANGE}, #ffc83d, #2ec4b6);
        -webkit-background-clip: text; background-clip: text; color: transparent; }}
    .stMainBlockContainer [data-testid="stHeading"] h2::before {{
        content: "🦝 Chapter " counter(section, upper-roman); }}
    .stMainBlockContainer [data-testid="stHeading"] h2::after {{
        width: 120px; height: 5px; background: linear-gradient(90deg, #ff5e8a, {FUN_ORANGE}, #ffc83d, #2ec4b6); }}
    [class*="st-key-panel-"] {{ border-radius: 24px !important; border-width: 2px !important;
        transition: transform .25s cubic-bezier(.3, 1.6, .5, 1), border-color .25s ease !important; }}
    [class*="st-key-panel-"]:hover {{ transform: translateY(-3px) rotate(-.25deg); }}
    @media (prefers-reduced-motion: reduce) {{ [class*="st-key-panel-"]:hover {{ transform: none; }} }}

    /* the buddy in the corner */
    #ba-buddy {{ position: fixed; right: 18px; bottom: 10px; width: 132px; z-index: 999990; cursor: pointer;
        filter: drop-shadow(0 6px 14px rgba(0,0,0,.25)); transition: transform .3s ease; }}
    #ba-buddy:hover {{ transform: translateY(-4px) scale(1.04); }}
    #ba-buddy svg {{ display: block; width: 100%; height: auto; }}
    #ba-buddy .bubble {{ position: absolute; right: 86%; bottom: 72%; width: max-content; max-width: 220px;
        background: #fffdf7; color: #1d1d22; border: 2px solid #1d1d22; border-radius: 16px 16px 4px 16px;
        padding: 7px 11px; font: 600 13px/1.35 "Fredoka", system-ui, sans-serif; box-shadow: 0 4px 0 #1d1d22;
        opacity: 0; transform: translateY(6px) scale(.9); transform-origin: bottom right;
        transition: opacity .25s ease, transform .25s cubic-bezier(.3, 1.6, .5, 1); pointer-events: none; }}
    #ba-buddy .bubble.show {{ opacity: 1; transform: none; }}
    .ba-peek {{ position: absolute; top: -40px; right: 48px; width: 76px; height: 40px; overflow: hidden;
        pointer-events: none; z-index: 5; }}
    .ba-peek svg {{ width: 76px; display: block; transform: translateY(42px); transition: transform .6s cubic-bezier(.3, 1.4, .5, 1); }}
    .ba-peek.up svg {{ transform: translateY(0); }}
    @media (max-width: 640px) {{ #ba-buddy {{ width: 84px; right: 6px; }} #ba-buddy .bubble {{ max-width: 160px; font-size: 12px; }} }}
    {raccoon.BUDDY_STYLE}
    </style>"""


def buddy_html() -> str:
    """The buddy's spot and speech bubble (st.html). st.html cleans out inline SVG, so the
    script draws the raccoon in (and again if Streamlit redraws this spot)."""
    return ('<div id="ba-buddy" data-act="wave" title="Click me!">'
            '<div class="bubble show">Hi! I read the whole book 📚</div></div>')


def book_facts(analysis, shape: str | None = None) -> list[str]:
    """Things the raccoon says about the open book (made here, no AI service needed)."""
    facts = ["Psst… press ▶ Travel on the Story road!", "I'm not lazy. I'm processing. 🦝",
             f"I read all {len(analysis.sentences):,} sentences. My eyes hurt."]
    people = sorted(analysis.characters, key=lambda c: -c.mentions)
    if people:
        facts.append(f"{people[0].name} is mentioned {people[0].mentions:,} times. Popular!")
    if len(people) > 2:
        facts.append(f"Don't forget {people[2].name}! Third most talked about.")
    if analysis.chapter_sentiment:
        tones = analysis.chapter_sentiment
        dark, bright = tones.index(min(tones)), tones.index(max(tones))
        facts.append(f"{analysis.chapters[dark].title} is the darkest chapter. I needed a snack after it. 🍪")
        facts.append(f"{analysis.chapters[bright].title} is the happiest chapter! 🎉")
    if analysis.relationships:
        names = {c.id: c.name for c in analysis.characters}
        r = max(analysis.relationships, key=lambda r: r.count)
        if r.source in names and r.target in names:
            facts.append(f"{names[r.source]} & {names[r.target]}: {r.count} moments together 👀")
    if shape:
        facts.append(f"Spoiler: this is {'an' if shape[0] in 'AEIOU' else 'a'} {shape} story.")
    return facts


def buddy_script(facts: list[str], peek: bool = True) -> str:
    """Brings the buddy to life (runs in a hidden frame and reaches into the page): eyes follow
    the mouse, a new act every few seconds or on a click, a fact in the bubble now and then,
    and sometimes a peek over a chart card that is on screen."""
    acts = json.dumps(raccoon.BUDDY_ACTS)
    lines = json.dumps({"wave": ["Hi there! 👋", "Hello, reader!"], "snack": ["nom nom 🍪", "Book snacks are the best."],
                        "nap": ["zzz…", "Five more chapters…"], "music": ["♪ This book has a beat", "🎧 Reading music"],
                        "juggle": ["Juggling emotions!", "Love, sadness, anger… whee!"],
                        "inspect": ["Hmm, interesting chart…", "Let me check these numbers 🔍"],
                        "stare": ["I can see you 👀", "Are you reading too?"]})
    peek_art, buddy_art = json.dumps(raccoon.peek_svg()), json.dumps(raccoon.buddy_svg())
    return f"""<script>
    const p = window.parent, doc = p.document;
    const ACTS = {acts}, LINES = {lines}, FACTS = {json.dumps(facts)}, PEEK = {peek_art}, ART = {buddy_art};
    const REDUCE = p.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // one set of timers for the whole page, even when Streamlit redraws this frame
    (p.__baBuddyTimers || []).forEach(clearInterval); p.__baBuddyTimers = [];
    if (p.__baBuddyMove) doc.removeEventListener("pointermove", p.__baBuddyMove);
    const pick = (list) => list[Math.floor(Math.random() * list.length)];
    const buddy = () => doc.getElementById("ba-buddy");
    // draw the raccoon into its spot, and wire it up once
    function ensure() {{
      const el = buddy(); if (!el) return;
      if (!el.querySelector("svg")) el.insertAdjacentHTML("beforeend", ART);
      if (!el.dataset.wired) {{ el.dataset.wired = "1"; el.addEventListener("click", nextAct);
        setTimeout(() => el.querySelector(".bubble")?.classList.remove("show"), 4500); }}
    }}
    let bubbleTimer = null;
    function say(text) {{
      const b = buddy() && buddy().querySelector(".bubble"); if (!b) return;
      b.textContent = text; b.classList.add("show");
      clearTimeout(bubbleTimer); bubbleTimer = setTimeout(() => b.classList.remove("show"), 4200);
    }}
    function nextAct() {{
      const el = buddy(); if (!el) return;
      const act = pick(ACTS.filter((a) => a !== el.dataset.act)); el.dataset.act = act;
      say(Math.random() < 0.45 ? pick(FACTS) : pick(LINES[act]));
    }}
    // the eyes follow the mouse
    p.__baBuddyMove = (e) => {{
      const el = buddy(), pupils = el && el.querySelector("#ba-pupils"); if (!pupils) return;
      const r = el.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height * 0.38;
      const dx = e.clientX - cx, dy = e.clientY - cy, d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 220) * 2.8;
      pupils.setAttribute("transform", `translate(${{(dx / d * k).toFixed(2)}} ${{(dy / d * k).toFixed(2)}})`);
    }};
    doc.addEventListener("pointermove", p.__baBuddyMove);
    ensure(); p.__baBuddyTimers.push(setInterval(ensure, 1000));
    p.__baBuddyTimers.push(setInterval(nextAct, REDUCE ? 15000 : 8000));
    // now and then, peek over the top edge of a chart card that is on screen
    function peek() {{
      if (!buddy() || doc.querySelector(".ba-peek")) return;
      const cards = [...doc.querySelectorAll('[class*="st-key-panel-"]')].filter((c) => {{
        const r = c.getBoundingClientRect(); return r.top > 60 && r.top < p.innerHeight * 0.7; }});
      if (!cards.length) return;
      const card = pick(cards), spot = doc.createElement("div");
      if (getComputedStyle(card).position === "static") card.style.position = "relative";
      spot.className = "ba-peek"; spot.innerHTML = PEEK; spot.style.right = `${{20 + Math.random() * 50}}%`;
      card.appendChild(spot);
      requestAnimationFrame(() => requestAnimationFrame(() => spot.classList.add("up")));
      setTimeout(() => spot.classList.remove("up"), 3200);
      setTimeout(() => spot.remove(), 4000);
    }}
    if ({'true' if peek else 'false'} && !REDUCE) p.__baBuddyTimers.push(setInterval(peek, 19000));
    </script>"""
