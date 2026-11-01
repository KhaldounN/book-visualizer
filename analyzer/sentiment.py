"""Score every sentence from -1 (very negative) to +1 (very positive)."""

from typing import Callable

from .models import Sentence

MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
BATCH_SIZE = 32
MAX_TOKENS = 128  # longer sentences are cut; the start usually carries the tone

# list of sentences -> one {"negative": p, "neutral": p, "positive": p} per sentence
Classifier = Callable[[list[str]], list[dict[str, float]]]
ProgressCallback = Callable[[int, int], None]  # (done, total)


def load_model() -> Classifier:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from transformers.utils import logging

    logging.set_verbosity_error()  # hide "some weights were not used" notices
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME).eval()
    labels = [model.config.id2label[i].lower() for i in range(model.config.num_labels)]

    def classify(texts: list[str]) -> list[dict[str, float]]:
        batch = tokenizer(texts, padding=True, truncation=True, max_length=MAX_TOKENS, return_tensors="pt")
        with torch.inference_mode():  # no training, so skip the bookkeeping for it
            probabilities = model(**batch).logits.softmax(dim=-1)
        return [dict(zip(labels, row.tolist())) for row in probabilities]

    return classify


def score(probabilities: dict[str, float]) -> float:
    """One number from the three probabilities: positive minus negative.
    A neutral sentence ends up near 0 because both are small."""
    return probabilities["positive"] - probabilities["negative"]


def score_sentences(
    sentences: list[Sentence], classify: Classifier, progress: ProgressCallback | None = None
) -> None:
    """Set .sentiment on every sentence."""
    # Sentences in one batch are padded to the longest one, so batching
    # sentences of similar length together wastes much less work
    order = sorted(sentences, key=lambda s: len(s.text))
    for i in range(0, len(order), BATCH_SIZE):
        batch = order[i:i + BATCH_SIZE]
        for sentence, probabilities in zip(batch, classify([s.text for s in batch])):
            sentence.sentiment = score(probabilities)
        if progress:
            progress(min(i + BATCH_SIZE, len(order)), len(order))
