import pytest
import spacy


@pytest.fixture(scope="session")
def nlp():
    # Loading the model takes a second or two, so share it across all tests
    return spacy.load("en_core_web_sm")
