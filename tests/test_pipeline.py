"""The whole pipeline on a short story: real spaCy, fake coref and sentiment
models (the real ones take minutes and are tested on their own)."""

import pytest

import numpy as np

from analyzer import chapter_events, coref, emotions, pipeline, sentiment

BOOK = b"""
CHAPTER I.

Anna Smith lived in a small house near the river. Anna loved the garden.
Tom Baker visited Anna every morning. Anna and Tom were happy together.
Tom brought flowers, and Anna was happy. Tom laughed with Anna all day.

CHAPTER II.

Then the storm came. Anna was frightened and sad. Tom could not reach Anna.
Tom was sad and alone. The river flooded the garden, and Anna wept.
Tom wrote a sad letter to Anna.
"""


class NoCoref:
    def predict(self, texts):
        return [type("Result", (), {"get_clusters": lambda self, as_strings=True: []})()]


def fake_classify(texts):
    def tone(t):
        if "happy" in t:
            return {"negative": 0.0, "neutral": 0.2, "positive": 0.8}
        if "sad" in t:
            return {"negative": 0.8, "neutral": 0.2, "positive": 0.0}
        return {"negative": 0.1, "neutral": 0.8, "positive": 0.1}

    return [tone(t) for t in texts]


def fake_emotions(texts):
    return [{"joy": 0.9, "neutral": 0.1} if "happy" in t else {"sadness": 0.8, "neutral": 0.2} if "sad" in t
            else {"neutral": 1.0} for t in texts]


def fake_embed(texts):
    """Pretend meaning-vectors: happy text points one way, sad text another."""
    v = np.array([[t.count("happy") + 0.1, t.count("sad") + 0.1] for t in texts], dtype=float)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


@pytest.fixture
def fake_models(monkeypatch, nlp):
    monkeypatch.setattr(pipeline, "load_spacy", lambda: nlp)
    monkeypatch.setattr(coref, "load_model", NoCoref)
    monkeypatch.setattr(sentiment, "load_model", lambda: fake_classify)
    monkeypatch.setattr(emotions, "load_model", lambda: fake_emotions)
    monkeypatch.setattr(chapter_events, "load_model", lambda: fake_embed)


def test_whole_pipeline(fake_models):
    progress = []
    result = pipeline.analyze(BOOK, lambda step, fraction: progress.append((step, fraction)),
                              filename="anna_and_tom.txt")

    assert (result.title, result.author) == ("Anna And Tom", None)
    assert [c.title for c in result.chapters] == ["CHAPTER I.", "CHAPTER II."]
    names = {c.name: c for c in result.characters}
    assert {"Anna", "Tom"} <= set(names)
    assert sum(c.mentions for c in result.characters) == len(result.mentions)

    anna, tom = names["Anna"].id, names["Tom"].id
    assert any({r.source, r.target} == {anna, tom} for r in result.relationships)
    # happy first chapter, sad second chapter
    assert result.chapter_sentiment[0] > 0 > result.chapter_sentiment[1]
    assert result.sentiment_by_chapter[anna][0] > 0 > result.sentiment_by_chapter[anna][1]
    happy = next(s for s in result.sentences if "happy" in s.text)
    assert emotions.top_emotion(happy.emotions) == "joy"
    assert len(result.chapter_events) == 2
    assert all(e.theme in chapter_events.THEMES and e.event for e in result.chapter_events)

    fractions = [f for _, f in progress]
    assert fractions == sorted(fractions), "progress never goes backwards"
    assert progress[-1] == ("Done", 1.0)
    assert set(result.timings) == set(pipeline.STEPS)


def test_file_without_story_text_is_rejected(fake_models):
    with pytest.raises(ValueError, match="No story text"):
        pipeline.analyze(b"   \n\n  ")
