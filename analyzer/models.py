"""Data containers shared by every step of the analysis.

All character positions (start/end) are offsets into the cleaned book text
returned by loaders.clean_text, so any step can point back to the exact words.
"""

from dataclasses import dataclass, field


@dataclass
class Entity:
    """A named thing spaCy found: a person, place, organization, ..."""

    text: str
    label: str  # spaCy label, e.g. PERSON, GPE (country/city), ORG
    start: int
    end: int


@dataclass
class Sentence:
    index: int
    text: str
    start: int
    end: int
    chapter: int
    entities: list[Entity] = field(default_factory=list)
    sentiment: float = 0.0  # -1 (very negative) to +1 (very positive)


@dataclass
class Chapter:
    index: int
    title: str
    start: int  # offset where the chapter's story text begins
