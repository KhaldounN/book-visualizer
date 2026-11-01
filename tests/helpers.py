import re

from analyzer.models import Entity, Sentence


def make_sentences(lines: list[str], chapters: list[int] | None = None) -> tuple[list[Sentence], str]:
    """One sentence per line. Words in [brackets] become entities, e.g.
    "[Darcy|PERSON]" -> entity "Darcy" with label PERSON."""
    text, sentences = "", []
    for i, line in enumerate(lines):
        start = len(text)
        entities, plain, pos = [], "", 0
        for m in re.finditer(r"\[([^|\]]+)\|(\w+)\]", line):
            plain += line[pos:m.start()]
            entity_start = start + len(plain)
            plain += m.group(1)
            entities.append(Entity(m.group(1), m.group(2), entity_start, entity_start + len(m.group(1))))
            pos = m.end()
        plain += line[pos:]
        chapter = chapters[i] if chapters else 0
        sentences.append(Sentence(i, plain, start, start + len(plain), chapter, entities))
        text += plain + "\n"
    return sentences, text
