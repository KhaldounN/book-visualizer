"""Run a Hugging Face text classifier over every sentence, in batches.

Shared by sentiment.py and emotions.py: both send each sentence through a
model and get back one probability per label.
"""

from typing import Callable

from .models import Sentence

MAX_TOKENS = 128  # longer sentences are cut; the start usually carries the tone

# list of sentences -> one {label: probability} per sentence
Classifier = Callable[[list[str]], list[dict[str, float]]]
ProgressCallback = Callable[[int, int], None]  # (done, total)


def load_classifier(model_name: str) -> Classifier:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from transformers.utils import logging

    logging.set_verbosity_error()  # hide "some weights were not used" notices
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name).eval()
    labels = [model.config.id2label[i].lower() for i in range(model.config.num_labels)]

    def classify(texts: list[str]) -> list[dict[str, float]]:
        batch = tokenizer(texts, padding=True, truncation=True, max_length=MAX_TOKENS, return_tensors="pt")
        with torch.inference_mode():  # no training, so skip the bookkeeping for it
            probabilities = model(**batch).logits.softmax(dim=-1)
        return [dict(zip(labels, row.tolist())) for row in probabilities]

    return classify


def classify_sentences(
    sentences: list[Sentence], classify: Classifier, batch_size: int,
    progress: ProgressCallback | None = None,
) -> list[dict[str, float]]:
    """Probabilities for every sentence, in the same order as `sentences`."""
    results: list[dict[str, float]] = [{} for _ in sentences]
    # Sentences in one batch are padded to the longest one, so batching
    # sentences of similar length together wastes much less work
    order = sorted(range(len(sentences)), key=lambda i: len(sentences[i].text))
    for start in range(0, len(order), batch_size):
        batch = order[start:start + batch_size]
        for i, probabilities in zip(batch, classify([sentences[i].text for i in batch])):
            results[i] = probabilities
        if progress:
            progress(min(start + batch_size, len(order)), len(order))
    return results
