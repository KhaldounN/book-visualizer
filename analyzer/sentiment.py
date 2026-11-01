"""Score every sentence from -1 (very negative) to +1 (very positive)."""

from .classifier import Classifier, ProgressCallback, classify_sentences, load_classifier
from .models import Sentence

MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
BATCH_SIZE = 32


def load_model() -> Classifier:
    return load_classifier(MODEL_NAME)


def score(probabilities: dict[str, float]) -> float:
    """One number from the three probabilities: positive minus negative.
    A neutral sentence ends up near 0 because both are small."""
    return probabilities["positive"] - probabilities["negative"]


def score_sentences(
    sentences: list[Sentence], classify: Classifier, progress: ProgressCallback | None = None
) -> None:
    """Set .sentiment on every sentence."""
    for sentence, probabilities in zip(sentences, classify_sentences(sentences, classify, BATCH_SIZE, progress)):
        sentence.sentiment = score(probabilities)
