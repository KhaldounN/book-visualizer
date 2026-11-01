"""Find a book's characters from the names spaCy tagged as PERSON.

spaCy finds names ("Darcy") but not who they belong to. This module:
1. reads the title in front of each name: "Mr. Darcy" and "Miss Darcy" are
   different people,
2. drops places spaCy mistook for people ("went to Meryton"),
3. groups the different ways of naming someone into one character:
   "Elizabeth", "Miss Elizabeth" and "Elizabeth Bennet".
"""

import re
from collections import Counter
from dataclasses import dataclass, field

from .models import Character, EntityCount, Mention, Sentence

MIN_MENTIONS = 5  # rarer names are usually spaCy mistakes or walk-on parts

# lowercase title -> how it is displayed
TITLES = {
    "mr": "Mr.", "mrs": "Mrs.", "miss": "Miss", "ms": "Ms.", "lady": "Lady",
    "lord": "Lord", "sir": "Sir", "dr": "Dr.", "doctor": "Dr.",
    "colonel": "Colonel", "captain": "Captain", "aunt": "Aunt", "uncle": "Uncle",
    "professor": "Professor", "rev": "Rev.",
}
_TITLE_BEFORE = re.compile(
    r"\b(" + "|".join(sorted(TITLES, key=len, reverse=True)) + r")\.?\s+$", re.IGNORECASE
)
_WORD_BEFORE = re.compile(r"(\w+)\W*$")

# Words that come before places far more often than before people
PLACE_CUES = {"in", "at", "from", "near", "into", "towards", "the"}
PLACE_CUE_SHARE = 0.25
PLACE_LABELS = {"GPE", "LOC", "FAC", "ORG", "NORP"}
# Non-person entity types worth listing in the results
OTHER_LABELS = PLACE_LABELS | {"EVENT", "WORK_OF_ART"}


@dataclass
class _Name:
    """One PERSON entity, split into an optional title and name words."""

    sentence_index: int
    start: int  # includes the title, if any
    end: int
    title: str | None
    words: tuple[str, ...]

    @property
    def key(self) -> tuple[str | None, tuple[str, ...]]:
        return self.title, tuple(w.lower() for w in self.words)

    @property
    def display(self) -> str:
        return " ".join(((self.title,) if self.title else ()) + self.words)


@dataclass
class _Cluster:
    """A group of name forms that we believe refer to the same person."""

    titles: set[str] = field(default_factory=set)
    tokens: set[str] = field(default_factory=set)
    first_names: set[str] = field(default_factory=set)
    multi: list[tuple[str, ...]] = field(default_factory=list)  # forms with 2+ words
    forms: Counter = field(default_factory=Counter)  # display form -> count

    @property
    def count(self) -> int:
        return sum(self.forms.values())

    def allows(self, title: str | None) -> bool:
        return title is None or not self.titles or title in self.titles


def _clean_name(raw: str) -> str:
    """spaCy sometimes runs past the name: "Jane Bennet,--she" -> "Jane Bennet"."""
    return re.split(r"[,;:!?()\"]|--", raw)[0].strip()


def _parse(entity, text: str, sentence_index: int) -> _Name | None:
    raw = _clean_name(entity.text)
    words = raw.split()
    start = entity.start
    end = entity.start + len(raw)
    title = None
    if words and words[0].lower().rstrip(".") in TITLES:
        title = TITLES[words[0].lower().rstrip(".")]
        words = words[1:]
    else:
        window = text[max(0, start - 12):start]
        found = _TITLE_BEFORE.search(window)
        if found:
            title = TITLES[found.group(1).lower()]
            start -= len(window) - found.start()

    words = [re.sub(r"'s?$", "", w).strip(".'") for w in words]
    # Letter headings are often in capitals: "CAROLINE BINGLEY" -> "Caroline Bingley"
    words = [w.title() if w.isupper() and len(w) > 1 else w for w in words if w]
    # Names start and end with a capital ("Catherine de Bourgh" is fine)
    if not words or not (words[0][0].isupper() and words[-1][0].isupper()):
        return None
    return _Name(sentence_index, start, end, title, tuple(words))


def _contains(longer: tuple[str, ...], shorter: tuple[str, ...]) -> bool:
    n = len(shorter)
    return any(longer[i:i + n] == shorter for i in range(len(longer) - n + 1))


def _candidates(clusters: list[_Cluster], title: str | None, tokens: tuple[str, ...]) -> list[_Cluster]:
    if len(tokens) > 1:
        # "Catherine de Bourgh" belongs with "Lady Catherine de Bourgh"
        return [
            c for c in clusters
            if c.allows(title) and any(_contains(m, tokens) or _contains(tokens, m) for m in c.multi)
        ]
    token = tokens[0]
    if title:
        # "Miss Elizabeth" joins "Elizabeth Bennet" (a first name), but a title
        # with a surname is its own person: "Mr. Bennet", "Mrs. Bennet" and
        # "Miss Bennet" are three different people
        return [c for c in clusters if token in c.first_names and c.allows(title)]
    # A bare "Darcy" can belong to anyone with that name; the caller picks the biggest
    return [c for c in clusters if token in c.tokens]


def _add(cluster: _Cluster, key: tuple, display: str, count: int) -> None:
    title, tokens = key
    if title:
        cluster.titles.add(title)
    cluster.tokens.update(tokens)
    if len(tokens) > 1:
        cluster.multi.append(tokens)
        cluster.first_names.update(tokens[:-1])
    cluster.forms[display] += count


def _group(forms: Counter, displays: dict) -> dict:
    """Assign every name form to a cluster. Returns form key -> cluster."""
    # Most specific forms first: full names, then titled names, then bare names
    order = sorted(forms, key=lambda k: (len(k[1]) < 2, k[0] is None, -forms[k]))
    clusters: list[_Cluster] = []
    assignment = {}
    for key in order:
        candidates = _candidates(clusters, *key)
        if candidates:
            cluster = max(candidates, key=lambda c: c.count)
        else:
            cluster = _Cluster()
            clusters.append(cluster)
        _add(cluster, key, displays[key], forms[key])
        assignment[key] = cluster

    # A group made only of full names, like "Mr. Fitzwilliam Darcy", belongs
    # to the matching "Mr. Darcy" group, if there is exactly one
    titled_surname = {}
    for (title, tokens), cluster in assignment.items():
        if title and len(tokens) == 1:
            titled_surname.setdefault((title, tokens[0]), set()).add(id(cluster))
    by_id = {id(c): c for c in clusters}
    for cluster in clusters:
        keys = [k for k, c in assignment.items() if c is cluster]
        if any(len(tokens) == 1 for _, tokens in keys):
            continue
        targets = {
            target
            for title, tokens in keys
            for (t, surname), ids in titled_surname.items()
            if surname == tokens[-1] and (title is None or title == t)
            for target in ids
        }
        if len(targets) == 1:
            target = by_id[targets.pop()]
            for key in keys:
                _add(target, key, displays[key], forms[key])
                assignment[key] = target
    return assignment


def find_characters(
    sentences: list[Sentence], text: str
) -> tuple[list[Character], list[Mention], list[EntityCount]]:
    """Return the characters (most mentioned first), every place they are
    named, and the other entities (places, organizations, ...)."""
    # spaCy's labels are unreliable for old-fashioned names: it tags Charlotte
    # as a city most of the time. So any name tagged PERSON at least once is a
    # candidate everywhere it appears, and context decides below.
    person_texts = {e.text for s in sentences for e in s.entities if e.label == "PERSON"}
    names: list[_Name] = []
    for s in sentences:
        for e in s.entities:
            if e.label == "PERSON" or (e.label in PLACE_LABELS and e.text in person_texts):
                if name := _parse(e, text, s.index):
                    names.append(name)

    # Places mistaken for people: count how often each untitled name comes
    # after a place word ("in Meryton", "the Longbourn family")
    cue_counts: Counter = Counter()
    untitled_counts: Counter = Counter()
    for n in names:
        if n.title is None:
            untitled_counts[n.display] += 1
            before = _WORD_BEFORE.search(text[max(0, n.start - 15):n.start])
            if before and before.group(1).lower() in PLACE_CUES:
                cue_counts[n.display] += 1
    places = {
        name for name, count in untitled_counts.items()
        if cue_counts[name] >= PLACE_CUE_SHARE * count
    }
    names = [n for n in names if n.title or n.display not in places]

    forms = Counter(n.key for n in names)
    displays = {}
    for n in names:
        displays.setdefault(n.key, n.display)
    assignment = _group(forms, displays)

    # Keep groups with enough mentions, biggest first
    kept = sorted(
        {id(c): c for c in assignment.values() if c.count >= MIN_MENTIONS}.values(),
        key=lambda c: -c.count,
    )
    ids = {id(c): i for i, c in enumerate(kept)}
    characters = [
        Character(
            id=i,
            name=c.forms.most_common(1)[0][0],
            aliases=[form for form, _ in c.forms.most_common()],
            mentions=c.count,
        )
        for i, c in enumerate(kept)
    ]
    mentions = [
        Mention(
            character_id=ids[id(assignment[n.key])],
            sentence_index=n.sentence_index,
            start=n.start,
            end=n.end,
            text=text[n.start:n.end],
        )
        for n in names
        if id(assignment[n.key]) in ids
    ]
    person_names = {n.display for n in names if n.title is None}
    return characters, mentions, _other_entities(sentences, person_names, places)


def _other_entities(
    sentences: list[Sentence], person_names: set[str], places: set[str]
) -> list[EntityCount]:
    labels: dict[str, Counter] = {}
    for s in sentences:
        for e in s.entities:
            name = _clean_name(e.text)
            if not name or not name[0].isupper() or name in person_names:
                continue
            if e.label in OTHER_LABELS:
                labels.setdefault(name, Counter())[e.label] += 1
            elif e.label == "PERSON" and name in places:  # a place mistaken for a person
                labels.setdefault(name, Counter())["LOC"] += 1
    counts = [
        EntityCount(name=name, label=c.most_common(1)[0][0], count=sum(c.values()))
        for name, c in labels.items()
    ]
    return sorted((e for e in counts if e.count >= 2), key=lambda e: -e.count)
