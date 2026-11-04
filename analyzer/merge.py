"""Merge characters the analysis kept apart, e.g. "Lizzy" into "Elizabeth".

Nicknames and married names need knowledge of the story, so the reader
decides; this recomputes everything that depends on who is who.
"""

from collections import Counter
from dataclasses import replace

from .models import BookAnalysis, Character, Mention
from .progression import emotions_by_character, mentions_by_chapter, sentiment_by_chapter
from .relationships import find_relationships


def merge_characters(analysis: BookAnalysis, merges: list[tuple[str, str]]) -> BookAnalysis:
    """Apply (merge this name, into this name) pairs; returns a new analysis.
    Character ids are renumbered so they stay 0..n-1, most mentioned first."""
    by_name = {c.name: c for c in analysis.characters}
    target = {c.id: c.id for c in analysis.characters}
    for source, into in merges:
        if source in by_name and into in by_name and source != into:
            target[by_name[source].id] = by_name[into].id
    # follow chains: Lizzy -> Eliza -> Elizabeth
    def root(character_id: int) -> int:
        seen = set()
        while target[character_id] != character_id and character_id not in seen:
            seen.add(character_id)
            character_id = target[character_id]
        return character_id

    counts = Counter(root(m.character_id) for m in analysis.mentions)
    survivors = sorted({root(c.id) for c in analysis.characters}, key=lambda i: -counts[i])
    new_id = {old: new for new, old in enumerate(survivors)}

    characters = []
    for old in survivors:
        main = analysis.characters[old]
        aliases = list(main.aliases)
        for c in analysis.characters:
            if c.id != old and root(c.id) == old:
                aliases += [a for a in c.aliases if a not in aliases]
        characters.append(Character(new_id[old], main.name, aliases, counts[old]))

    mentions = [replace(m, character_id=new_id[root(m.character_id)]) for m in analysis.mentions]
    return _recompute(analysis, characters, mentions)


def _recompute(analysis: BookAnalysis, characters: list[Character], mentions: list[Mention]) -> BookAnalysis:
    sentences, n_chapters = analysis.sentences, len(analysis.chapters)
    return replace(
        analysis,
        characters=characters,
        mentions=mentions,
        relationships=find_relationships(sentences, mentions, n_chapters),
        mentions_by_chapter=mentions_by_chapter(mentions, sentences, len(characters), n_chapters),
        sentiment_by_chapter=sentiment_by_chapter(mentions, sentences, len(characters), n_chapters),
        character_emotions=emotions_by_character(mentions, sentences, len(characters)),
        character_fine=emotions_by_character(mentions, sentences, len(characters), "fine"),
    )


# Common English nicknames -> the full first name they come from (for merge suggestions only:
# nicknames are never merged automatically, the reader decides)
NICKNAMES = {
    "lizzy": "elizabeth", "lizzie": "elizabeth", "liz": "elizabeth", "eliza": "elizabeth", "bess": "elizabeth",
    "bessie": "elizabeth", "bessy": "elizabeth", "betsy": "elizabeth", "beth": "elizabeth", "kitty": "catherine",
    "kate": "catherine", "cathy": "catherine", "jem": "james", "jemmy": "james", "jim": "james", "jamie": "james",
    "bob": "robert", "bobby": "robert", "rob": "robert", "bill": "william", "billy": "william", "will": "william",
    "dick": "richard", "tom": "thomas", "tommy": "thomas", "ned": "edward", "ted": "edward", "teddy": "edward",
    "nell": "ellen", "nelly": "ellen", "meg": "margaret", "maggie": "margaret", "peggy": "margaret",
    "polly": "mary", "molly": "mary", "sally": "sarah", "fanny": "frances", "harry": "henry", "jack": "john",
    "johnny": "john", "charley": "charles", "charlie": "charles", "joe": "joseph", "sam": "samuel",
    "ben": "benjamin", "fred": "frederick", "freddy": "frederick", "sophy": "sophia", "nan": "anne",
    "nancy": "anne", "annie": "anne", "jenny": "jane", "jo": "josephine", "dolly": "dorothy", "tony": "anthony",
    "nick": "nicholas", "pip": "philip", "matty": "matthew", "phil": "philip", "georgie": "georgiana",
}


def suggest_merges(characters: list[Character]) -> list[tuple[str, str]]:
    """(nickname character, full-name character) pairs that are probably one person: "Lizzy" and
    "Elizabeth". Only when the full name is used on its own (no title), so "Kitty" is never offered
    as "Lady Catherine". Most mentioned targets first."""
    by_first: dict[str, Character] = {}
    for c in sorted(characters, key=lambda c: -c.mentions):
        first = c.name.split()[0].lower()
        if first not in by_first and first not in NICKNAMES:
            by_first[first] = c
    pairs = []
    for c in characters:
        words = c.name.split()
        full = NICKNAMES.get(words[0].lower()) if len(words) == 1 else None
        if full and full in by_first and by_first[full].id != c.id:
            pairs.append((by_first[full].mentions, c.name, by_first[full].name))
    return [(nick, target) for _, nick, target in sorted(pairs, reverse=True)]
