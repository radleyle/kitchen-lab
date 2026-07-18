"""Tests for deterministic kitchen personalization -- oven dials, boiling
point, dietary conflicts. No database, no LLM.
"""

import pytest

from app.kitchen.personalize import (
    apply_oven_offset_to_text,
    boiling_point_c,
    dial_for_desired_oven_f,
    dietary_conflicts,
    filter_substitutions_for_diet,
    kitchen_prompt_block,
    personalize_recipe,
)


def test_oven_running_cold_raises_dial():
    # Oven runs 15F cold (offset -15): to get 350 actual, dial 365.
    assert dial_for_desired_oven_f(350, -15) == 365


def test_oven_running_hot_lowers_dial():
    assert dial_for_desired_oven_f(350, 10) == 340


def test_apply_oven_offset_rewrites_fahrenheit_only():
    text = "Bake at 350F until golden, about 12 minutes. Rest at 20C."
    new, adj = apply_oven_offset_to_text(text, -15)
    assert "365F (dial; oven runs -15F)" in new
    assert "20C" in new  # Celsius left alone
    assert adj == [{"desired_f": 350.0, "dial_f": 365.0}]


def test_zero_offset_is_noop():
    text = "Bake at 350F"
    new, adj = apply_oven_offset_to_text(text, 0)
    assert new == text
    assert adj == []


def test_boiling_point_drops_with_elevation():
    assert boiling_point_c(0) == 100.0
    # Denver ~1600 m -> ~94.7C
    assert boiling_point_c(1600) == pytest.approx(94.7, abs=0.1)
    assert boiling_point_c(None) is None


def test_dietary_allergen_conflict():
    conflicts = dietary_conflicts(
        ["butter", "flour", "sugar"],
        {"allergens": ["milk"]},
    )
    assert any(c["kind"] == "allergen" and c["name"] == "milk" for c in conflicts)
    assert "butter" in conflicts[0]["triggered_by"]


def test_dietary_vegan_flags_eggs():
    conflicts = dietary_conflicts(
        ["egg", "flour"],
        {"diets": ["vegan"]},
    )
    assert any(c["kind"] == "diet" for c in conflicts)


def test_personalize_recipe_applies_offset_and_notes():
    recipe = {
        "ingredients": [{"ingredient": "butter"}, {"ingredient": "flour"}],
        "steps": [{"instruction": "Bake at 375F for 20 minutes."}],
    }
    snapshot = {
        "profile": {
            "oven_offset_f": -15,
            "elevation_m": 1600,
            "dietary_restrictions": {"allergens": ["milk"]},
            "preferences": {"salt_type": "diamond_kosher_salt"},
        },
        "equipment": [{"kind": "oven", "name": "Toaster oven", "details": {}}],
    }
    out = personalize_recipe(recipe, snapshot)
    assert "390F" in out["steps"][0]["instruction"]
    assert out["kitchen"]["oven_adjustments"]
    assert out["kitchen"]["dietary_conflicts"]
    assert out["kitchen"]["boiling_point_c"] == pytest.approx(94.7, abs=0.1)
    assert any("Diamond" in n or "diamond" in n for n in out["kitchen"]["notes"])


def test_kitchen_prompt_block_empty_without_profile():
    assert kitchen_prompt_block(None) == ""
    assert kitchen_prompt_block({"profile": {}, "equipment": []}) == ""


def test_kitchen_prompt_block_includes_equipment():
    block = kitchen_prompt_block(
        {
            "profile": {"oven_offset_f": -10, "cooktop_type": "induction"},
            "equipment": [
                {"kind": "air_fryer", "name": "Cosori 5.8qt", "details": {"watts": 1700}}
            ],
        }
    )
    assert "induction" in block
    assert "air_fryer" in block
    assert "do NOT adjust dial temps yourself" in block


def test_filter_substitutions_marks_diet_conflicts():
    options = [
        {"substitute": "butter", "ratio": 1.0},
        {"substitute": "vegetable oil", "ratio": 0.8},
    ]
    filtered = filter_substitutions_for_diet(
        options, {"allergens": ["milk"]}
    )
    # Oil first (no conflict), butter marked.
    assert filtered[0]["substitute"] == "vegetable oil"
    assert filtered[1].get("excluded_by_diet")
