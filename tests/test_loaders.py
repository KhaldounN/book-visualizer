import pytest

from analyzer.loaders import book_info, clean_text, decode

GUTENBERG_BOOK = """The Project Gutenberg eBook of Test

Title: The Adventures
       of a Test Book

Author: Ann Example

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


def test_title_and_author_come_from_the_gutenberg_header():
    assert book_info(GUTENBERG_BOOK.encode(), "anything.txt") == ("The Adventures of a Test Book", "Ann Example")


def test_title_in_the_story_itself_is_ignored():
    # only the header (before the START marker) counts
    book = "*** START OF THE PROJECT GUTENBERG EBOOK X ***\nTitle: Not this\n"
    assert book_info(book.encode(), "my_novel.txt") == ("My Novel", None)


@pytest.mark.parametrize("filename, title", [
    ("pride_and_prejudice.txt", "Pride And Prejudice"),
    ("Moby-Dick.TXT", "Moby Dick"),
    ("The Hobbit.txt", "The Hobbit"),
    (None, "Untitled book"),
])
def test_title_falls_back_to_the_file_name(filename, title):
    assert book_info(b"Just a story.", filename) == (title, None)


def test_decode_falls_back_for_non_utf8_files():
    assert decode("café".encode("cp1252")) == "café"
    assert decode("﻿Hello".encode("utf-8")) == "Hello"
