from analyzer.segment import FALLBACK_PARTS, chapter_headings, display_title, find_chapters, split_sentences

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


def test_each_sentence_counts_its_word_types(nlp):
    sentences, _ = split_sentences(BOOK, nlp)
    assert all(s.tags is not None for s in sentences)
    assert sum(s.tags["VERB"] for s in sentences) > 0 and sum(s.tags["ADJ"] for s in sentences) > 0


def _book(headings: list[str], contents: bool = False) -> str:
    """A book with these chapter headings, each followed by enough text to be a chapter."""
    words = " ".join(["The road was long and the night was cold."] * 6)
    front = "Contents\n\n" + "\n\n".join(headings) + "\n\n" if contents else ""
    return front + "".join(f"{h}\n\n{words}\n\n" for h in headings)


def test_chapters_without_the_word_chapter_are_found():
    # Roman numerals with or without a title (The Wind in the Willows, Treasure Island, Gatsby)
    assert [c.title for c in find_chapters(_book(["I. THE RIVER BANK", "II. THE OPEN ROAD", "III. THE WILD WOOD"]))] \
        == ["I. THE RIVER BANK", "II. THE OPEN ROAD", "III. THE WILD WOOD"]
    assert len(find_chapters(_book(["I The Old Sea-dog", "II Black Dog Appears", "III The Black Spot"]))) == 3
    assert len(find_chapters(_book(["I", "II", "III", "IV"]))) == 4
    # staves (A Christmas Carol), numbers (Black Beauty), number words beyond twenty (Little Women)
    assert len(find_chapters(_book(["STAVE I: MARLEY'S GHOST", "STAVE II: THE FIRST SPIRIT", "STAVE III"]))) == 3
    assert len(find_chapters(_book(["01 My Early Home", "02 The Hunt", "03 My Breaking In"]))) == 3
    assert find_chapters(_book(["CHAPTER TWENTY", "CHAPTER TWENTY-ONE", "CHAPTER TWENTY-TWO"]))[1].title \
        == "CHAPTER TWENTY-ONE"


def test_lines_that_merely_start_with_a_numeral_are_not_chapters():
    assert find_chapters(_book(["I took a step nearer.", "I said nothing.", "I think so?"])) == []  # sentences
    assert find_chapters(_book(["III. A", "I. B", "VII. C", "II. D"])) == []  # not counting up: stray lines


def test_a_contents_page_is_not_read_as_chapters():
    titles = ["CHAPTER 1. Loomings", "CHAPTER 2. The Carpet-Bag", "CHAPTER 3. The Inn"]
    assert [c.title for c in find_chapters(_book(titles, contents=True))] == titles
    # the last contents entry is followed by text (an epigraph), yet comes before chapter 1
    epigraph = " ".join(["An old epigraph about whales."] * 12)
    assert find_chapters(f"CHAPTER 3. The Inn\n\n{epigraph}\n\n" + _book(titles))[0].title == titles[0]


def test_chapter_titles_are_shown_one_tidy_way():
    from analyzer.segment import display_title
    assert display_title("CHAPTER XLVII.") == "Chapter 47"
    assert display_title("CHAPTER II. TREATS OF OLIVER TWIST'S GROWTH") == "Chapter 2: Treats of Oliver Twist's Growth"
    assert display_title("STAVE I: MARLEY'S GHOST") == "Stave 1: Marley's Ghost"
    assert display_title("IV. THE CYLINDER OPENS.") == "Chapter 4: The Cylinder Opens"
    assert display_title("CHAPTER TWENTY-ONE MEG GOES TO VANITY FAIR") == "Chapter 21: Meg Goes to Vanity Fair"
    assert display_title("Chapter I The Cyclone") == "Chapter 1: The Cyclone"  # mixed case stays as written
    assert display_title("Part 3") == "Part 3"


def test_scripture_books_and_suras_are_chapters():
    """The Bible's books (a line before its first verse, "1:1") and the Quran's suras (Rodwell's
    translation, in the order of revelation, so not counting up) are found as chapters."""
    filler = " ".join(["word"] * 60)
    bible = "".join(f"The Book of {name}\n\n1:1 {filler}\n\n1:2 {filler}\n\n" for name in ("Ruth", "Job", "Jonah"))
    assert [m.group(0).strip() for m in chapter_headings(bible)] == ["The Book of Ruth", "The Book of Job", "The Book of Jonah"]
    quran = "".join(f"SURA {n}.-THE {name} [{i}.]\n\n{filler}\n\n"
                    for i, (n, name) in enumerate((("XCVI", "CLOTS1"), ("LXXIV", "ENWRAPPED"), ("I", "OPENING")), 1))
    assert len(chapter_headings(quran)) == 3
    assert display_title("SURA1 XCVI.-THICK BLOOD, OR CLOTS OF BLOOD [I.]") == "Sura 96: Thick Blood, or Clots of Blood"
    assert display_title("SURA LXXIV.-THE ENWRAPPED1 [II.]") == "Sura 74: The Enwrapped"
