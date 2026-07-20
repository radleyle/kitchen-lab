"""Tests for the deterministic calculators.

Run inside the backend container:
    docker compose exec backend pytest -v

Each test asserts against values checked by hand or against standard
culinary references. If a refactor ever changes an answer, these go red.
"""

import pytest

from app.calculators.baking import bakers_percentages, hydration_percent
from app.calculators.brine import equilibrium_salt, salt_for_brine, salt_grams_to_tbsp
from app.calculators.scaling import scale_recipe
from app.calculators.units import (
    c_to_f,
    convert_mass,
    convert_volume,
    f_to_c,
    volume_to_grams,
)


# ---------- Temperature ----------

def test_temperature_roundtrip():
    assert f_to_c(212) == pytest.approx(100)  # water boils
    assert f_to_c(32) == pytest.approx(0)  # water freezes
    assert c_to_f(74) == pytest.approx(165.2)  # poultry safe temp
    # Converting there and back should return the original.
    assert f_to_c(c_to_f(63)) == pytest.approx(63)


# ---------- Mass and volume ----------

def test_mass_conversion():
    assert convert_mass(1, "lb", "g") == pytest.approx(453.592)
    assert convert_mass(16, "oz", "lb") == pytest.approx(1)


def test_volume_conversion():
    # rel=1e-3 -> "within 0.1%". Floats are never compared with bare ==;
    # rounded reference constants make the ratio 15.99994..., not 16.
    assert convert_volume(1, "cup", "tbsp") == pytest.approx(16, rel=1e-3)
    assert convert_volume(3, "tsp", "tbsp") == pytest.approx(1, rel=1e-3)


def test_unknown_unit_raises():
    with pytest.raises(ValueError):
        convert_mass(1, "stone", "g")


# ---------- Volume -> mass depends on ingredient ----------

def test_cup_of_flour_vs_cup_of_water():
    flour = volume_to_grams(1, "cup", "all_purpose_flour")
    water = volume_to_grams(1, "cup", "water")
    assert flour == pytest.approx(120, rel=0.02)  # ~120 g/cup
    assert water == pytest.approx(237, rel=0.01)  # ~237 g/cup
    assert flour < water  # same volume, very different mass


def test_unknown_ingredient_raises():
    with pytest.raises(ValueError):
        volume_to_grams(1, "cup", "unicorn_dust")


# ---------- Brine ----------

def test_salt_for_standard_brine():
    # 1 liter of water (1000 g) at 5% -> 50 g salt
    assert salt_for_brine(1000, 5) == 50.0


def test_brine_rejects_impossible_strength():
    with pytest.raises(ValueError):
        salt_for_brine(1000, 30)  # beyond saturation (~26%)


def test_equilibrium_salt():
    # 800 g chicken + 700 g water = 1500 g total at 2% -> 30 g
    assert equilibrium_salt(1500, 2.0) == 30.0


def test_equilibrium_salt_rejects_high_percent():
    with pytest.raises(ValueError):
        equilibrium_salt(500, 6.0)


def test_salt_brands_differ():
    # The same 30 g is ~2 tbsp table salt but ~3.6 tbsp Diamond kosher.
    table = salt_grams_to_tbsp(30, "table_salt")
    diamond = salt_grams_to_tbsp(30, "diamond_kosher_salt")
    assert table == pytest.approx(1.66, abs=0.05)
    assert diamond == pytest.approx(3.56, abs=0.05)
    assert diamond > table * 2  # Diamond is fluffier: >2x the volume


# ---------- Scaling ----------

def test_scale_up():
    scaled = scale_recipe(
        [{"name": "chicken breast", "amount": 450, "unit": "g"}],
        original_servings=2,
        target_servings=6,
    )
    assert scaled[0].amount == 1350
    assert scaled[0].note is None  # chicken scales linearly, no warning


def test_scaling_flags_leavening_at_large_factors():
    scaled = scale_recipe(
        [{"name": "instant yeast", "amount": 7, "unit": "g"}],
        original_servings=2,
        target_servings=8,  # 4x -> warning expected
    )
    assert scaled[0].note is not None


def test_scale_rejects_zero_servings():
    with pytest.raises(ValueError):
        scale_recipe([], original_servings=0, target_servings=4)


# ---------- Baking ----------

def test_bakers_percentages():
    pcts = bakers_percentages({"bread flour": 500, "water": 375, "salt": 10})
    assert pcts["bread flour"] == 100.0
    assert pcts["water"] == 75.0
    assert pcts["salt"] == 2.0


def test_multiple_flours_count_together():
    pcts = bakers_percentages({"bread flour": 400, "rye flour": 100, "water": 350})
    assert pcts["water"] == 70.0  # of the 500 g combined flour


def test_hydration_counts_milk_water_content():
    plain = hydration_percent({"flour": 500, "water": 350})
    with_milk = hydration_percent({"flour": 500, "water": 300, "milk": 100})
    assert plain == 70.0
    # 300 water + 100 milk * 0.87 = 387 -> 77.4%
    assert with_milk == pytest.approx(77.4)


def test_no_flour_raises():
    with pytest.raises(ValueError):
        bakers_percentages({"water": 100})
