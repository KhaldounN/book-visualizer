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
    )
