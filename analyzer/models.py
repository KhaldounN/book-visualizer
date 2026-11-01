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


@dataclass
class Character:
    id: int
    name: str  # display name, e.g. "Mr. Darcy"
    aliases: list[str]  # every way the book names them, most frequent first
    mentions: int = 0


@dataclass
class Mention:
    """One place in the text that refers to a character."""

    character_id: int
    sentence_index: int
    start: int
    end: int
    text: str
    source: str = "name"  # "name" (found by spaCy) or "coref" (a pronoun etc.)


@dataclass
class EntityCount:
    """A non-character entity (place, organization, ...) and how often it appears."""

    name: str
    label: str
    count: int


@dataclass
class Relationship:
    """Two characters who appear close together in the text."""

    source: int  # character id (always the smaller of the two)
    target: int
    count: int  # how many times they appear together
    sentiment: float  # average tone of the sentences where they appear together
    # the same two numbers per chapter, to show how the relationship changes
    chapter_counts: list[int] = field(default_factory=list)
    chapter_sentiment: list[float | None] = field(default_factory=list)


@dataclass
class BookAnalysis:
    """Everything the website needs to draw its charts."""

    chapters: list[Chapter]
    sentences: list[Sentence]
    characters: list[Character]
    mentions: list[Mention]
    entities: list[EntityCount]
    relationships: list[Relationship]
    chapter_sentiment: list[float]  # [chapter] -> average sentence sentiment
    mentions_by_chapter: list[list[int]]  # [character][chapter] -> mention count
    # [character][chapter] -> average sentiment of sentences mentioning them (None: absent)
    sentiment_by_chapter: list[list[float | None]]
    timings: dict[str, float] = field(default_factory=dict)  # step -> seconds
