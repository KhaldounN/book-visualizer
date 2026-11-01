import gc

import pytest
import spacy

# This computer can only reserve about 2 GB, so tests must not keep several
# large models in memory at once (the pipeline loads them one at a time too).


@pytest.fixture(autouse=True)
def free_models_after_slow_tests(request):
    """Each real-model test loads a large AI model; free it before the next one."""
    yield
    if request.node.get_closest_marker("slow"):
        gc.collect()


@pytest.fixture(scope="session")
def nlp():
    # The tests check our own logic on short made-up stories, which the small
    # model handles fine; it needs ~15 MB instead of ~600 MB for the large one
    # that real analyses use (pipeline.SPACY_MODEL)
    return spacy.load("en_core_web_sm")
