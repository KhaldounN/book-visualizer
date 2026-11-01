"""Chapter themes and events. A fake embedder stands in for the local
theme model, so these tests are fast and don't download anything."""

import numpy as np

from analyzer import chapter_events
from analyzer.models import Character, Sentence

CHAPTERS = [
    ["Anna danced at the grand ball.", "The ball lasted until dawn and everyone danced.", "It rained."],
    ["Anna read the letter twice.", "The letter revealed a terrible secret about her brother."],
    ["The storm wrecked the harbour.", "Ships sank in the storm.", "Nobody slept."],
]
SENTENCES = [Sentence(i, text, 0, 0, c) for i, (c, text) in
             enumerate((c, t) for c, texts in enumerate(CHAPTERS) for t in texts)]
CHARACTERS = [Character(0, "Anna", ["Anna", "Anna Smith"], 5)]


def fake_embed(texts):
    """A pretend meaning-vector: how often a text mentions dancing, letters
    and fighting/storms (plus a constant so no vector is all zeros)."""
    def vector(text):
        t = text.lower()
        return [t.count("danc") + t.count("ball"), t.count("letter"), t.count("storm") + t.count("fight"), 0.2]
    v = np.array([vector(t) for t in texts], dtype=float)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_keywords_are_the_words_typical_of_each_chapter():
    weights = chapter_events.word_weights(SENTENCES, CHARACTERS, 3)
    assert chapter_events.keywords(weights[0])[:2] == ["ball", "danced"]
    assert chapter_events.keywords(weights[1])[0] == "letter"
    assert chapter_events.keywords(weights[2])[0] == "storm"
    assert all("anna" not in w and "smith" not in w for w in weights)  # names are left out


def test_key_sentence_is_the_one_richest_in_typical_words():
    weights = chapter_events.word_weights(SENTENCES, CHARACTERS, 3)
    best = chapter_events.key_sentences(CHAPTERS[0], weights[0], k=1)
    assert CHAPTERS[0][best[0]] == "The ball lasted until dawn and everyone danced."


def test_themes_come_from_the_embedder():
    events = chapter_events.name_chapters(SENTENCES, CHARACTERS, 3, fake_embed)
    assert [e.theme for e in events] == ["Ball", "Letter", "Battle"]
    assert all(e.strength > 0 for e in events)
    assert events[1].event == "The letter revealed a terrible secret about her brother."
    assert events[2].keywords[0] == "storm"


def test_a_theme_close_to_every_chapter_does_not_win_everywhere():
    # theme 0 is very close to all chapters, theme 1 only stands out in chapter 1
    chapters = np.array([[0.9, 0.1], [0.9, 0.5], [0.9, 0.1]])
    themes = np.array([[1.0, 0.0], [0.0, 1.0]])
    best, strength = chapter_events.match_themes(chapters, themes)
    assert best[1] == 1 and strength[1] > 1


def test_without_a_model_the_theme_is_the_top_keyword():
    events = chapter_events.name_chapters(SENTENCES, CHARACTERS, 3, embed=None)
    assert [e.theme for e in events] == ["ball", "letter", "storm"]
    assert all(e.strength == 0 for e in events)


def test_long_sentences_are_shortened_at_a_word():
    short = chapter_events.shorten('"' + "word " * 60 + '"', limit=30)
    assert short.endswith(" …") and len(short) <= 32 and "wor …" not in short


def test_progress_reaches_the_end():
    calls = []
    chapter_events.name_chapters(SENTENCES, CHARACTERS, 3, None, lambda d, t: calls.append((d, t)))
    assert calls[-1] == (3, 3)  # the whole book is handled in one batch


def test_every_theme_has_its_own_description():
    assert len(set(chapter_events.THEMES.values())) == len(chapter_events.THEMES)
