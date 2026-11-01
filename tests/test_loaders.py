from analyzer.loaders import clean_text, decode

GUTENBERG_BOOK = """The Project Gutenberg eBook of Test

*** START OF THE PROJECT GUTENBERG EBOOK TEST ***

[Illustration: A TEST BOOK

Chapter I.]

It was a _very_ fine day, and Anna
walked to the village.

[Illustration]

“Hello,” she said.

[Illustration:

      THE
      END
       ]

PRINTER'S ADDRESS, LONDON.

*** END OF THE PROJECT GUTENBERG EBOOK TEST ***

Licence text that must disappear.
"""


def test_strips_gutenberg_header_and_footer():
    text = clean_text(GUTENBERG_BOOK)
    assert "Project Gutenberg" not in text
    assert "Licence" not in text


def test_cuts_back_matter_after_the_end():
    text = clean_text(GUTENBERG_BOOK)
    assert text.endswith('"Hello," she said.')


def test_keeps_chapter_heading_hidden_in_illustration():
    text = clean_text(GUTENBERG_BOOK)
    assert text.startswith("Chapter I.\n\n")
    assert "Illustration" not in text


def test_joins_wrapped_lines_and_removes_formatting():
    paragraphs = clean_text(GUTENBERG_BOOK).split("\n\n")
    assert paragraphs[1] == "It was a very fine day, and Anna walked to the village."
    assert paragraphs[2] == '"Hello," she said.'


def test_decode_falls_back_for_non_utf8_files():
    assert decode("café".encode("cp1252")) == "café"
    assert decode("﻿Hello".encode("utf-8")) == "Hello"
