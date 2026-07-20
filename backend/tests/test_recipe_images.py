"""Unit tests for recipe cover-image search query shaping / scoring."""

from app.recipes.images import (
    _score_photo,
    food_search_queries,
    food_search_query,
)


def test_food_search_queries_prefer_parenthetical_dish_name():
    qs = food_search_queries("Korean Army Stew (Budae Jjigae)")
    assert qs[0] == "budae jjigae"
    assert any("stew" in q for q in qs)


def test_food_search_query_primary():
    assert food_search_query("Pan-Seared Salmon") == "pan seared salmon"


def test_food_search_query_empty_falls_back():
    assert food_search_queries("!!!") == ["homemade meal plated"]


def test_score_photo_rewards_keyword_overlap():
    photo = {
        "alt_description": "A bowl of spicy budae jjigae Korean army stew",
        "description": "",
        "tags": [{"title": "korean"}, {"title": "stew"}],
    }
    score = _score_photo(photo, ["budae", "jjigae", "korean", "stew"])
    assert score >= 2.5

    weak = _score_photo(
        {"alt_description": "fresh vegetables on a table", "tags": []},
        ["budae", "jjigae", "korean", "stew"],
    )
    assert weak < 1.5
