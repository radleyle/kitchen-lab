"""Tests for the deterministic parts of recipe generation: citation
mapping and the safety-floor enforcement (the pass that outranks the LLM).
The LLM call itself is not under test here.
"""

import pytest
from types import SimpleNamespace

import app.recipes.generator as gen
from app.recipes.generator import _attach_citations, _standardize_ingredients


def make_passages(n: int) -> list[dict]:
    return [
        {
            "claim": f"claim {i}",
            "confidence": "high",
            "scope": "test",
            "source": {"title": f"source {i}"},
        }
        for i in range(1, n + 1)
    ]


def test_attach_citations_maps_indices_to_objects():
    steps = [{"instruction": "sear", "citations_used": [2, 1]}]
    _attach_citations(steps, make_passages(3))
    assert [c["claim"] for c in steps[0]["citations"]] == ["claim 2", "claim 1"]
    assert "citations_used" not in steps[0]


def test_attach_citations_drops_out_of_range_and_junk():
    steps = [{"instruction": "sear", "citations_used": [0, 99, "two", 3]}]
    _attach_citations(steps, make_passages(3))
    assert [c["claim"] for c in steps[0]["citations"]] == ["claim 3"]


def test_safety_floor_raises_low_temperature(monkeypatch):
    fake_rule = SimpleNamespace(min_internal_temp_c=73.9, food="chicken")
    monkeypatch.setattr(gen, "find_temp_rule", lambda db, q: fake_rule)
    monkeypatch.setattr(gen, "rule_to_response", lambda r: {"food": r.food})

    steps = [
        {"instruction": "sear the thighs", "target_internal_temp_c": None},
        {"instruction": "roast until done", "target_internal_temp_c": 65},
    ]
    result = gen._enforce_safety_floor(None, "chicken thighs", steps)

    assert steps[1]["target_internal_temp_c"] == 73.9
    assert "74C" in steps[1]["instruction"]  # visible, not silent
    assert result["overrides"] == [
        {"step": 2, "proposed_c": 65, "enforced_c": 73.9, "rule": "chicken"}
    ]
    assert steps[0]["target_internal_temp_c"] is None  # untouched


def test_safety_floor_leaves_compliant_temps_alone(monkeypatch):
    fake_rule = SimpleNamespace(min_internal_temp_c=62.8, food="pork")
    monkeypatch.setattr(gen, "find_temp_rule", lambda db, q: fake_rule)
    monkeypatch.setattr(gen, "rule_to_response", lambda r: {"food": r.food})

    steps = [{"instruction": "roast", "target_internal_temp_c": 63}]
    result = gen._enforce_safety_floor(None, "pork loin", steps)
    assert steps[0]["target_internal_temp_c"] == 63
    assert result["overrides"] == []


def test_safety_floor_no_rule_is_a_noop(monkeypatch):
    monkeypatch.setattr(gen, "find_temp_rule", lambda db, q: None)
    steps = [{"instruction": "simmer", "target_internal_temp_c": 40}]
    result = gen._enforce_safety_floor(None, "tomato sauce", steps)
    assert result == {"safety": None, "overrides": []}
    assert steps[0]["target_internal_temp_c"] == 40


def test_standardize_volume_with_density():
    out = _standardize_ingredients(
        [{"ingredient": "flour", "quantity": 3, "unit": "cup",
          "density_key": "all_purpose_flour", "amount": "3 cups", "note": ""}]
    )
    assert out[0]["grams"] == pytest.approx(362, abs=1)  # 3 x ~120.7 g
    assert out[0]["amount"] == "3 cups"


def test_standardize_tsp_is_not_a_cup():
    # The bug that motivated this design: the LLM once used per-cup gram
    # figures for teaspoon measures. Python arithmetic cannot make it.
    out = _standardize_ingredients(
        [{"ingredient": "salt", "quantity": 1, "unit": "tsp",
          "density_key": "table_salt", "amount": "", "note": ""}]
    )
    assert out[0]["grams"] == pytest.approx(6.0, abs=0.1)
    assert out[0]["amount"] == "1 tsp"  # built from parsed qty/unit


def test_standardize_mass_units_need_no_density():
    out = _standardize_ingredients(
        [{"ingredient": "chocolate", "quantity": 8, "unit": "oz",
          "density_key": None, "amount": "", "note": "chopped"}]
    )
    assert out[0]["grams"] == pytest.approx(226.8, abs=0.1)


def test_standardize_plural_units_and_name_fallback():
    # "cups" (plural) + missing density_key but a recognizable name:
    # both normalizations are deterministic Python, not LLM judgment.
    out = _standardize_ingredients(
        [{"ingredient": "all-purpose flour", "quantity": 3, "unit": "cups",
          "density_key": None, "amount": "3 cups", "note": ""}]
    )
    assert out[0]["grams"] == pytest.approx(362, abs=1)


def test_standardize_unknown_measures_stay_untouched():
    out = _standardize_ingredients(
        [{"ingredient": "eggs", "quantity": None, "unit": None,
          "density_key": None, "amount": "2 large", "note": ""},
         {"ingredient": "chips", "quantity": 2, "unit": "cup",
          "density_key": None, "amount": "", "note": ""}]
    )
    assert out[0]["grams"] is None
    assert out[0]["amount"] == "2 large"
    # Volume without a density stays a volume -- no guessed grams.
    assert out[1]["grams"] is None
    assert out[1]["amount"] == "2 cup"
