import pytest

from analyzer import emotions
from analyzer.models import Sentence


def sentences(*texts):
    return [Sentence(i, t, 0, 0, 0) for i, t in enumerate(texts)]


def fake_classify(texts):
    return [{"anger": 0.7, "neutral": 0.3} if "furious" in t else {"neutral": 0.95, "joy": 0.05} for t in texts]


def test_every_sentence_gets_all_seven_emotions():
    items = sentences("He was furious.", "They walked home.")
    emotions.detect_emotions(items, fake_classify)
    assert all(set(s.emotions) == set(emotions.EMOTIONS) for s in items)
    assert items[0].emotions["anger"] == 0.7
    assert items[0].emotions["disgust"] == 0.0  # labels the model didn't return count as 0
    assert [emotions.top_emotion(s.emotions) for s in items] == ["anger", "neutral"]


def test_top_emotion_of_nothing_is_neutral():
    assert emotions.top_emotion({}) == "neutral"


@pytest.mark.slow
def test_real_model_fixes_the_beta_models_mistakes():
    # Book Analyzer Beta's word-count model called both of these "joy"
    items = sentences("this is a let down", "it disgust me", "this makes me happy",
                      "Elizabeth walked to the village after breakfast.")
    emotions.detect_emotions(items, emotions.load_model())
    assert [emotions.top_emotion(s.emotions) for s in items] == ["sadness", "disgust", "joy", "neutral"]
