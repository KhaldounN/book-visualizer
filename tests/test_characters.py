"""Tests for the grouping rules, using hand-made entities so the results do
not depend on spaCy's guesses."""

from analyzer.characters import MIN_MENTIONS, find_characters
from helpers import make_sentences


def repeat(line: str, times: int = MIN_MENTIONS) -> list[str]:
    return [line] * times


def by_name(characters):
    return {c.name: c for c in characters}


def test_titles_separate_family_members():
    sentences, text = make_sentences(
        repeat("Mr. [Bennet|PERSON] laughed.") + repeat("Mrs. [Bennet|PERSON] cried.")
        + repeat("Miss [Bennet|PERSON] smiled.")
    )
    characters, _, _ = find_characters(sentences, text)
    assert set(by_name(characters)) == {"Mr. Bennet", "Mrs. Bennet", "Miss Bennet"}


def test_name_variants_are_grouped():
    sentences, text = make_sentences(
        ["[Elizabeth Bennet|PERSON] arrived."]
        + repeat("[Elizabeth|PERSON] laughed.")
        + ["Miss [Elizabeth|PERSON] sat down."]
        + repeat("Mr. [Darcy|PERSON] bowed.")
        + ["[Darcy|PERSON] left.", "Mr. [Fitzwilliam Darcy|PERSON] wrote."]
    )
    characters = by_name(find_characters(sentences, text)[0])
    assert set(characters) == {"Elizabeth", "Mr. Darcy"}
    assert characters["Elizabeth"].mentions == MIN_MENTIONS + 2
    assert set(characters["Mr. Darcy"].aliases) == {"Mr. Darcy", "Darcy", "Mr. Fitzwilliam Darcy"}


def test_title_is_part_of_the_mention_span():
    sentences, text = make_sentences(repeat("Then Mrs. [Bennet|PERSON]'s nerves failed."))
    _, mentions, _ = find_characters(sentences, text)
    assert {m.text for m in mentions} == {"Mrs. Bennet"}
    assert all(text[m.start:m.end] == m.text for m in mentions)


def test_places_tagged_as_people_are_dropped():
    sentences, text = make_sentences(
        repeat("They walked to [Meryton|PERSON].", 3) + repeat("All was quiet in [Meryton|PERSON].", 3)
        + repeat("[Anna|PERSON] smiled.")
    )
    characters, _, others = find_characters(sentences, text)
    assert set(by_name(characters)) == {"Anna"}
    assert ("Meryton", "LOC") in {(e.name, e.label) for e in others}


def test_person_mislabeled_as_place_still_counts():
    # spaCy often tags "Charlotte" as a city (GPE)
    sentences, text = make_sentences(
        ["[Charlotte|PERSON] spoke."] + repeat("[Charlotte|GPE] agreed.") + ["They went to [London|GPE]."] * 2
    )
    characters, _, others = find_characters(sentences, text)
    assert by_name(characters)["Charlotte"].mentions == MIN_MENTIONS + 1
    assert {e.name for e in others} == {"London"}


def test_trailing_punctuation_is_cut_from_names():
    sentences, text = make_sentences(repeat("Only [Jane Bennet,--she|PERSON] knew."))
    characters, mentions, _ = find_characters(sentences, text)
    assert [c.name for c in characters] == ["Jane Bennet"]
    assert {m.text for m in mentions} == {"Jane Bennet"}


def test_rare_names_are_ignored():
    sentences, text = make_sentences(repeat("[Anna|PERSON] smiled.", MIN_MENTIONS - 1))
    assert find_characters(sentences, text)[0] == []
