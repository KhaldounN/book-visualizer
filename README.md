# 📖 Book Analyzer

Upload an English novel as a `.txt` file and explore:

- **Characters**: who appears and how often, counting names *and* pronouns ("she", "his")
- **Story sentiment**: the mood per chapter (whole book or per character), the mood sentence by
  sentence, and the **key moments**: the darkest and brightest passages, quoted
- **Emotions**: joy, sadness, anger, fear, disgust, surprise (and neutral) for every sentence: the
  book's mix, how it changes chapter by chapter, and each character's profile
- **Timeline**: where each character appears across the chapters
- **Relationships**: who shares scenes with whom, how the tone of those scenes changes, and their
  emotions early, midway and late in the book
- **Places & entities**: where the story happens chapter by chapter, plus organizations and groups

The title and author are read from the book (Project Gutenberg files include them).

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

A full novel takes about 7 minutes on a normal computer (`--no-coref` and `--no-emotions` make the
command line faster). Results are saved in `results/`, so the same
book opens instantly the next time. The uploaded text itself is never saved.

## How it works

| Step | Tool |
|---|---|
| Split the text into chapters and sentences, find names | [spaCy](https://spacy.io) `en_core_web_lg` |
| Group name variants into characters (Mr. Darcy = Darcy) | our own rules (`analyzer/characters.py`) |
| Link pronouns to characters | [fastcoref](https://github.com/shon-otmazgin/fastcoref) |
| Score each sentence from −1 (negative) to +1 (positive) | [`cardiffnlp/twitter-roberta-base-sentiment-latest`](https://huggingface.co/cardiffnlp/twitter-roberta-base-sentiment-latest) |
| Detect the emotion of each sentence | [`j-hartmann/emotion-english-distilroberta-base`](https://huggingface.co/j-hartmann/emotion-english-distilroberta-base) |
| Tell places from organizations ("at Pemberley") | our own rules (`analyzer/characters.py`) |
| Charts | [Plotly](https://plotly.com/python/) in [Streamlit](https://streamlit.io) |

## Limits worth knowing

- **Tone is about words, not feelings.** Polite flattery scores positive even when the story mocks it.
- **"Disgust" mostly means disapproval or contempt** in classic novels, which are full of social
  judgement. Emotions are best read as trends across chapters, not sentence by sentence.
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
