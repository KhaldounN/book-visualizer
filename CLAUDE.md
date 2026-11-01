# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Book Analyzer: upload an English novel (`.txt`) and get its characters, mention counts (names + pronouns), per-sentence sentiment and emotions, key moments, character relationships, places, and how all of these change chapter by chapter. Several ideas came from the owner's 2020 project (github.com/KhaldounN/book-analyzer-beta), reimplemented. A pure-Python analysis engine (`analyzer/`) plus a Streamlit website (`app/`). The owner is learning programming: explain changes simply.

## Commands (Windows, PowerShell, run from the repo root)

```powershell
python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt   # setup
.\.venv\Scripts\python.exe scripts\download_samples.py                               # test novel -> data/
.\.venv\Scripts\python.exe -m pytest                                  # all tests (~20 s)
.\.venv\Scripts\python.exe -m pytest -m "not slow"                    # skip tests that load a real AI model
.\.venv\Scripts\python.exe -m pytest tests/test_coref.py::test_pronoun_of_the_wrong_gender_is_dropped   # one test
.\.venv\Scripts\python.exe -m analyzer data\pride_and_prejudice.txt   # full analysis, prints a summary (~7 min)
.\.venv\Scripts\python.exe -m analyzer book.txt --no-coref --no-emotions   # faster, skips those steps
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py                # the website
```

There is no linter or build step.

## Architecture

`pipeline.analyze(bytes, progress)` runs the steps in order and returns a `BookAnalysis` (`analyzer/models.py`):

1. `loaders.load_text`: decode, strip the Project Gutenberg licence, remove `[Illustration…]` blocks (but keep a chapter heading or "THE END" hidden inside one), cut back matter after "THE END", and join wrapped lines so every paragraph is one line.
2. `segment.split_sentences`: spaCy `en_core_web_lg` over each paragraph produces sentences with their entities. Text before the first `CHAPTER …` heading (preface, contents) is dropped. Books without headings are split into 50 equal parts.
3. `characters.find_characters`: PERSON entities become characters. The title before a name separates people (Mr./Mrs./Miss Bennet are three characters). Name forms are grouped from most specific to least (full names, then titled names, then bare names). One "follows a place word" rule (`_after_place_word`: `in/at/from/the…`) removes places tagged as people (Meryton) *and* turns ORG estates into places (Netherfield, Pemberley). Plural surnames ("the Lucases") become groups. Entities keep per-chapter counts.
4. `coref.resolve`: fastcoref `FCoref` runs on ~1,500-word chunks, each with ~250 words of read-only context in front. A coreference group is credited to the character whose names dominate it. I/you/they/it words and forms of address are skipped, and pronouns of the wrong gender are dropped (gender comes from titles, else from the 3:1 pronoun ratio).
5. `sentiment.score_sentences`: each sentence gets P(positive) − P(negative) from `cardiffnlp/twitter-roberta-base-sentiment-latest`.
6. `emotions.detect_emotions`: each sentence keeps all 7 probabilities from `j-hartmann/emotion-english-distilroberta-base`. Steps 5 and 6 share `classifier.py` (model loading + length-sorted batching).
7. `relationships` / `progression`: per-chapter aggregates and emotion averages (`emotions.average_emotions`, which lives in `emotions.py` to avoid a circular import). Two characters are "together" when mentioned in the same or the next sentence of the same chapter; each pair also keeps an emotion mix per third of the book. `progression.rolling_sentiment` / `key_moments` are computed in the app at render time, not stored.

Title and author come from `loaders.book_info` (the Gutenberg `Title:`/`Author:` header lines, else the filename).

Key invariants:
- **Every `start`/`end` is an offset into the cleaned text** from `load_text`, and tests assert `text[start:end] == mention.text`. Keep it that way.
- **Character ids are list indexes**, `0..n-1`. `merge.merge_characters` renumbers them and recomputes relationships and progression. Never cache anything keyed by old ids across a merge.
- **Models are injectable** for tests. `coref.resolve` takes a `model` with `.predict`; `sentiment.score_sentences` and `emotions.detect_emotions` take a `classify(list[str])` function.
- **Bump `pipeline.ANALYSIS_VERSION`** whenever `BookAnalysis` or the analysis changes: cached results are `results/v{N}-{sha256}.pkl`, so old ones are then ignored instead of loaded with missing fields. Tests use fakes (`tests/test_coref.py::FakeModel`), and `tests/test_pipeline.py` monkeypatches the `load_model` functions.
- The pipeline loads **one AI model at a time** and deletes it with `gc.collect()` before loading the next.

Website (`app/streamlit_app.py`): Streamlit re-runs the script on every interaction. Analyses live in `st.session_state["analyses"][sha256]` together with the user's merges (merges are applied at render time). Finished analyses are pickled to `results/v{ANALYSIS_VERSION}-<sha256>.pkl`; the uploaded text itself is never saved. `app/charts.py` holds the Plotly figures. Its `THEMES` colors come from the dataviz skill's palette, validated for colorblind safety in light and dark mode. Keep a character's color tied to its mention rank (`character_colors`), never to selection order. The emotion colors follow `EMOTION_ORDER`, an order that passed the validator for stacked neighbours (sadness next to fear failed). Re-validate if you reorder them. `tests/test_app.py` drives the page with Streamlit's `AppTest`.

## Gotchas

- **Keep `transformers<5` and `datasets<5`** (pinned in `requirements.txt`): fastcoref crashes with version 5 of either.
- **Memory:** this machine has the Windows page file off, and the owner's read-aloud voice server (`pythonw … piper_server.py`, never kill it) reserves ~2.6 GB, so often only ~2–3 GB is left. Out-of-memory can show up as a Windows "access violation" crash, not a Python error. Don't load several big models in one process, and don't run the full pipeline, the website and the tests at the same time. The tests use `en_core_web_sm` (see `tests/conftest.py`) for this reason.
- **Speed:** a full novel takes ~7 min (coref ~2 min, sentiment ~3 min, emotions ~1.5 min). Int8 quantization of the sentiment model was tested and rejected: only 71% of sentences kept the same category.
- **Commits:** Windows PowerShell 5.1 mangles double quotes in `git commit -m`. Write the message to a file and use `git commit -F <file>`.
- **Measured accuracy:** coref is ~75% correct on a hand check, and the UI tells users the counts are estimates. The emotion model's "disgust" mostly means disapproval/contempt in classic novels, so the UI labels it that way. Nicknames and married names (Lizzy/Eliza = Elizabeth, Mrs. Collins = Charlotte) are deliberately not auto-merged; the sidebar merge handles them.
- `data/`, `results/`, `.venv/` and `models/` are gitignored.
