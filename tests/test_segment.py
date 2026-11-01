from analyzer.segment import FALLBACK_PARTS, split_sentences

BOOK = """Preface by a critic. Walt Whitman once wrote something wise.

CHAPTER I.

Anna Brown lived in London. She was happy.

Tom visited her on Sunday.

Chapter 2: The Storm

The storm destroyed the house. Everyone was afraid."""


def test_finds_chapters_and_skips_front_matter(nlp):
    sentences, chapters = split_sentences(BOOK, nlp)
    assert [c.title for c in chapters] == ["CHAPTER I.", "Chapter 2: The Storm"]
    assert not any("Whitman" in s.text for s in sentences)
    assert not any("CHAPTER" in s.text for s in sentences)


def test_splits_sentences_and_assigns_chapters(nlp):
    sentences, _ = split_sentences(BOOK, nlp)
    assert [(s.text, s.chapter) for s in sentences] == [
        ("Anna Brown lived in London.", 0),
        ("She was happy.", 0),
        ("Tom visited her on Sunday.", 0),
        ("The storm destroyed the house.", 1),
        ("Everyone was afraid.", 1),
    ]


def test_offsets_point_back_into_the_text(nlp):
    sentences, _ = split_sentences(BOOK, nlp)
    for s in sentences:
        assert BOOK[s.start:s.end] == s.text
        for e in s.entities:
            assert BOOK[e.start:e.end] == e.text
    labels = {e.text: e.label for s in sentences for e in s.entities}
    assert labels["Anna Brown"] == "PERSON"
    assert labels["London"] == "GPE"


def test_book_without_chapters_is_split_into_equal_parts(nlp):
    text = "\n\n".join(f"This is sentence number {i}." for i in range(200))
    sentences, chapters = split_sentences(text, nlp)
    assert len(chapters) == FALLBACK_PARTS
    assert sentences[0].chapter == 0
    assert sentences[-1].chapter == FALLBACK_PARTS - 1
