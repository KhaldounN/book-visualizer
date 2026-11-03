r"""Add word-type counts (verbs, adjectives, ...) to books analysed before they were stored.

The pace measures' "action vs. description" needs them. Instead of re-analysing every book
(~10 min each), this runs only spaCy's word tagger over the saved sentences (~1 min a book)
and saves the result in place. Books that already have them are skipped.

    .\.venv\Scripts\python.exe scripts\add_word_types.py
"""

import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import spacy  # noqa: E402

from analyzer.pipeline import ANALYSIS_VERSION, SPACY_MODEL  # noqa: E402
from analyzer.segment import word_types  # noqa: E402


def main() -> None:
    nlp = None
    for path in sorted((ROOT / "results").glob(f"v{ANALYSIS_VERSION}-*.pkl"), key=lambda p: p.stat().st_size):
        analysis = pickle.loads(path.read_bytes())
        if all(getattr(s, "tags", None) is not None for s in analysis.sentences):
            continue
        if nlp is None:  # only the tagger: no parser or entity finder, so it's fast
            nlp = spacy.load(SPACY_MODEL, disable=["parser", "ner", "lemmatizer"])
        start = time.time()
        for sentence, doc in zip(analysis.sentences, nlp.pipe((s.text for s in analysis.sentences), batch_size=256)):
            sentence.tags = word_types(doc)
        path.write_bytes(pickle.dumps(analysis))
        print(f"{analysis.title[:40]:40} {len(analysis.sentences):6} sentences  {time.time() - start:.0f} s")


if __name__ == "__main__":
    main()
