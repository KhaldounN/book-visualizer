"""Turn an uploaded .txt file into clean text: one paragraph per line,
paragraphs separated by a blank line."""

import re

_UNITS = "one|two|three|four|five|six|seven|eight|nine"
_NUMBER_WORDS = (  # one ... nineteen, twenty, twenty-one ... ninety-nine ("CHAPTER TWENTY-ONE")
    rf"(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[- ](?:{_UNITS}))?|"
    "ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|" + _UNITS
)
# A whole line like "CHAPTER II.", "Chapter 12", "Chapter One: The Ball".
# The {0,140} limit stops a normal sentence starting with "Chapter" from matching
# (and still allows Dickens's long titles: "CHAPTER II. TREATS OF OLIVER TWIST'S GROWTH, ...").
CHAPTER_HEADING = re.compile(
    rf"^[ \t]*chapter\s+(?:\d+|[ivxlcdm]+|{_NUMBER_WORDS})\b[^\n]{{0,140}}$",
    re.IGNORECASE | re.MULTILINE,
)

_GUTENBERG_START = re.compile(r"^\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG.*$", re.MULTILINE)
_GUTENBERG_END = re.compile(r"^\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG", re.MULTILINE)
_ILLUSTRATION = re.compile(r"\[Illustration[^\]]*\]", re.DOTALL)
_SMART_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


def decode(data: bytes) -> str:
    """Bytes from an uploaded file -> text. Most files are UTF-8; older
    Windows files are often cp1252, which accepts any byte."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def strip_gutenberg(text: str) -> str:
    """Keep only the book between Project Gutenberg's START and END markers."""
    start = _GUTENBERG_START.search(text)
    if start:
        text = text[start.end():]
    end = _GUTENBERG_END.search(text)
    if end:
        text = text[: end.start()]
    return text


def _is_the_end(paragraph: str) -> bool:
    return " ".join(paragraph.split()).upper().rstrip(".") == "THE END"


def _replace_illustration(match: re.Match) -> str:
    # Some editions hide a chapter heading or "THE END" inside the illustration
    # caption, e.g. "[Illustration: PRIDE AND PREJUDICE  Chapter I.]". Keep them.
    caption = match.group(0)[len("[Illustration"):].strip(" :]\n")
    if _is_the_end(caption):
        return "\n\nTHE END\n\n"
    heading = CHAPTER_HEADING.search(match.group(0).rstrip("]"))
    return f"\n\n{heading.group(0).strip()}\n\n" if heading else ""


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_gutenberg(text)
    text = _ILLUSTRATION.sub(_replace_illustration, text)
    text = text.replace("_", "")  # Gutenberg marks _italics_ with underscores
    text = text.translate(_SMART_QUOTES)

    # Plain-text books wrap lines at ~70 characters. Join the lines of each
    # paragraph back together so sentences are not cut in half.
    paragraphs = []
    for block in re.split(r"\n\s*\n", text):
        paragraph = " ".join(block.split())
        if paragraph:
            paragraphs.append(paragraph)

    # Drop back matter (printer's notes, adverts) after a closing "THE END".
    # Only look in the second half, so a contents-page entry is never used.
    for i in range(len(paragraphs) - 1, len(paragraphs) // 2, -1):
        if _is_the_end(paragraphs[i]):
            paragraphs = paragraphs[:i]
            break
    return "\n\n".join(paragraphs)


def load_text(data: bytes) -> str:
    return clean_text(decode(data))


def _header_field(header: str, name: str) -> str | None:
    """A "Name: value" line from the Gutenberg header. Long values continue
    on the next lines, indented: "Title: The Adventures\\n    of Tom Sawyer"."""
    match = re.search(rf"^{name}:[ \t]*(.+(?:\n[ \t]+\S.*)*)", header, re.MULTILINE)
    if not match:
        return None
    lines = [" ".join(line.split()) for line in match.group(1).split("\n")]
    # a continuation that starts with a capital after a finished line is a subtitle
    # ("Black Beauty" / "The autobiography of a horse"); "The Adventures" / "of Tom Sawyer" is one title
    kept = lines[:1]
    for line in lines[1:]:
        if line[:1].isupper() and kept[-1].split()[-1].lower() not in ("of", "the", "and", "a", "an", "in", "to", "or"):
            break
        kept.append(line)
    return " ".join(kept)


def _title_from_filename(filename: str | None) -> str:
    """ "pride_and_prejudice.txt" -> "Pride And Prejudice" """
    if not filename:
        return "Untitled book"
    stem = re.sub(r"\.txt$", "", filename, flags=re.IGNORECASE)
    words = re.sub(r"[_\-]+", " ", stem).strip()
    return words.title() if words.islower() else words or "Untitled book"


def book_info(data: bytes, filename: str | None = None) -> tuple[str, str | None]:
    """(title, author) from a Project Gutenberg header, falling back to the
    file name. The author is None when unknown."""
    text = decode(data).replace("\r\n", "\n")
    start = _GUTENBERG_START.search(text)
    header = text[: start.start()] if start else text[:3000]
    return _header_field(header, "Title") or _title_from_filename(filename), _header_field(header, "Author")
