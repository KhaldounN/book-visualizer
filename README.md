# 📖 Book Analyzer

Upload an English novel as a `.txt` file and explore:

- **Characters**: who appears and how often, counting names *and* pronouns ("she", "his")
- **Story sentiment**: the mood of every sentence, averaged per chapter, for the whole book or per character
- **Timeline**: where each character appears across the chapters
- **Relationships**: who shares scenes with whom, and how the tone of those scenes changes over the book
- **Entities**: places, organizations and other named things

Plain-text novels from [Project Gutenberg](https://www.gutenberg.org) work well.

## Setup (Windows)

Requires Python 3.13. The first run downloads about 2 GB of AI models.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\download_samples.py   # optional: Pride and Prejudice for testing
```

## Use it

**Website:**

```powershell
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py
```

**Command line** (prints a summary):

```powershell
.\.venv\Scripts\python.exe -m analyzer data\pride_and_prejudice.txt
```

A full novel takes about 7 minutes on a normal computer. Results are saved in `results/`, so the same
book opens instantly the next time. The uploaded text itself is never saved.

## How it works

| Step | Tool |
|---|---|
| Split the text into chapters and sentences, find names | [spaCy](https://spacy.io) `en_core_web_lg` |
| Group name variants into characters (Mr. Darcy = Darcy) | our own rules (`analyzer/characters.py`) |
| Link pronouns to characters | [fastcoref](https://github.com/shon-otmazgin/fastcoref) |
| Score each sentence from −1 (negative) to +1 (positive) | [`cardiffnlp/twitter-roberta-base-sentiment-latest`](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest) |
| Charts | [Plotly](https://plotly.com/python/) in [Streamlit](https://streamlit.io) |

## Limits worth knowing

- **Tone is about words, not feelings.** Polite flattery scores positive even when the story mocks it.
- **Pronoun links are right about 3 times out of 4**, so treat mention counts as estimates and look at
  trends. "I" and "you" in dialogue are not counted.
- **Nicknames and married names** (Lizzy, Eliza = Elizabeth) need knowledge of the story; merge them in
  the website's sidebar.
- English `.txt` files only for now; PDF and EPUB are planned.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest              # all tests
.\.venv\Scripts\python.exe -m pytest -m "not slow"  # skip the test that loads a real AI model
```
