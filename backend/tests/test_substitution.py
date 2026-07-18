"""Tests for the pure ingredient-matching functions. The join itself is
SQL and the function classification is the LLM's; what must never be
flaky is mapping a user's phrase to the right canonical ingredient.
"""

from app.substitution.engine import best_ingredient_match, normalize

CANDIDATES = [
    ("egg", ["eggs", "whole egg", "large egg"]),
    ("egg white", ["egg whites"]),
    ("cornstarch", ["corn starch", "cornflour (UK)"]),
    ("all-purpose flour", ["ap flour", "plain flour"]),
    ("butter", ["unsalted butter"]),
]


def test_normalize_plurals():
    assert normalize("Eggs ") == "egg"
    assert normalize("tomatoes") == "tomato"
    assert normalize("egg whites") == "egg white"
    assert normalize("butter") == "butter"


def test_exact_and_alias_match():
    assert best_ingredient_match("egg", CANDIDATES) == "egg"
    assert best_ingredient_match("Eggs", CANDIDATES) == "egg"
    assert best_ingredient_match("corn starch", CANDIDATES) == "cornstarch"
    assert best_ingredient_match("plain flour", CANDIDATES) == "all-purpose flour"


def test_longest_match_wins():
    # "egg whites" must resolve to "egg white", not the shorter "egg".
    assert best_ingredient_match("egg whites", CANDIDATES) == "egg white"


def test_containment_match():
    assert best_ingredient_match("3 large eggs", CANDIDATES) == "egg"
    assert best_ingredient_match("a stick of butter", CANDIDATES) == "butter"


def test_no_match_returns_none():
    assert best_ingredient_match("saffron", CANDIDATES) is None
