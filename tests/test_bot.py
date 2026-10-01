from pathlib import Path

import pytest

from chatbot import DataError, Store, answer
from chatbot.parser import parse
from evals.phrasings import CASES

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def store():
    return Store.load(FIXTURES)


# --- the four example queries -------------------------------------------------------------------

def test_hotel_in_paris_under_90(store):
    reply = answer(store, "Find me a hotel in Paris under 90")
    assert "Hotel Petit Jardin" in reply and "Rue Vivienne Inn" in reply
    assert "Seine Side Rooms" not in reply  # priced exactly 90: 'under' is strict
    assert "Le Marais Boutique" not in reply and "Miami" not in reply


def test_french_restaurants_in_miami(store):
    reply = answer(store, "Show me French restaurants in Miami")
    assert "Bistro Brickell" in reply and "Maison Wynwood" in reply
    assert "Le Petit Comptoir" not in reply  # French, but in Paris
    assert "Island Spice Kitchen" not in reply  # Miami, but Caribbean


def test_compound_query_uses_same_city(store):
    reply = answer(store, "Find me a hotel in Miami under 100 and a Caribbean restaurant in the same city")
    assert "South Beach Hostelry" in reply and "Biscayne Bay Motel" in reply
    assert "Wynwood Lofts" not in reply  # priced exactly 100
    assert "Island Spice Kitchen" in reply and "Calypso Grill" in reply
    assert "Maison Wynwood" not in reply  # French, not Caribbean
    assert "Paris" not in reply


def test_luxury_hotels_in_paris_above_500(store):
    reply = answer(store, "Find me luxury hotels in Paris above 500")
    assert "Grand Palais Royale" in reply and "Maison Etoile" in reply
    assert "Le Marais Boutique" not in reply and "Coral Gables Grand" not in reply


# --- boundary semantics --------------------------------------------------------------------------

def test_at_most_is_inclusive(store):
    assert "Seine Side Rooms" in answer(store, "hotels in Paris at most 90")


def test_at_least_is_inclusive_and_above_is_strict(store):
    assert "Wynwood Lofts" in answer(store, "hotels in Miami at least 100")
    assert "Wynwood Lofts" not in answer(store, "hotels in Miami above 100")


def test_between_is_inclusive(store):
    reply = answer(store, "hotels in Paris between 90 and 165")
    assert "Seine Side Rooms" in reply and "Le Marais Boutique" in reply
    assert "Rue Vivienne Inn" not in reply and "Grand Palais Royale" not in reply


def test_no_match_reports_the_price_range(store):
    reply = answer(store, "hotels in Paris under 10")
    assert "No matches" in reply and "range from 78 to 780" in reply


# --- honesty: say what was not understood ----------------------------------------------------------

def test_unknown_words_are_reported_not_guessed(store):
    reply = answer(store, "somewhere cheap to stay in Paris")
    assert "'cheap'" in reply and "ignored" in reply


def test_unknown_city_asks_instead_of_guessing(store):
    reply = answer(store, "hotels in Tokyo under 200")
    assert "Which city" in reply and "Paris" in reply and "Hotel Petit Jardin" not in reply


def test_unrelated_text_shows_help(store):
    assert "I can find hotels and restaurants" in answer(store, "what's the weather in Paris?")


# --- structure -------------------------------------------------------------------------------------

def test_parse_produces_structured_clauses(store):
    parsed = parse("Find me a hotel in Miami under 100 and a Caribbean restaurant in the same city", store.vocab)
    hotel, restaurant = parsed.clauses
    assert (hotel.kind, hotel.cities, hotel.price.hi, hotel.price.hi_incl) == ("hotel", ["miami"], 100, False)
    assert (restaurant.kind, restaurant.cities, restaurant.cuisines) == ("restaurant", ["miami"], ["caribbean"])
    assert parsed.status == "full"


def test_phrasing_eval_statuses_do_not_regress(store):
    for text, expected, _note in CASES:
        assert parse(text, store.vocab).status == expected, text


# --- data layer ------------------------------------------------------------------------------------

def test_missing_data_file_is_a_clear_error(tmp_path):
    with pytest.raises(DataError, match="missing data file"):
        Store.load(tmp_path)


def test_record_without_city_is_rejected(tmp_path):
    (tmp_path / "hotels.json").write_text('[{"name": "X", "price": 5}]')
    (tmp_path / "restaurants.json").write_text("[]")
    with pytest.raises(DataError, match="need 'name' and 'city'"):
        Store.load(tmp_path)


def test_vocabulary_comes_from_the_data(tmp_path):
    (tmp_path / "hotels.json").write_text('[{"name": "H", "city": "New York", "price": 50}]')
    (tmp_path / "restaurants.json").write_text('[{"name": "R", "city": "New York", "cuisine": "Thai", "price": 20}]')
    store = Store.load(tmp_path)
    assert "H" in answer(store, "hotels in new york under 60")
    assert "R" in answer(store, "thai restaurants in New York")
