"""Analyses that run in their own process (analyzer/worker.py), started and followed by the website.

Why: analyzing inside the website meant a book too big for the free memory (the Bible) took the
whole website down. Now only the worker can fail; the page explains why and stays up. The worker
also runs at a lower priority, so the website stays quick while it works, and it carries on if the
page is closed. One analysis runs at a time.
"""

import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "results" / "jobs"  # one status file per book (by its sha256 key)

# Memory an analysis needs, measured roughly: the biggest AI model and the libraries (~2.5 GB),
# plus the book's sentences and scores (grows with its length). The Bible needs about 4 GB.
BASE_MB, PER_TEXT_MB = 2500, 350


def needed_mb(size_bytes: int) -> int:
    return int(BASE_MB + size_bytes / 1e6 * PER_TEXT_MB)


class _Memory(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total_phys", ctypes.c_ulonglong),
                ("avail_phys", ctypes.c_ulonglong), ("total_commit", ctypes.c_ulonglong),
                ("avail_commit", ctypes.c_ulonglong), ("total_virtual", ctypes.c_ulonglong),
                ("avail_virtual", ctypes.c_ulonglong), ("avail_extended", ctypes.c_ulonglong)]


def available_mb() -> int | None:
    """Memory Windows can still promise to a program. With the page file off this is the real
    limit (it can be far below the 'free' memory Task Manager shows). None if unknown."""
    if sys.platform != "win32":
        return None
    status = _Memory()
    status.length = ctypes.sizeof(_Memory)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return int(min(status.avail_commit, status.avail_phys) / 2 ** 20)


def _alive(pid: int) -> bool:
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    # (on Windows os.kill(pid, 0) would END the process, so ask Windows instead)
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(handle)
    return code.value == 259  # STILL_ACTIVE


def status(key: str) -> dict | None:
    """The job's last status: state running / done / failed, step, fraction... A job whose
    process died without a word (Windows ends a program that runs out of memory) is 'failed'."""
    path = JOBS / f"{key}.json"
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if found.get("state") == "running" and not _alive(found.get("pid", 0)):
        found.update(state="failed", reason="crashed")
    return found


def running() -> tuple[str, dict] | None:
    """(key, status) of the analysis running now, if any."""
    for path in JOBS.glob("*.json") if JOBS.exists() else []:
        found = status(path.stem)
        if found and found.get("state") == "running":
            return path.stem, found
    return None


def start(key: str, result: Path, data: bytes, filename: str, book: Path | None = None) -> None:
    """Start analyzing in the background. `book` is the file when it is already on disk (a famous
    book); otherwise the bytes are written to a temporary file, deleted when the worker is done."""
    JOBS.mkdir(parents=True, exist_ok=True)
    extra = []
    if book is None:
        folder = JOBS / key
        folder.mkdir(exist_ok=True)
        book = folder / Path(filename).name  # keeps the name, the title's fallback
        book.write_bytes(data)
        extra = ["--delete-book"]
    status_file = JOBS / f"{key}.json"
    status_file.write_text(json.dumps({"state": "running", "step": "Starting", "fraction": 0.0, "pid": 0,
                                       "started": time.time(), "updated": time.time()}), encoding="utf-8")
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", PYTHONIOENCODING="utf-8")
    flags = 0
    if sys.platform == "win32":  # no console window, its own group (survives a website restart), lower priority
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.BELOW_NORMAL_PRIORITY_CLASS
    with open(JOBS / f"{key}.log", "w", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-m", "analyzer.worker", str(book), str(result), str(status_file),
                                    *extra], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=flags)
    # the pid right away, so the page can tell a crash from a slow start
    found = json.loads(status_file.read_text(encoding="utf-8"))
    if not found.get("pid"):
        found["pid"] = process.pid
        status_file.write_text(json.dumps(found), encoding="utf-8")


def forget(key: str) -> None:
    """Remove a finished or failed job's files (not the result)."""
    for path in (JOBS / f"{key}.json", JOBS / f"{key}.log"):
        path.unlink(missing_ok=True)
    shutil.rmtree(JOBS / key, ignore_errors=True)
