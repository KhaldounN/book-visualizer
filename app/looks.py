"""The page's look: light or dark.

Both are Streamlit's own themes (.streamlit/config.toml). Streamlit reads the chosen one
from the browser's localStorage when the page loads, so switching needs one reload:
`switch_script` saves the choice there and reloads (the open book survives in the
address, see streamlit_app.py).
"""

import json

LOOKS = {"light": "Light", "dark": "Dark"}


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
