r"""Analyze every book in data/ ahead of time, so the website opens them instantly.

Saves each analysis where the website looks for it (results/v{version}-{sha256}.pkl,
the same as analyzing it on the site). Books already analyzed are skipped.
Run it from the project folder:  .venv\Scripts\python.exe scripts\analyze_samples.py
Shortest books first; a full novel takes about 10 minutes.
"""

import hashlib
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from analyzer.pipeline import ANALYSIS_VERSION, analyze  # noqa: E402

DATA_DIR, CACHE = ROOT / "data", ROOT / "results"


def main() -> None:
    CACHE.mkdir(exist_ok=True)
    for path in sorted(DATA_DIR.glob("*.txt"), key=lambda p: p.stat().st_size):
        data = path.read_bytes()
        saved = CACHE / f"v{ANALYSIS_VERSION}-{hashlib.sha256(data).hexdigest()}.pkl"
        if saved.exists():
            print(f"Already analyzed: {path.name}", flush=True)
            continue
        print(f"Analyzing {path.name} ({len(data) // 1024} KB) ...", flush=True)
        started = time.time()
        result = analyze(data, filename=path.name)
        saved.write_bytes(pickle.dumps(result))
        print(f"  done in {(time.time() - started) / 60:.1f} min: {result.title}", flush=True)


if __name__ == "__main__":
    main()
