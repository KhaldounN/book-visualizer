"""Download public-domain test novels from Project Gutenberg into data/."""

from pathlib import Path
from urllib.request import urlopen

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# file name -> Project Gutenberg plain-text URL
SAMPLES = {
    "great_expectations.txt": "https://www.gutenberg.org/cache/epub/1400/pg1400.txt",  # the website's sample book
    "pride_and_prejudice.txt": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
    # famous books with very different settings and weather, to try the Story road with
    "alice_in_wonderland.txt": "https://www.gutenberg.org/cache/epub/11/pg11.txt",
    "a_christmas_carol.txt": "https://www.gutenberg.org/cache/epub/46/pg46.txt",
    "the_wonderful_wizard_of_oz.txt": "https://www.gutenberg.org/cache/epub/55/pg55.txt",
    "the_call_of_the_wild.txt": "https://www.gutenberg.org/cache/epub/215/pg215.txt",
    "treasure_island.txt": "https://www.gutenberg.org/cache/epub/120/pg120.txt",
    "the_hound_of_the_baskervilles.txt": "https://www.gutenberg.org/cache/epub/2852/pg2852.txt",
    "frankenstein.txt": "https://www.gutenberg.org/cache/epub/84/pg84.txt",
    "wuthering_heights.txt": "https://www.gutenberg.org/cache/epub/768/pg768.txt",
    "dracula.txt": "https://www.gutenberg.org/cache/epub/345/pg345.txt",
    # 39 more famous public-domain story books, for a library of 50
    "jane_eyre.txt": "https://www.gutenberg.org/cache/epub/1260/pg1260.txt",
    "sense_and_sensibility.txt": "https://www.gutenberg.org/cache/epub/161/pg161.txt",
    "emma.txt": "https://www.gutenberg.org/cache/epub/158/pg158.txt",
    "persuasion.txt": "https://www.gutenberg.org/cache/epub/105/pg105.txt",
    "the_adventures_of_tom_sawyer.txt": "https://www.gutenberg.org/cache/epub/74/pg74.txt",
    "adventures_of_huckleberry_finn.txt": "https://www.gutenberg.org/cache/epub/76/pg76.txt",
    "the_adventures_of_sherlock_holmes.txt": "https://www.gutenberg.org/cache/epub/1661/pg1661.txt",
    "a_study_in_scarlet.txt": "https://www.gutenberg.org/cache/epub/244/pg244.txt",
    "the_sign_of_the_four.txt": "https://www.gutenberg.org/cache/epub/2097/pg2097.txt",
    "little_women.txt": "https://www.gutenberg.org/cache/epub/514/pg514.txt",
    "anne_of_green_gables.txt": "https://www.gutenberg.org/cache/epub/45/pg45.txt",
    "the_secret_garden.txt": "https://www.gutenberg.org/cache/epub/113/pg113.txt",
    "a_little_princess.txt": "https://www.gutenberg.org/cache/epub/146/pg146.txt",
    "peter_pan.txt": "https://www.gutenberg.org/cache/epub/16/pg16.txt",
    "the_jungle_book.txt": "https://www.gutenberg.org/cache/epub/236/pg236.txt",
    "black_beauty.txt": "https://www.gutenberg.org/cache/epub/271/pg271.txt",
    "heidi.txt": "https://www.gutenberg.org/cache/epub/1448/pg1448.txt",
    "the_picture_of_dorian_gray.txt": "https://www.gutenberg.org/cache/epub/174/pg174.txt",
    "dr_jekyll_and_mr_hyde.txt": "https://www.gutenberg.org/cache/epub/43/pg43.txt",
    "the_time_machine.txt": "https://www.gutenberg.org/cache/epub/35/pg35.txt",
    "the_war_of_the_worlds.txt": "https://www.gutenberg.org/cache/epub/36/pg36.txt",
    "the_invisible_man.txt": "https://www.gutenberg.org/cache/epub/5230/pg5230.txt",
    "twenty_thousand_leagues_under_the_sea.txt": "https://www.gutenberg.org/cache/epub/164/pg164.txt",
    "around_the_world_in_eighty_days.txt": "https://www.gutenberg.org/cache/epub/103/pg103.txt",
    "journey_to_the_centre_of_the_earth.txt": "https://www.gutenberg.org/cache/epub/18857/pg18857.txt",
    "oliver_twist.txt": "https://www.gutenberg.org/cache/epub/730/pg730.txt",
    "a_tale_of_two_cities.txt": "https://www.gutenberg.org/cache/epub/98/pg98.txt",
    "the_scarlet_letter.txt": "https://www.gutenberg.org/cache/epub/33/pg33.txt",
    "white_fang.txt": "https://www.gutenberg.org/cache/epub/910/pg910.txt",
    "the_last_of_the_mohicans.txt": "https://www.gutenberg.org/cache/epub/940/pg940.txt",
    "gullivers_travels.txt": "https://www.gutenberg.org/cache/epub/829/pg829.txt",
    "robinson_crusoe.txt": "https://www.gutenberg.org/cache/epub/521/pg521.txt",
    "the_wind_in_the_willows.txt": "https://www.gutenberg.org/cache/epub/289/pg289.txt",
    "through_the_looking_glass.txt": "https://www.gutenberg.org/cache/epub/12/pg12.txt",
    "moby_dick.txt": "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
    "the_great_gatsby.txt": "https://www.gutenberg.org/cache/epub/64317/pg64317.txt",
    "the_phantom_of_the_opera.txt": "https://www.gutenberg.org/cache/epub/175/pg175.txt",
    "pinocchio.txt": "https://www.gutenberg.org/cache/epub/500/pg500.txt",
    "the_mysterious_affair_at_styles.txt": "https://www.gutenberg.org/cache/epub/863/pg863.txt",
    # scriptures (the owner asked for them): chapters are the Bible's books and the Quran's suras
    "the_bible.txt": "https://www.gutenberg.org/cache/epub/10/pg10.txt",  # King James Version
    "the_quran.txt": "https://www.gutenberg.org/cache/epub/2800/pg2800.txt",  # J. M. Rodwell's translation
}
# The website lists only the books directly in data/ (the owner chose 10 famous ones); the rest go
# to data/more/, where they are kept but not offered.
LIBRARY = {"pride_and_prejudice.txt", "great_expectations.txt", "frankenstein.txt", "dracula.txt",
           "alice_in_wonderland.txt", "wuthering_heights.txt", "the_hound_of_the_baskervilles.txt",
           "the_wonderful_wizard_of_oz.txt", "jane_eyre.txt", "a_christmas_carol.txt"}
# (the Bible and the Quran were offered for a while, then taken off the website at the owner's request:
# they still download into data/more/)


def main() -> None:
    (DATA_DIR / "more").mkdir(parents=True, exist_ok=True)
    for name, url in SAMPLES.items():
        target = DATA_DIR / name if name in LIBRARY else DATA_DIR / "more" / name
        if target.exists():
            print(f"Already have {name}")
            continue
        print(f"Downloading {name} ...")
        with urlopen(url) as response:
            target.write_bytes(response.read())
        print(f"Saved {target} ({target.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
