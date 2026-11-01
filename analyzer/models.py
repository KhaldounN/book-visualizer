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
    emotions: dict[str, float] = field(default_factory=dict)  # emotion family (and "neutral") -> score
    fine: dict[str, float] = field(default_factory=dict)  # fine emotion (e.g. "guilt") -> score, only those present


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
    label: str  # spaCy's label, e.g. GPE
    count: int
    kind: str = "other"  # place / organization / group / other
    chapter_counts: list[int] = field(default_factory=list)  # [chapter] -> mentions


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
    # average emotion mix of their shared moments, overall and per third of the book
    emotions: dict[str, float] = field(default_factory=dict)
    emotions_by_part: list[dict[str, float]] = field(default_factory=list)


@dataclass
class ChapterEvent:
    """What a chapter is about, found by local models (see chapter_events.py)."""

    theme: str  # one word from chapter_events.THEMES, e.g. "Proposal" (or the top keyword)
    strength: float  # how much the theme stands out in this chapter (above 2 = clearly; 0 = no model used)
    event: str  # the chapter's most telling sentence, shortened
    keywords: list[str]  # the words most typical of the chapter


@dataclass
class KeyMoment:
    """A passage whose sentences are, on average, especially dark or bright."""

    first: int  # sentence index where the passage starts
    last: int  # sentence index where it ends (included)
    chapter: int
    score: float  # average sentiment of the passage


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
    title: str = "Untitled book"
    author: str | None = None
    chapter_emotions: list[dict[str, float]] = field(default_factory=list)  # [chapter] -> mix
    character_emotions: list[dict[str, float]] = field(default_factory=list)  # [character] -> mix
    chapter_fine: list[dict[str, float]] = field(default_factory=list)  # [chapter] -> fine emotion mix
    character_fine: list[dict[str, float]] = field(default_factory=list)  # [character] -> fine emotion mix
    # [chapter] -> its theme and event. A plain None default (not a list
    # factory) so analyses saved before this field existed still load:
    # unpickling falls back to the class default.
    chapter_events: list[ChapterEvent] | None = None
