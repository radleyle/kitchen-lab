"""Tests for the deterministic safety logic (pure parts -- no database)."""

from app.safety.allergens import detect_allergens
from app.safety.temps import keyword_score


# ---------- Keyword scoring for temperature rules ----------

def test_keyword_score_counts_matches():
    poultry_kw = ["chicken", "turkey", "poultry", "thigh"]
    assert keyword_score("pan-seared chicken thigh", poultry_kw) == 2
    assert keyword_score("beef wellington", poultry_kw) == 0


def test_multiword_keywords_beat_single():
    # "ground beef burger" should score higher against the ground-meat rule
    # than the whole-cuts rule -- that's how disambiguation works.
    ground_kw = ["ground beef", "burger", "meatball"]
    whole_kw = ["beef", "steak", "roast"]
    query = "ground beef burger"
    assert keyword_score(query, ground_kw) > keyword_score(query, whole_kw)


# ---------- Allergen detection ----------

def test_detects_hidden_allergens():
    result = detect_allergens(["soy sauce", "panko breadcrumbs", "shrimp"])
    found = result["allergens_detected"]
    assert "soy sauce" in found["soybeans"]
    assert "soy sauce" in found["wheat"]  # soy sauce contains wheat!
    assert "panko breadcrumbs" in found["wheat"]
    assert "shrimp" in found["crustacean_shellfish"]


def test_butter_implies_milk():
    found = detect_allergens(["unsalted butter"])["allergens_detected"]
    assert "milk" in found


def test_false_friends_not_flagged():
    found = detect_allergens(["coconut milk", "buckwheat flour", "eggplant"])
    detected = found["allergens_detected"]
    assert "milk" not in detected  # coconut milk is not dairy
    assert "wheat" not in detected  # buckwheat flour is gluten-free
    assert "eggs" not in detected  # eggplant is not egg


def test_almond_milk_is_tree_nut_not_milk():
    detected = detect_allergens(["almond milk"])["allergens_detected"]
    assert "milk" not in detected
    assert "tree_nuts" in detected


def test_clean_ingredients_pass():
    result = detect_allergens(["chicken breast", "salt", "olive oil"])
    assert result["allergens_detected"] == {}
    assert "cross-contact" in result["note"]
