"""Turn an uploaded .txt file into clean text: one paragraph per line,
paragraphs separated by a blank line."""

import re

_NUMBER_WORDS = (
    "one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
    "fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
)
# A whole line like "CHAPTER II.", "Chapter 12", "Chapter One: The Ball".
# The {0,80} limit stops a normal sentence starting with "Chapter" from matching.
CHAPTER_HEADING = re.compile(
    rf"^[ \t]*chapter\s+(?:\d+|[ivxlcdm]+|{_NUMBER_WORDS})\b[^\n]{{0,80}}$",
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
