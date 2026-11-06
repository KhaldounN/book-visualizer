r"""Analyze every famous book in data/ ahead of time, so the website opens them all instantly.

    .venv\Scripts\python.exe scripts\analyze_library.py

Safe to leave running for hours and to stop and start again:
- shortest books first, so many are ready soon; books already analyzed are skipped;
- each book is analyzed by the website's own worker (analyzer/worker.py, via app/jobs.py) in its own
  low-priority process, so if one runs out of memory only that book fails; it is tried again at the end;
- before each book it waits until Windows can spare the memory the book needs, and it never runs
  while the website is reading a book itself (one analysis at a time);
- after each book it saves the book's comparison summary (analyzer/library.py).
Progress goes to the console and to results/library_progress.log.
"""

import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))

import jobs  # noqa: E402  (app/jobs.py: no Streamlit, no AI libraries)
from analyzer.library import saved_summary  # noqa: E402
from analyzer.version import ANALYSIS_VERSION  # noqa: E402

DATA, CACHE = ROOT / "data", ROOT / "results"
LOG = CACHE / "library_progress.log"
TRIES = 2


def say(text: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M')}  {text}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as log:
        log.write(line + "\n")


def wait_for_room(need_mb: int, name: str) -> None:
    """Wait while the website is reading a book, or while there isn't enough memory."""
    told = False
    while True:
        other = jobs.running()
        free = jobs.available_mb()
        if other is None and (free is None or free >= need_mb):
            return
        if not told:
            why = (f"the website is reading another book" if other
                   else f"needs {need_mb / 1024:.1f} GB, {free / 1024:.1f} GB free")
            say(f"waiting before {name}: {why}")
            told = True
        time.sleep(60)


def main() -> None:
    CACHE.mkdir(exist_ok=True)
    books = sorted(DATA.glob("*.txt"), key=lambda p: p.stat().st_size)
    queue = [(path, 1) for path in books]
    done = failed = 0
    say(f"library: {len(books)} books")
    while queue:
        path, attempt = queue.pop(0)
        data = path.read_bytes()
        key = hashlib.sha256(data).hexdigest()
        result = CACHE / f"v{ANALYSIS_VERSION}-{key}.pkl"
        if not result.exists():
            wait_for_room(jobs.needed_mb(len(data)), path.name)
            say(f"reading {path.name} ({len(data) // 1024} KB), try {attempt}")
            started = time.time()
            jobs.start(key, result, data, path.name, book=path)
            while (status := jobs.status(key)) and status.get("state") == "running":
                time.sleep(15)
            if not result.exists():
                reason = (status or {}).get("reason", "unknown")
                say(f"  failed: {path.name} ({reason})" + (", will try again at the end" if attempt < TRIES else ""))
                if attempt < TRIES:
                    queue.append((path, attempt + 1))
                else:
                    failed += 1
                continue
            jobs.forget(key)
            say(f"  done in {(time.time() - started) / 60:.1f} min")
        saved_summary(CACHE, key)  # the comparison numbers, so the website never has to work them out
        done += 1
    say(f"finished: {done} books ready, {failed} failed")


if __name__ == "__main__":
    main()
