"""Download the cover picture of every book in data/ from Project Gutenberg into app/static/covers/
(served by Streamlit at /app/static/covers/, see .streamlit/config.toml).

Run from the project folder:  .venv\\Scripts\\python.exe scripts\\download_covers.py
Each cover is shrunk to 220 pixels wide (a few KB), so the start page loads quickly.
"""

import io
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from download_samples import SAMPLES  # noqa: E402  (file name -> Gutenberg text URL, which holds the book's number)

COVERS = ROOT / "app" / "static" / "covers"
WIDTH = 220


def main() -> None:
    COVERS.mkdir(parents=True, exist_ok=True)
    for path in sorted((ROOT / "data").glob("*.txt")):
        target = COVERS / f"{path.stem}.jpg"
        url = SAMPLES.get(path.name)
        number = re.search(r"/epub/(\d+)/", url or "")
        if target.exists() or not number:
            print(f"{'Already have' if target.exists() else 'No Gutenberg number for'} {path.name}")
            continue
        n = number.group(1)
        cover_url = f"https://www.gutenberg.org/cache/epub/{n}/pg{n}.cover.medium.jpg"
        try:
            with urlopen(Request(cover_url, headers={"User-Agent": "BookVisualizer/1.0"}), timeout=30) as response:
                picture = Image.open(io.BytesIO(response.read())).convert("RGB")
        except OSError as error:
            print(f"No cover for {path.name}: {error}")
            continue
        picture.thumbnail((WIDTH, WIDTH * 2))
        picture.save(target, "JPEG", quality=82, optimize=True)
        print(f"Saved {target.name} ({target.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
