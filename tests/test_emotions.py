import pytest

from analyzer import emotions
from analyzer.models import Sentence


def sentences(*texts):
    return [Sentence(i, t, 0, 0, 0) for i, t in enumerate(texts)]


def fake_classify(texts):
    """Like the real model: an independent score per fine emotion."""
    def one(t):
        scores = {e: 0.01 for e in emotions.FINE}
        if "furious" in t:
            scores.update(annoyance=0.9, frustration=0.6, disgust=0.3)
        if "calm" in t:
            scores.update(calmness=0.95)
        return scores
    return [one(t) for t in texts]


def test_the_38_fine_emotions_are_all_accounted_for():
    assert len(emotions.FINE) == 38
    grouped = [e for members in emotions.FAMILIES.values() for e in members] + list(emotions.CALM)
    assert sorted(grouped) == sorted(emotions.FINE), "every fine emotion is in exactly one family or calm"
    assert len(emotions.FAMILIES) == 8


def test_families_take_their_strongest_member():
    items = sentences("He was furious.", "They walked home.", "She was calm.")
    emotions.detect_emotions(items, fake_classify)
    furious, plain, calm = items
    assert furious.fine == {"annoyance": 0.9, "frustration": 0.6, "disgust": 0.3}, "only emotions >= 0.1 are kept"
    assert furious.emotions["anger"] == 0.9
    assert furious.emotions["disapproval"] == 0.0, "disgust 0.3 is kept as a fine emotion but too weak for its family"
    assert furious.emotions["neutral"] == pytest.approx(0.1)
    assert set(furious.emotions) == set(emotions.EMOTIONS)
    assert emotions.top_emotion(plain.emotions) == "neutral" and plain.fine == {}
    # calm feelings belong to no family, so a calm sentence is neutral
    assert calm.fine == {"calmness": 0.95} and emotions.top_emotion(calm.emotions) == "neutral"


def test_top_emotion_of_nothing_is_neutral():
    assert emotions.top_emotion({}) == "neutral"


def test_average_of_sparse_mixes_counts_missing_as_zero():
    assert emotions.average_emotions([{"guilt": 0.6}, {"grief": 0.4}, {}]) == {"guilt": 0.3, "grief": 0.2}
    assert emotions.average_emotions([]) == {}


def test_stand_out_finds_what_is_above_the_book():
    book = {"guilt": 0.02, "curiosity": 0.20, "grief": 0.001, "love": 0.10}
    character = {"guilt": 0.10, "curiosity": 0.20, "grief": 0.02, "love": 0.11}
    # guilt is 5x the book; curiosity is only average; love is just 10% above
    # (noise); grief is too rare to count
    assert emotions.stand_out(character, book) == ["guilt"]


@pytest.mark.slow
def test_real_model_fixes_the_beta_models_mistakes():
    # Book Analyzer Beta's word-count model called the first two "joy"
    items = sentences("this is a let down", "it disgust me", "this makes me happy",
                      "Elizabeth walked to the village after breakfast.",
                      "I was much obliged to him for his kindness.")
    emotions.detect_emotions(items, emotions.load_model())
    assert [emotions.top_emotion(s.emotions) for s in items] == ["sadness", "disapproval", "joy", "neutral", "love"]
    assert "disappointment" in items[0].fine and "gratitude" in items[4].fine
