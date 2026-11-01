"""Split clean book text into chapters and sentences with spaCy."""

import re
from bisect import bisect_right
from typing import Callable

from spacy.language import Language

from .loaders import CHAPTER_HEADING
from .models import Chapter, Entity, Sentence

# Used when a book has no "Chapter ..." headings
FALLBACK_PARTS = 50

ProgressCallback = Callable[[int, int], None]  # (done, total)


def find_chapters(text: str) -> list[Chapter]:
    return [
        Chapter(index=i, title=m.group(0).strip(), start=m.end())
        for i, m in enumerate(CHAPTER_HEADING.finditer(text))
    ]


def _story_paragraphs(text: str, chapters: list[Chapter]) -> list[tuple[int, str]]:
    """(offset, paragraph) pairs, skipping chapter headings and any front matter
    (title page, preface, contents) before the first chapter."""
    heading_starts = {m.start() for m in CHAPTER_HEADING.finditer(text)}
    first = chapters[0].start if chapters else 0
    return [
        (m.start(), m.group(0))
        for m in re.finditer(r"[^\n]+", text)
        if m.start() >= first and m.start() not in heading_starts
    ]


def split_sentences(
    text: str, nlp: Language, progress: ProgressCallback | None = None
) -> tuple[list[Sentence], list[Chapter]]:
    """Return every story sentence (with the entities spaCy found in it) and
    the chapters. Books without headings are cut into equal parts."""
    chapters = find_chapters(text)
    chapter_starts = [c.start for c in chapters]
    paragraphs = _story_paragraphs(text, chapters)

    sentences: list[Sentence] = []
    # nlp.pipe processes paragraphs in batches, which is much faster than one by one
    docs = nlp.pipe((p for _, p in paragraphs), batch_size=64)
    for done, ((offset, _), doc) in enumerate(zip(paragraphs, docs), start=1):
        chapter = max(bisect_right(chapter_starts, offset) - 1, 0)
        for sent in doc.sents:
            if not sent.text.strip():
                continue
            sentences.append(
                Sentence(
                    index=len(sentences),
                    text=sent.text,
                    start=offset + sent.start_char,
                    end=offset + sent.end_char,
                    chapter=chapter,
                    entities=[
                        Entity(e.text, e.label_, offset + e.start_char, offset + e.end_char)
                        for e in sent.ents
                    ],
                )
            )
        if progress and done % 50 == 0:
            progress(done, len(paragraphs))

    if not chapters:
        chapters = _equal_parts(sentences)
    return sentences, chapters


def _equal_parts(sentences: list[Sentence]) -> list[Chapter]:
    """Assign sentences to FALLBACK_PARTS equal-sized parts."""
    if not sentences:
        return []
    parts = min(FALLBACK_PARTS, len(sentences))
    chapters = []
    for s in sentences:
        s.chapter = s.index * parts // len(sentences)
        if s.chapter == len(chapters):
            chapters.append(Chapter(index=s.chapter, title=f"Part {s.chapter + 1}", start=s.start))
    return chapters
