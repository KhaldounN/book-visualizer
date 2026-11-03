"""Book Analyzer: find characters, sentiment and relationships in a novel."""

import os

# Everything runs on this computer: the AI models are stored in the local Hugging Face
# cache, and without this the model library still asks huggingface.co whether a newer
# version exists each time a model loads (it sends the model's name, never the book).
# Offline mode stops that. To download the models the first time on a new computer, run
# once with BOOK_ANALYZER_ALLOW_DOWNLOADS=1.
if os.environ.get("BOOK_ANALYZER_ALLOW_DOWNLOADS") != "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
