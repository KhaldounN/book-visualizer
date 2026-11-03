from analyzer.models import Sentence
from analyzer.pace import chapter_pace, grade_label, measure, pace_scores, richness, syllables


def sentences(*texts: str, chapter: int = 0, tags: dict | None = None) -> list[Sentence]:
    return [Sentence(i, t, 0, len(t), chapter, tags=tags) for i, t in enumerate(texts)]


def test_syllables_are_counted_from_vowel_groups():
    assert [syllables(w) for w in ("cat", "reading", "made", "table", "beautiful", "rhythm")] == [1, 2, 1, 2, 3, 1]


def test_richness_is_the_share_of_different_words_per_stretch():
    assert richness(["a", "b", "a", "b"]) == 0.5
    assert richness(["w"] * 300) == 1 / 100  # one word repeated: 1 different word in every 100
    assert richness([f"w{i}" for i in range(300)]) == 1.0
    assert richness([]) == 0.0


def test_measure_reads_time_length_and_level():
    simple = measure(sentences("The cat sat.", "The dog ran."))
    assert (simple.words, simple.sentence_length) == (6, 3.0)
    assert simple.minutes == 6 / 230
    assert simple.grade < 0 < measure(sentences(
        "Notwithstanding considerable deliberation, the philosophical gentleman remained extraordinarily "
        "unconvinced regarding the respectability of their intentions.")).grade
    assert simple.action is None  # no word types saved
    tagged = measure(sentences("He ran.", tags={"VERB": 3, "ADJ": 1}))
    assert tagged.action == 0.75


def test_chapter_pace_and_scores():
    fast = sentences(*["He ran. She hid."] * 30, chapter=0)
    slow = sentences(*["The long and quiet and very green valley lay sleeping under the soft grey sky."] * 30,
                     chapter=1)
    paces = chapter_pace(fast + slow, 2, dialogue=[0.6, 0.1])
    assert paces[0].dialogue == 0.6 and paces[0].sentence_length < paces[1].sentence_length
    scores = pace_scores(paces)
    assert scores[0] > 0 > scores[1]
    assert pace_scores(paces[:1]) == [0.0]  # one chapter: nothing to compare with


def test_grade_labels():
    assert grade_label(4) == "very easy" and grade_label(9) == "average" and grade_label(16) == "very hard"
