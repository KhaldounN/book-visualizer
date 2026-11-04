import re

from analyzer.dialogue import (
    chapter_dialogue_share, find_lines, paragraphs, signature_words, strongest_lines, who_talks_to_whom,
    words_by_chapter, words_spoken,
)
from analyzer.models import Mention, Sentence

CAST = {"Elizabeth": 0, "Darcy": 1, "Jane": 2, "she": 0, "he": 1}


def book(*paras: list[str], chapters: list[int] | None = None, tone: dict[str, float] | None = None):
    """Sentences laid out like the cleaned text: one space between sentences, a blank line
    between paragraphs. Names (and "she" = Elizabeth, "he" = Darcy) become mentions."""
    text, sentences, mentions = "", [], []
    for p, para in enumerate(paras):
        if text:
            text += "\n\n"
        for k, sent in enumerate(para):
            if k:
                text += " "
            start = len(text)
            text += sent
            i = len(sentences)
            sentences.append(Sentence(i, sent, start, len(text), chapters[p] if chapters else 0,
                                      sentiment=(tone or {}).get(sent, 0.0)))
            for m in re.finditer(r"\b(" + "|".join(CAST) + r")\b", sent):
                mentions.append(Mention(CAST[m.group(1)], i, start + m.start(), start + m.end(), m.group(1)))
    return sentences, mentions, text


def test_paragraphs_come_from_the_gaps_between_sentences():
    sentences, _, _ = book(["One.", "Two."], ["Three."], ["Four."], chapters=[0, 0, 1])
    assert paragraphs(sentences) == [[0, 1], [2], [3]]


def test_a_speech_verb_next_to_a_name_gives_the_speaker():
    sentences, mentions, text = book(['"I am quite well," said Elizabeth.'], ['Darcy replied, "So am I."'])
    first, second = find_lines(sentences, mentions)
    assert (first.text, first.speaker, first.how) == ("I am quite well,", 0, "said")
    assert text[first.start:first.end] == first.text  # offsets point into the text
    assert (second.text, second.speaker) == ("So am I.", 1)
    assert (first.listener, second.listener) == (1, 0)


def test_a_pronoun_speaker_is_marked_as_less_sure():
    sentences, mentions, _ = book(['"I am quite well," said she.'])
    for m in mentions:
        m.source = "coref"
    line = find_lines(sentences, mentions)[0]
    assert (line.speaker, line.how) == (0, "pronoun")


def test_names_inside_the_quote_are_not_the_speaker():
    sentences, mentions, _ = book(['"Darcy is proud," said Jane.'])
    assert find_lines(sentences, mentions)[0].speaker == 2


def test_her_father_is_not_her():
    sentences, mentions, _ = book(['"Be quiet," said her father.'])
    assert find_lines(sentences, mentions)[0].speaker is None


def test_a_quote_split_by_its_speaker_is_one_turn():
    sentences, mentions, _ = book(['"Well," said Jane, "I hope so."'])
    lines = find_lines(sentences, mentions)
    assert [line.text for line in lines] == ["Well,", "I hope so."]
    assert {line.speaker for line in lines} == {2}
    from analyzer.dialogue import whole_turns
    (turn,) = whole_turns(lines)
    assert turn.text == "Well, I hope so." and turn.speaker == 2


def test_narration_before_the_quote_names_the_speaker():
    sentences, mentions, _ = book(["Elizabeth smiled."], ['"Of course."'])
    assert find_lines(sentences, mentions)[0].how == ""  # different paragraphs
    sentences, mentions, _ = book(['Elizabeth smiled. "Of course."'])
    line = find_lines(sentences, mentions)[0]
    assert (line.speaker, line.how) == (0, "before")


def test_unattributed_turns_alternate_between_two_speakers():
    sentences, mentions, _ = book(['"Is it far?" asked Jane.'], ['"Not at all," said Darcy.'], ['"Then let us walk."'],
                                  ['"Gladly."'])
    who = [(line.speaker, line.how) for line in find_lines(sentences, mentions)]
    assert who == [(2, "said"), (1, "said"), (2, "turn"), (1, "turn")]


def test_a_long_narration_ends_the_conversation():
    sentences, mentions, _ = book(['"Is it far?" asked Jane.'], ['"Not at all," said Darcy.'],
                                  ["They walked.", "It rained.", "The road was long."], ['"Tired?"'])
    last = find_lines(sentences, mentions)[-1]
    assert last.speaker is None and last.listener is None


def test_summaries_count_words_and_listeners():
    sentences, mentions, _ = book(['"Is it far from here?" asked Jane.'], ['"No," said Darcy.'],
                                  ["The end of it all."])
    lines = find_lines(sentences, mentions)
    assert words_spoken(lines, 3) == [0, 1, 5]
    talk = who_talks_to_whom(lines, 3)
    assert talk[2][1] == 1 and talk[1][2] == 1 and talk[0] == [0, 0, 0]
    share = chapter_dialogue_share(lines, sentences, 1)[0]
    assert share == 6 / 15  # 6 spoken words out of 15


def test_strongest_lines_and_signature_words():
    happy, sad = '"What a lovely happy day this is," said Jane.', '"This is the worst thing that ever happened," said Jane.'
    sentences, mentions, _ = book([happy], [sad], tone={happy: 0.9, sad: -0.8})
    lines = find_lines(sentences, mentions)
    bright, dark = strongest_lines(lines, sentences, 2)
    assert bright[0][0].text.startswith("What a lovely") and dark[0][0].text.startswith("This is the worst")
    talk = [['"Pray, pray, pray do come," said Jane.'], ['"Pray come soon," said Jane.'],
            ['"I shall come," said Darcy.'], ['"I shall not," said Darcy.']]
    sentences, mentions, _ = book(*talk)
    lines = find_lines(sentences, mentions)
    assert signature_words(lines, 2, min_count=3, stop_words=frozenset({"do", "come"})) == ["pray"]
    assert signature_words(lines, 0) == []  # Elizabeth says nothing


def test_words_are_counted_per_chapter_and_speaker():
    sentences, mentions, _ = book(['"Is it far from here?" asked Jane.'], ['"No," said Darcy.'],
                                  ["They walked.", "It rained.", "The road was long."], ['"Tired, very tired?"'],
                                  chapters=[0, 1, 1, 1])
    counts, unknown = words_by_chapter(find_lines(sentences, mentions), 3, 2)
    assert counts == [[0, 0], [0, 1], [5, 0]]  # Jane speaks in chapter 1, Darcy in chapter 2
    assert unknown == [0, 3]  # after a long narration, nobody is known to say "Tired, very tired?"
