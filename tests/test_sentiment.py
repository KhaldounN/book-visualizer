import pytest

from analyzer import sentiment
from analyzer.models import Sentence


def fake_classify(texts):
    """Pretends to be the model: "good" -> positive, "bad" -> negative."""
    results = []
    for t in texts:
        if "good" in t:
            results.append({"negative": 0.1, "neutral": 0.1, "positive": 0.8})
        elif "bad" in t:
            results.append({"negative": 0.9, "neutral": 0.1, "positive": 0.0})
        else:
            results.append({"negative": 0.1, "neutral": 0.8, "positive": 0.1})
    return results


def sentences(*texts):
    return [Sentence(i, t, 0, 0, 0) for i, t in enumerate(texts)]


def test_score_is_positive_minus_negative():
    assert sentiment.score({"negative": 0.1, "neutral": 0.1, "positive": 0.8}) == pytest.approx(0.7)
    assert sentiment.score({"negative": 0.2, "neutral": 0.6, "positive": 0.2}) == pytest.approx(0.0)


def test_scores_land_on_the_right_sentences(monkeypatch):
    # Sentences are sorted by length into batches, so check each score still
    # ends up on its own sentence
    monkeypatch.setattr(sentiment, "BATCH_SIZE", 2)
    items = sentences("A very long and good sentence indeed.", "bad", "So-so day.", "good")
    sentiment.score_sentences(items, fake_classify)
    assert [round(s.sentiment, 1) for s in items] == [0.7, -0.9, 0.0, 0.7]


def test_progress_is_reported(monkeypatch):
    monkeypatch.setattr(sentiment, "BATCH_SIZE", 2)
    calls = []
    sentiment.score_sentences(sentences("a", "b", "c"), fake_classify, lambda done, total: calls.append((done, total)))
    assert calls == [(2, 3), (3, 3)]


@pytest.mark.slow
def test_real_model_reads_tone_sensibly():
    items = sentences(
        "She was delighted to see her dearest sister again.",
        "He was the most disagreeable, proud and insolent man in the world.",
        "They walked to the village after breakfast.",
    )
    sentiment.score_sentences(items, sentiment.load_model())
    happy, angry, plain = (s.sentiment for s in items)
    assert happy > 0.5
    assert angry < -0.5
    assert abs(plain) < 0.3
