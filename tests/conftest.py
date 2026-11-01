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


@pytest.fixture(scope="module")
def nlp():
    # Shared by the tests of one file (loading takes a second or two), then
    # freed so it isn't still in memory when a real-model test runs
    model = spacy.load("en_core_web_lg")
    yield model
    del model
    gc.collect()
