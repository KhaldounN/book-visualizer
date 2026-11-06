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
    # 51 more famous books (2026-11-06), for a library of 100: each checked for its title and chapters
    "les_miserables.txt": "https://www.gutenberg.org/cache/epub/135/pg135.txt",
    "the_count_of_monte_cristo.txt": "https://www.gutenberg.org/cache/epub/1184/pg1184.txt",
    "the_three_musketeers.txt": "https://www.gutenberg.org/cache/epub/1257/pg1257.txt",
    "war_and_peace.txt": "https://www.gutenberg.org/cache/epub/2600/pg2600.txt",
    "anna_karenina.txt": "https://www.gutenberg.org/cache/epub/1399/pg1399.txt",
    "crime_and_punishment.txt": "https://www.gutenberg.org/cache/epub/2554/pg2554.txt",
    "the_brothers_karamazov.txt": "https://www.gutenberg.org/cache/epub/28054/pg28054.txt",
    "don_quixote.txt": "https://www.gutenberg.org/cache/epub/996/pg996.txt",
    "madame_bovary.txt": "https://www.gutenberg.org/cache/epub/2413/pg2413.txt",
    "middlemarch.txt": "https://www.gutenberg.org/cache/epub/145/pg145.txt",
    "northanger_abbey.txt": "https://www.gutenberg.org/cache/epub/121/pg121.txt",
    "mansfield_park.txt": "https://www.gutenberg.org/cache/epub/141/pg141.txt",
    "david_copperfield.txt": "https://www.gutenberg.org/cache/epub/766/pg766.txt",
    "bleak_house.txt": "https://www.gutenberg.org/cache/epub/1023/pg1023.txt",
    "hard_times.txt": "https://www.gutenberg.org/cache/epub/786/pg786.txt",
    "vanity_fair.txt": "https://www.gutenberg.org/cache/epub/599/pg599.txt",
    "tess_of_the_durbervilles.txt": "https://www.gutenberg.org/cache/epub/110/pg110.txt",
    "far_from_the_madding_crowd.txt": "https://www.gutenberg.org/cache/epub/107/pg107.txt",
    "silas_marner.txt": "https://www.gutenberg.org/cache/epub/550/pg550.txt",
    "the_mill_on_the_floss.txt": "https://www.gutenberg.org/cache/epub/6688/pg6688.txt",
    "ivanhoe.txt": "https://www.gutenberg.org/cache/epub/82/pg82.txt",
    "kidnapped.txt": "https://www.gutenberg.org/cache/epub/421/pg421.txt",
    "the_prince_and_the_pauper.txt": "https://www.gutenberg.org/cache/epub/1837/pg1837.txt",
    "a_connecticut_yankee.txt": "https://www.gutenberg.org/cache/epub/86/pg86.txt",
    "the_age_of_innocence.txt": "https://www.gutenberg.org/cache/epub/541/pg541.txt",
    "ethan_frome.txt": "https://www.gutenberg.org/cache/epub/4517/pg4517.txt",
    "uncle_toms_cabin.txt": "https://www.gutenberg.org/cache/epub/203/pg203.txt",
    "the_red_badge_of_courage.txt": "https://www.gutenberg.org/cache/epub/73/pg73.txt",
    "heart_of_darkness.txt": "https://www.gutenberg.org/cache/epub/219/pg219.txt",
    "lord_jim.txt": "https://www.gutenberg.org/cache/epub/5658/pg5658.txt",
    "sons_and_lovers.txt": "https://www.gutenberg.org/cache/epub/217/pg217.txt",
    "a_room_with_a_view.txt": "https://www.gutenberg.org/cache/epub/2641/pg2641.txt",
    "howards_end.txt": "https://www.gutenberg.org/cache/epub/2946/pg2946.txt",
    "martin_eden.txt": "https://www.gutenberg.org/cache/epub/1056/pg1056.txt",
    "the_island_of_doctor_moreau.txt": "https://www.gutenberg.org/cache/epub/159/pg159.txt",
    "king_solomons_mines.txt": "https://www.gutenberg.org/cache/epub/2166/pg2166.txt",
    "the_scarlet_pimpernel.txt": "https://www.gutenberg.org/cache/epub/60/pg60.txt",
    "the_prisoner_of_zenda.txt": "https://www.gutenberg.org/cache/epub/95/pg95.txt",
    "pollyanna.txt": "https://www.gutenberg.org/cache/epub/1450/pg1450.txt",
    "kim.txt": "https://www.gutenberg.org/cache/epub/2226/pg2226.txt",
    "the_hunchback_of_notre_dame.txt": "https://www.gutenberg.org/cache/epub/2610/pg2610.txt",
    "candide.txt": "https://www.gutenberg.org/cache/epub/19942/pg19942.txt",
    "north_and_south.txt": "https://www.gutenberg.org/cache/epub/4276/pg4276.txt",
    "the_moonstone.txt": "https://www.gutenberg.org/cache/epub/155/pg155.txt",
    "the_woman_in_white.txt": "https://www.gutenberg.org/cache/epub/583/pg583.txt",
    "the_lost_world.txt": "https://www.gutenberg.org/cache/epub/139/pg139.txt",
    "tarzan_of_the_apes.txt": "https://www.gutenberg.org/cache/epub/78/pg78.txt",
    "the_mysterious_island.txt": "https://www.gutenberg.org/cache/epub/1268/pg1268.txt",
    "my_antonia.txt": "https://www.gutenberg.org/cache/epub/242/pg242.txt",
    "the_metamorphosis.txt": "https://www.gutenberg.org/cache/epub/5200/pg5200.txt",
    "ben_hur.txt": "https://www.gutenberg.org/cache/epub/2145/pg2145.txt",
}
# The website lists the books directly in data/: every book above (100) except a few kept aside in
# data/more/: the Bible and the Quran (offered briefly, removed at the owner's request) and The Jungle
# Book (separate stories with no chapters, which the analysis isn't made for).
ASIDE = {"the_bible.txt", "the_quran.txt", "the_jungle_book.txt"}


def main() -> None:
    (DATA_DIR / "more").mkdir(parents=True, exist_ok=True)
    for name, url in SAMPLES.items():
        target = DATA_DIR / "more" / name if name in ASIDE else DATA_DIR / name
        if target.exists():
            print(f"Already have {name}")
            continue
        print(f"Downloading {name} ...")
        with urlopen(url) as response:
            target.write_bytes(response.read())
        print(f"Saved {target} ({target.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
