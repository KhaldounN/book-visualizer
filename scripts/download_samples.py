"""Download public-domain test novels from Project Gutenberg into data/."""

from pathlib import Path
from urllib.request import urlopen

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# file name -> Project Gutenberg plain-text URL
SAMPLES = {
    "great_expectations.txt": "https://www.gutenberg.org/cache/epub/1400/pg1400.txt",  # the website's sample book
    "pride_and_prejudice.txt": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
    # famous books with very different settings and weather, to try the Story road with
    "alice_in_wonderland.txt": "https://www.gutenberg.org/cache/epub/11/pg11.txt",
    "a_christmas_carol.txt": "https://www.gutenberg.org/cache/epub/46/pg46.txt",
    "the_wonderful_wizard_of_oz.txt": "https://www.gutenberg.org/cache/epub/55/pg55.txt",
    "the_call_of_the_wild.txt": "https://www.gutenberg.org/cache/epub/215/pg215.txt",
    "treasure_island.txt": "https://www.gutenberg.org/cache/epub/120/pg120.txt",
    "the_hound_of_the_baskervilles.txt": "https://www.gutenberg.org/cache/epub/2852/pg2852.txt",
    "frankenstein.txt": "https://www.gutenberg.org/cache/epub/84/pg84.txt",
    "wuthering_heights.txt": "https://www.gutenberg.org/cache/epub/768/pg768.txt",
    "dracula.txt": "https://www.gutenberg.org/cache/epub/345/pg345.txt",
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
