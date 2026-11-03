from analyzer.models import Sentence
from analyzer.weather import LABELS, WEATHERS, chapter_weather


def book(*chapters):
    filler = " ".join(["word"] * 40)
    return [Sentence(i, f"{text} {filler}", 0, 0, i) for i, text in enumerate(chapters)]


def test_every_weather_has_a_label():
    assert set(LABELS) == set(WEATHERS)


def test_weather_words_choose_the_weather():
    sky = chapter_weather(book(
        "It was raining hard; the rain soaked her umbrella.",
        "The snow fell all night, and snowflakes covered the hedge.",
        "A thick fog lay on the marsh, and the mist hid the church.",
        "Bright sunshine; the sunlight warmed the cloudless morning.",
    ), 4)
    assert [w["kind"] for w in sky] == ["rain", "snow", "fog", "sun"]
    assert set(sky[0]["clues"]) <= {"rain", "umbrella"} and 0.3 <= sky[0]["strength"] <= 1


def test_thunder_turns_rain_into_a_storm():
    sky = chapter_weather(book("Rain, rain and more rain, then thunder and lightning split the sky."), 1)
    assert sky[0]["kind"] == "storm" and "thunder" in sky[0]["clues"]


def test_weather_is_never_carried_over():
    sky = chapter_weather(book("The rain and the wind and the rain again.", "They talked for an hour."), 2)
    assert sky[0]["kind"] == "rain" and sky[1] is None


def test_one_passing_word_is_not_weather():
    assert chapter_weather(book("Her words were a storm of feeling."), 1) == [None]
    assert chapter_weather([], 0) == []
