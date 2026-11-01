"""Detect the emotions of every sentence.

The model (EmoLit) was trained on sentences from Project Gutenberg books and
knows 38 fine emotions, each scored on its own from 0 to 1, so a sentence can
show several at once (grief *and* guilt) or none at all. We keep:

- `sentence.fine`: the fine emotions that are present (score >= FINE_MIN);
- `sentence.emotions`: one score per *family* (the strongest of its fine
  emotions) plus "neutral" = how far the sentence is from any family. Charts
  use the families: 38 colours would be unreadable.

Calm feelings (calmness, indifference, boredom, courage, faith) belong to no
family, so a calm sentence counts as neutral.
"""

from .classifier import Classifier, ProgressCallback, classify_sentences, load_classifier
from .models import Sentence

MODEL_NAME = "lrei/roberta-base-emolit"
BATCH_SIZE = 32
FINE_MIN = 0.1  # fine emotions below this are not stored at all
# a family only counts members the model is confident about (its usual yes/no
# line); counting weak scores too made every chapter look alike (measured on
# Great Expectations: chapters differ ~45% more with this cut)
PRESENT = 0.5

FAMILIES = {
    "love": ("love", "caring", "desire", "admiration", "gratitude", "trust", "approval"),
    "joy": ("joy", "amusement", "excitement", "optimism", "relief", "pride"),
    "surprise": ("surprise", "curiosity"),
    "shame": ("guilt", "embarrassment"),
    "sadness": ("sadness", "grief", "despair", "disappointment", "nostalgia", "pain"),
    "anger": ("anger", "annoyance", "frustration"),
    "fear": ("fear", "nervousness", "doubt"),
    "disapproval": ("disgust", "disapproval", "envy", "greed"),
}
CALM = ("calmness", "indifference", "boredom", "courage", "faith")
FINE = tuple(sorted({e for members in FAMILIES.values() for e in members} | set(CALM)))  # all 38
EMOTIONS = (*FAMILIES, "neutral")
FAMILY_OF = {e: family for family, members in FAMILIES.items() for e in members}


def load_model() -> Classifier:
    return load_classifier(MODEL_NAME)


def families(fine: dict[str, float]) -> dict[str, float]:
    """Family scores (the strongest member scored >= PRESENT, else 0) plus
    neutral = 1 - the strongest family."""
    scores = {family: max((fine[e] for e in members if fine.get(e, 0.0) >= PRESENT), default=0.0)
              for family, members in FAMILIES.items()}
    scores["neutral"] = 1 - max(scores.values())
    return scores


def detect_emotions(
    sentences: list[Sentence], classify: Classifier, progress: ProgressCallback | None = None
) -> None:
    """Set .fine ({fine emotion: score}, only those present) and .emotions
    ({family: score, "neutral": score}) on every sentence."""
    for sentence, scores in zip(sentences, classify_sentences(sentences, classify, BATCH_SIZE, progress)):
        sentence.fine = {e: round(p, 2) for e, p in scores.items() if e in FINE and p >= FINE_MIN}
        sentence.emotions = {e: round(p, 3) for e, p in families(sentence.fine).items()}


def top_emotion(emotions: dict[str, float]) -> str:
    return max(emotions, key=emotions.get) if emotions else "neutral"


def average_emotions(mixes: list[dict[str, float]]) -> dict[str, float]:
    """Average several {emotion: score} mixes; an emotion missing from a mix
    counts as 0 ({} if there are none, e.g. when emotion detection was skipped)."""
    mixes = [m for m in mixes if m]
    if not mixes:
        return {}
    keys = {e for m in mixes for e in m}
    return {e: sum(m.get(e, 0.0) for m in mixes) / len(mixes) for e in keys}


def stand_out(fine: dict[str, float], book: dict[str, float], n: int = 3, floor: float = 0.03,
              min_lift: float = 1.25) -> list[str]:
    """The fine emotions that are most above the book's own average, e.g.
    ["guilt", "gratitude"] for a character. An emotion must be at least
    `min_lift` times the book's level (a few percent above average is just
    noise), and at least `floor` (a high ratio of two tiny numbers means nothing)."""
    lift = {e: v / max(book.get(e, 0.0), 0.01) for e, v in fine.items() if v >= floor}
    return sorted((e for e in lift if lift[e] >= min_lift), key=lift.get, reverse=True)[:n]
