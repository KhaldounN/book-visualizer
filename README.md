# 📖 Book Analyzer

Upload an English novel as a `.txt` file and explore:

- **Story timeline**: every chapter's theme (ball, proposal, scandal, journey…), its most telling sentence and
  keywords, along the mood and emotions of the book; the story's arc with its turning points and acts; and a 3D
  "story road" that climbs and dips with the mood, with signposts at the turning points, to travel along. Themes come from a small model running on your computer and are
  right about half the time, so each one is shown with the sentence and words it is based on
- **Characters**: who appears and how often, counting names *and* pronouns ("she", "his")
- **Story sentiment**: the mood per chapter (whole book or per character), the mood sentence by
  sentence, and the **key moments**: the darkest and brightest passages, quoted
- **Emotions**: joy, sadness, anger, fear, disgust, surprise (and neutral) for every sentence: the
  book's mix, how it changes chapter by chapter, and each character's profile
- **Timeline**: where each character appears across the chapters
- **Relationships**: who shares scenes with whom, how the tone of those scenes changes, and their
  emotions early, midway and late in the book
- **Places & entities**: where the story happens chapter by chapter, plus organizations and groups
- **Explore in 3D**: five interactive scenes to rotate and click: a character constellation, a story
  terrain, an emotion crystal per character, a relationship double helix, and a fly-through chapter
  tunnel (needs an internet connection to load the 3D library)

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
.\run_website.ps1
```

(It runs `streamlit run app\streamlit_app.py` with a memory-saving setting, see the script.)

One scrolling page: the book's title over a "mood barcode" (one stripe per chapter), headline cards,
then 3D views and charts, each with an explanation next to it. Every main character keeps one colour
in every chart and 3D view (the legend is in the sidebar).

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
| Pick each chapter's theme | [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) embeddings + our key sentences and keywords (`analyzer/chapter_events.py`) |
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
