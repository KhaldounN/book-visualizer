"""Detect the emotion of every sentence: anger, disgust, fear, joy,
neutral, sadness or surprise.

The model gives a probability for each of the seven; we keep all of them,
so averages over a chapter or a character can show mixed feelings.
"""

from .classifier import Classifier, ProgressCallback, classify_sentences, load_classifier
from .models import Sentence

MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"
BATCH_SIZE = 32
EMOTIONS = ("joy", "surprise", "neutral", "sadness", "fear", "anger", "disgust")


def load_model() -> Classifier:
    return load_classifier(MODEL_NAME)


def detect_emotions(
    sentences: list[Sentence], classify: Classifier, progress: ProgressCallback | None = None
) -> None:
    """Set .emotions on every sentence: {emotion: probability}."""
    for sentence, probabilities in zip(sentences, classify_sentences(sentences, classify, BATCH_SIZE, progress)):
        # 3 decimals is plenty and keeps saved results small
        sentence.emotions = {e: round(probabilities.get(e, 0.0), 3) for e in EMOTIONS}


def top_emotion(emotions: dict[str, float]) -> str:
    return max(emotions, key=emotions.get) if emotions else "neutral"


def average_emotions(mixes: list[dict[str, float]]) -> dict[str, float]:
    """Average several {emotion: probability} mixes ({} if there are none,
    e.g. when emotion detection was skipped)."""
    mixes = [m for m in mixes if m]
    if not mixes:
        return {}
    return {e: sum(m[e] for m in mixes) / len(mixes) for e in mixes[0]}
