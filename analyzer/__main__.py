"""Command line: python -m analyzer path/to/book.txt [--no-coref]"""

import argparse
import sys
from pathlib import Path

from .emotions import average_emotions
from .pipeline import analyze


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze the characters and sentiment of a novel.")
    parser.add_argument("book", type=Path, help="a .txt file")
    parser.add_argument("--no-coref", action="store_true", help="skip pronoun linking (faster)")
    parser.add_argument("--no-emotions", action="store_true", help="skip emotion detection (faster)")
    args = parser.parse_args()

    last = None

    def progress(step: str, fraction: float) -> None:
        nonlocal last
        shown = (step, round(fraction * 100))
        if shown != last:  # only redraw when the percentage changes
            print(f"\r{step + ':':24}{shown[1]:4}%", end="" if fraction < 1 else "\n", flush=True)
            last = shown

    result = analyze(args.book.read_bytes(), progress, use_coref=not args.no_coref, filename=args.book.name,
                     use_emotions=not args.no_emotions)
    names = {c.id: c.name for c in result.characters}
    print("\n")
    print(result.title + (f" by {result.author}" if result.author else ""))
    print(f"{len(result.chapters)} chapters, {len(result.sentences):,} sentences, "
          f"{len(result.characters)} characters, {len(result.mentions):,} mentions")
    print("Time: " + ", ".join(f"{step} {seconds:.0f}s" for step, seconds in result.timings.items()))

    book_mix = average_emotions([s.emotions for s in result.sentences])
    if book_mix:
        print("Emotions: " + ", ".join(f"{e} {p:.0%}" for e, p in sorted(book_mix.items(), key=lambda kv: -kv[1])))

    print("\nMost mentioned characters:")
    for c in sorted(result.characters, key=lambda c: -c.mentions)[:10]:
        print(f"  {c.mentions:5,}  {c.name}")

    print("\nStrongest relationships (times together, average tone, tone by quarter of the book):")
    quarters = [range(q * len(result.chapters) // 4, (q + 1) * len(result.chapters) // 4) for q in range(4)]
    for r in result.relationships[:10]:
        by_quarter = []
        for chapters in quarters:
            n = sum(r.chapter_counts[c] for c in chapters)
            tone = sum(r.chapter_sentiment[c] * r.chapter_counts[c] for c in chapters if r.chapter_counts[c])
            by_quarter.append(f"{tone / n:+.2f}" if n else "  -  ")
        print(f"  {r.count:4}  {r.sentiment:+.2f}  [{' '.join(by_quarter)}]  {names[r.source]} & {names[r.target]}")
        if any(r.emotions_by_part):
            # strongest emotion other than neutral in the early, middle and late book
            arc = [max((e for e in mix if e != "neutral"), key=mix.get) if mix else "-" for mix in r.emotions_by_part]
            print(f"{'':19}emotions: {' -> '.join(arc)}")

    ranked = sorted(range(len(result.chapters)), key=lambda c: result.chapter_sentiment[c])
    for label, chapters in (("darkest", ranked[:3]), ("brightest", ranked[-3:][::-1])):
        print(f"\nThe {label} chapters:")
        for c in chapters:
            print(f"  {result.chapter_sentiment[c]:+.2f}  {result.chapters[c].title}")


if __name__ == "__main__":
    sys.exit(main())
