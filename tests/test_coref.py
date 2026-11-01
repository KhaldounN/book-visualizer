"""Tests for linking pronouns to characters. A fake model stands in for
fastcoref, so the tests check our rules, not the model's guesses."""

import re

from analyzer import coref
from analyzer.models import Character, Mention
from helpers import make_sentences


class FakeResult:
    def __init__(self, clusters):
        self.clusters = clusters

    def get_clusters(self, as_strings=True):
        return self.clusters


class FakeModel:
    """Pretends to be fastcoref: each cluster is a list of phrases, and every
    whole-word occurrence of those phrases in the chunk is put in the group."""

    def __init__(self, clusters: list[list[str]]):
        self.clusters = clusters
        self.chunks_seen = []

    def predict(self, texts):
        chunk = texts[0]
        self.chunks_seen.append(chunk)
        result = []
        for phrases in self.clusters:
            spans = [
                (m.start(), m.end())
                for p in phrases
                for m in re.finditer(rf"(?<!\w){re.escape(p)}(?!\w)", chunk)
            ]
            if len(spans) > 1:
                result.append(sorted(spans))
        return [FakeResult(result)]


def setup(lines, characters, chapters=None):
    """Sentences, text and name mentions: every entity whose text matches a
    character's alias becomes a name mention of that character."""
    sentences, text = make_sentences(lines, chapters)
    names = [
        Mention(c.id, s.index, e.start, e.end, e.text)
        for s in sentences for e in s.entities
        for c in characters if e.text in c.aliases
    ]
    return sentences, text, names


ANNA = Character(0, "Anna", ["Anna"])
TOM = Character(1, "Mr. Tom", ["Mr. Tom", "Tom"])


def found_words(found, character):
    return [m.text for m in found if m.character_id == character.id]


def test_pronouns_are_linked_to_the_named_character():
    sentences, text, names = setup(
        ["[Anna|PERSON] smiled.", "She waved, and everyone looked at her."], [ANNA]
    )
    found = coref.resolve(text, sentences, [ANNA], names, FakeModel([["Anna", "She", "her"]]))
    assert found_words(found, ANNA) == ["She", "her"]
    assert [m.sentence_index for m in found] == [1, 1]
    assert all(m.source == "coref" and text[m.start:m.end] == m.text for m in found)


def test_dialogue_plural_and_address_words_are_skipped():
    sentences, text, names = setup(
        ["[Tom|PERSON] came in.", '"I am late, sir," he said.', "They sat down."], [TOM]
    )
    model = FakeModel([["Tom", "I", "sir", "he", "They"]])
    found = coref.resolve(text, sentences, [TOM], names, model)
    assert found_words(found, TOM) == ["he"]


def test_group_with_mixed_names_is_ignored():
    sentences, text, names = setup(["[Anna|PERSON] and [Tom|PERSON] met.", "She left."], [ANNA, TOM])
    found = coref.resolve(text, sentences, [ANNA, TOM], names, FakeModel([["Anna", "Tom", "She"]]))
    assert found == []


def test_group_without_known_names_is_ignored():
    sentences, text, names = setup(["The letter arrived.", "Nobody read it."], [ANNA])
    found = coref.resolve(text, sentences, [ANNA], names, FakeModel([["The letter", "it"]]))
    assert found == []


def test_pronoun_of_the_wrong_gender_is_dropped():
    # "Mr." tells us Tom is male, so the model's "she" must be a mistake
    sentences, text, names = setup(["[Tom|PERSON] smiled.", "He nodded and she waved."], [TOM])
    found = coref.resolve(text, sentences, [TOM], names, FakeModel([["Tom", "He", "she"]]))
    assert found_words(found, TOM) == ["He"]


def test_possessive_name_does_not_claim_the_phrase():
    # "Tom's sister" is about the sister, not about Tom
    sentences, text, names = setup(["[Tom|PERSON]'s sister arrived.", "She was tired."], [TOM])
    found = coref.resolve(text, sentences, [TOM], names, FakeModel([["Tom's sister", "She"]]))
    assert found == []


def test_chunks_stay_inside_chapters_and_carry_context(monkeypatch):
    monkeypatch.setattr(coref, "CHUNK_WORDS", 6)
    monkeypatch.setattr(coref, "CONTEXT_WORDS", 3)
    lines = ["one two three.", "four five six.", "seven eight nine.", "ten eleven twelve."]
    sentences, _ = make_sentences(lines, chapters=[0, 0, 0, 1])
    # (context start, own start, own end) in sentence numbers
    assert coref._chunks(sentences) == [(0, 0, 2), (1, 2, 3), (3, 3, 4)]


def test_context_is_read_but_not_counted_twice(monkeypatch):
    monkeypatch.setattr(coref, "CHUNK_WORDS", 4)
    monkeypatch.setattr(coref, "CONTEXT_WORDS", 4)
    sentences, text, names = setup(
        ["[Anna|PERSON] smiled at her friend.", "She then left the room."], [ANNA]
    )
    model = FakeModel([["Anna", "She", "her friend"]])
    found = coref.resolve(text, sentences, [ANNA], names, model)
    # the second chunk re-reads sentence 1 as context, so it can still see "Anna"
    assert len(model.chunks_seen) == 2 and "Anna" in model.chunks_seen[1]
    assert found_words(found, ANNA) == ["her friend", "She"]
