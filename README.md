# 📖 Book Analyzer

Upload an English novel as a `.txt` file and explore:

- **The story**: every chapter's theme (ball, proposal, scandal, journey…), its most telling sentence and
  keywords, mood, emotions, people and place, as a strip of chapter cards; and a 3D "story road" that climbs and
  dips with the mood, with signposts at the turning points and gates at each act, to travel along with the cast: each
  character's face steps onto the road when they enter the story and walks off when they leave it. The land beside the road shows **where** each chapter happens (forest, town, mountains, sea, marshes, desert, snow), read from the words that describe the surroundings. A badge names the story's **shape**: which of the six classic emotional shapes
  (Rags to riches, Tragedy, Man in a hole, Icarus, Cinderella, Oedipus; Reagan et al., 2016) its mood curve fits best. Themes come from a small model running on your computer and are
  right about half the time, so each one is shown with the sentence and words it is based on
- **Characters**: who appears and how often, counting names *and* pronouns ("she", "his"), each main
  character with a drawn period portrait based on what the book says about them (hair, age, job, a
  bridal veil…), with the story filling in the blanks
- **Story sentiment**: the mood per chapter (whole book or per character), the mood sentence by
  sentence, and the **key moments**: the darkest and brightest passages, quoted
- **Emotions**: 38 fine emotions (grief, guilt, gratitude, curiosity, envy…) for every sentence, from a
  model trained on classic books, grouped into 8 families (love, joy, surprise, shame, sadness, anger,
  fear, disapproval): the book's mix, how it changes chapter by chapter, each character's profile, and
  what stands out for each character and chapter
- **Timeline**: where each character appears across the chapters
- **Relationships**: who shares scenes with whom, how the tone of those scenes changes, and their
  emotions early, midway and late in the book
- **Places & entities**: where the story happens chapter by chapter, plus organizations and groups
- **Light or dark**: a switch in the sidebar (the open book stays open).
- **Explore in 3D**: three interactive scenes to rotate and click: a story road, a character constellation
  and an emotion crystal per character (needs an internet connection to load the 3D library)

The title and author are read from the book (Project Gutenberg files include them).

Plain-text novels from [Project Gutenberg](https://www.gutenberg.org) work well.

## Setup (Windows)

Requires Python 3.13. The first run downloads about 2 GB of AI models.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\download_samples.py   # optional: sample books (Great Expectations for the website's sample button, Pride and Prejudice)
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
| Detect the emotions of each sentence | [`lrei/roberta-base-emolit`](https://huggingface.co/lrei/roberta-base-emolit) (EmoLit, trained on Project Gutenberg sentences) |
| Pick each chapter's theme | [`sentence-transformers/all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) embeddings + our key sentences and keywords (`analyzer/chapter_events.py`) |
| Tell places from organizations ("at Pemberley") | our own rules (`analyzer/characters.py`) |
| Charts | [Plotly](https://plotly.com/python/) in [Streamlit](https://streamlit.io) |

## Limits worth knowing

- **Tone is about words, not feelings.** Polite flattery scores positive even when the story mocks it.
- **Emotions are right about 4 times in 5** on a hand check of 60 sentences (the previous,
  tweet-trained model: about 3 in 4), and weakest at fear. Read them as trends across chapters, not
  sentence by sentence.
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
