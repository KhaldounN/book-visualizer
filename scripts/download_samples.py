"""Download public-domain test novels from Project Gutenberg into data/."""

from pathlib import Path
from urllib.request import urlopen

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# file name -> Project Gutenberg plain-text URL
SAMPLES = {
    "pride_and_prejudice.txt": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
}


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for name, url in SAMPLES.items():
        target = DATA_DIR / name
        if target.exists():
            print(f"Already have {name}")
            continue
        print(f"Downloading {name} ...")
        with urlopen(url) as response:
            target.write_bytes(response.read())
        print(f"Saved {target} ({target.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
