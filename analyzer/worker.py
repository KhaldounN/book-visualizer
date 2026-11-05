"""Analyze one book in its own process, for the website.

    python -m analyzer.worker <book.txt> <result.pkl> <status.json> [--delete-book]

The website starts this instead of analyzing inside its own process: a long book (the Bible is
about 7 times a novel) can need more memory than the computer has, and then only this process
dies, never the website. Progress goes to the status file (written whole each time, so the
website never reads half a file); the result is saved where the website looks for it.
--delete-book removes the book file when done (an upload is only kept while it is analyzed).
"""

import json
import os
import pickle
import sys
import time
import traceback
from pathlib import Path


def write_status(path: Path, **status) -> None:
    status["updated"] = time.time()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(status), encoding="utf-8")
    os.replace(temporary, path)  # all at once, so a reader never sees half a file


def main() -> None:
    book, result, status_file = (Path(a) for a in sys.argv[1:4])
    delete_book = "--delete-book" in sys.argv
    started = time.time()
    base = {"pid": os.getpid(), "started": started, "book": book.name}
    write_status(status_file, state="running", step="Starting", fraction=0.0, **base)
    try:
        from .pipeline import analyze  # imported here: loading the AI libraries takes a while

        def progress(step: str, fraction: float) -> None:
            write_status(status_file, state="running", step=step, fraction=round(fraction, 4), **base)

        analysis = analyze(book.read_bytes(), progress, filename=book.name)
        temporary = result.with_suffix(".tmp")
        temporary.write_bytes(pickle.dumps(analysis))
        os.replace(temporary, result)
        write_status(status_file, state="done", step="Done", fraction=1.0, minutes=(time.time() - started) / 60, **base)
    except MemoryError:
        write_status(status_file, state="failed", reason="memory", step="Out of memory", fraction=0.0, **base)
    except ValueError as error:  # e.g. "No story text found in this file."
        write_status(status_file, state="failed", reason="book", error=str(error), step="Failed", fraction=0.0, **base)
    except Exception:  # noqa: BLE001 - anything else is reported to the page, not lost
        write_status(status_file, state="failed", reason="error", error=traceback.format_exc(limit=3)[-600:],
                     step="Failed", fraction=0.0, **base)
    finally:
        if delete_book:
            book.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
