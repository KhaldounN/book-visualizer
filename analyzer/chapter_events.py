"""Name each chapter's main theme and event, entirely on this computer.

1. Keywords: the words most typical of the chapter compared with the rest
   of the book (TF-IDF).
2. Key sentence: the chapter's sentence richest in those words; it stands
   for the chapter's main event.
3. Theme: a small sentence-embedding model turns the chapter's key sentences
   and a description of each story theme into vectors ("meaning as
   numbers"). The theme whose description is unusually close to this
   chapter, compared with the rest of the book, wins.

Tested on Pride and Prejudice: about 5 in 12 known chapters exactly right
and 4 close, in a few seconds for the whole book. (A zero-shot classifier was
tried first: no better, and about 2 hours per novel on this computer.)
"""

import math
import re
from collections import Counter
from typing import Callable

import numpy as np

from .models import ChapterEvent, Character, Sentence

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
KEY_SENTENCES = 6  # how many of a chapter's sentences stand for the whole chapter
EVENT_CHARS = 140  # the key sentence is shortened to about this length

# theme shown to the reader -> the description the model compares chapters with
THEMES = {
    "Ball": "a ball or dance party with music, dancing partners and guests",
    "Proposal": "a man asks a woman to marry him and declares his love",
    "Engagement": "the news that a couple are engaged to be married",
    "Wedding": "a wedding ceremony and a newly married couple",
    "Letter": "someone reads or writes a long letter",
    "Journey": "travelling, a carriage journey, a tour to another place",
    "Visit": "calling on neighbours, a visit to someone's house",
    "Argument": "an angry argument or quarrel",
    "Gossip": "gossip, rumours and news about other people",
    "Revelation": "a hidden truth or secret is revealed",
    "Scandal": "a scandal, disgrace and shame for a family",
    "Betrayal": "a betrayal of trust",
    "Confrontation": "a tense confrontation where someone is insulted or challenged",
    "Reconciliation": "making peace and forgiving after a quarrel",
    "Romance": "falling in love, admiration and affection",
    "Illness": "someone is ill and being nursed",
    "Death": "a death and mourning",
    "Battle": "a battle, fighting and soldiers in combat",
    "Danger": "danger, threats and fear for someone's safety",
    "Adventure": "an exciting adventure",
    "Celebration": "happy news and celebration",
    "Sadness": "grief, sorrow and tears",
    "Family": "family life at home with parents and sisters",
    "Money": "money, fortune, income and inheritance",
}

# Words common in every novel's chapters that say nothing about events
_COMMON = {
    "said", "dear", "know", "think", "shall", "little", "good", "great", "time", "soon", "make", "come",
    "thing", "say", "tell", "away", "long", "nothing", "felt", "feel", "much", "well", "upon", "though",
}
_WORD = re.compile(r"[a-z]{4,}")

Embedder = Callable[[list[str]], np.ndarray]  # texts -> one unit-length vector per text
ProgressCallback = Callable[[int, int], None]  # (done, total)


def load_model() -> Embedder:
    import torch
    from transformers import AutoModel, AutoTokenizer
    from transformers.utils import logging

    logging.set_verbosity_error()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModel.from_pretrained(MODEL_NAME).eval()

    def embed(texts: list[str]) -> np.ndarray:
        batch = tokenizer(texts, padding=True, truncation=True, max_length=256, return_tensors="pt")
        with torch.inference_mode():
            words = model(**batch).last_hidden_state
        mask = batch["attention_mask"].unsqueeze(-1)
        vectors = (words * mask).sum(1) / mask.sum(1)  # average over the words of each text
        return torch.nn.functional.normalize(vectors, dim=-1).numpy()

    return embed


def word_weights(sentences: list[Sentence], characters: list[Character],
                 num_chapters: int) -> list[dict[str, float]]:
    """[chapter] -> {word: how typical it is of that chapter} (TF-IDF), leaving
    out common words and character names."""
    from spacy.lang.en.stop_words import STOP_WORDS

    names = {w.lower() for c in characters for alias in c.aliases for w in alias.split()}
    skip = STOP_WORDS | _COMMON | names
    counts = [Counter() for _ in range(num_chapters)]
    for s in sentences:
        for word in _WORD.findall(s.text.lower()):
            if word not in skip:
                counts[s.chapter][word] += 1
    # in how many chapters each word appears: rarer across chapters = more telling
    spread = Counter(word for c in counts for word in c)
    return [{w: n * math.log(num_chapters / spread[w]) for w, n in c.items()} for c in counts]


def keywords(weights: dict[str, float], top: int = 3) -> list[str]:
    return sorted(weights, key=lambda w: (-weights[w], w))[:top]


def key_sentences(chapter: list[str], weights: dict[str, float], k: int) -> list[int]:
    """Indexes of the k sentences richest in the chapter's typical words,
    best first. Dividing by the square root of the length keeps long
    sentences from winning just by being long."""
    def score(sentence: str) -> float:
        return sum(weights.get(w, 0.0) for w in _WORD.findall(sentence.lower())) / math.sqrt(len(sentence.split()) + 5)

    return sorted(range(len(chapter)), key=lambda i: -score(chapter[i]))[:k]


def shorten(sentence: str, limit: int = EVENT_CHARS) -> str:
    sentence = sentence.strip().strip('"').strip()
    return sentence if len(sentence) <= limit else sentence[:limit].rsplit(" ", 1)[0] + " …"


def match_themes(chapter_vectors: np.ndarray, theme_vectors: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For each chapter: the index of the best theme and how strongly it
    stands out. Scores are compared with each theme's own average over the
    book; without that, a theme close to everything ("Scandal" in a society
    novel) would win almost every chapter."""
    similarity = chapter_vectors @ theme_vectors.T  # cosine similarity (vectors have length 1)
    spread = similarity.std(axis=0)
    standout = (similarity - similarity.mean(axis=0)) / np.where(spread > 0, spread, 1)
    best = standout.argmax(axis=1)
    return best, standout[np.arange(len(best)), best]


def name_chapters(sentences: list[Sentence], characters: list[Character], num_chapters: int,
                  embed: Embedder | None, progress: ProgressCallback | None = None) -> list[ChapterEvent]:
    """A ChapterEvent for every chapter. Without a model (theme detection
    switched off) the theme is the chapter's top keyword."""
    weights = word_weights(sentences, characters, num_chapters)
    by_chapter: list[list[str]] = [[] for _ in range(num_chapters)]
    for s in sentences:
        by_chapter[s.chapter].append(s.text)

    tops = [key_sentences(chapter, weights[ch], KEY_SENTENCES) for ch, chapter in enumerate(by_chapter)]
    words = [keywords(w) for w in weights]
    themes = [w[0] if w else "" for w in words]
    strengths = [0.0] * num_chapters
    if embed and num_chapters > 1:
        digests = [" ".join(chapter[i] for i in sorted(top)) for chapter, top in zip(by_chapter, tops)]
        names = list(THEMES)
        best, strength = match_themes(embed(digests), embed([THEMES[t] for t in names]))
        themes = [names[i] if digests[ch] else themes[ch] for ch, i in enumerate(best)]
        strengths = [round(float(s), 2) for s in strength]
    if progress:
        progress(num_chapters, num_chapters)
    return [
        ChapterEvent(theme=themes[ch], strength=strengths[ch],
                     event=shorten(by_chapter[ch][tops[ch][0]]) if tops[ch] else "", keywords=words[ch])
        for ch in range(num_chapters)
    ]
