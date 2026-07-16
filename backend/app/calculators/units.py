"""Unit conversions: temperature, mass, and ingredient-aware volume->mass."""


# ---------- Temperature ----------

def f_to_c(fahrenheit: float) -> float:
    return (fahrenheit - 32) * 5 / 9


def c_to_f(celsius: float) -> float:
    return celsius * 9 / 5 + 32


# ---------- Mass ----------

GRAMS_PER = {
    "g": 1.0,
    "kg": 1000.0,
    "oz": 28.3495,
    "lb": 453.592,
}


def convert_mass(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit not in GRAMS_PER or to_unit not in GRAMS_PER:
        raise ValueError(f"Unknown mass unit: {from_unit!r} or {to_unit!r}")
    return value * GRAMS_PER[from_unit] / GRAMS_PER[to_unit]


# ---------- Volume ----------

ML_PER = {
    "ml": 1.0,
    "l": 1000.0,
    "tsp": 4.92892,
    "tbsp": 14.7868,
    "cup": 236.588,  # US cup
    "fl_oz": 29.5735,
    "quart": 946.353,
}


def convert_volume(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit not in ML_PER or to_unit not in ML_PER:
        raise ValueError(f"Unknown volume unit: {from_unit!r} or {to_unit!r}")
    return value * ML_PER[from_unit] / ML_PER[to_unit]


# ---------- Volume -> mass (ingredient-dependent!) ----------
# A cup of flour and a cup of honey weigh very different amounts.
# Densities in grams per ml, from standard culinary references.

DENSITY_G_PER_ML = {
    "water": 1.0,
    "milk": 1.03,
    "all_purpose_flour": 0.51,  # ~120 g per US cup, spoon-and-level
    "bread_flour": 0.51,
    "granulated_sugar": 0.85,  # ~200 g per cup
    "brown_sugar_packed": 0.93,
    "butter": 0.96,
    "vegetable_oil": 0.92,
    "honey": 1.42,
    "table_salt": 1.22,  # ~18 g per tbsp
    "morton_kosher_salt": 1.02,  # ~15 g per tbsp
    "diamond_kosher_salt": 0.57,  # ~8.4 g per tbsp -- half of Morton!
    "cornstarch": 0.54,
    "baking_soda": 0.97,
}


def volume_to_grams(value: float, unit: str, ingredient: str) -> float:
    """Convert a volume measure of a known ingredient to grams."""
    if ingredient not in DENSITY_G_PER_ML:
        raise ValueError(
            f"No density on record for {ingredient!r}. "
            f"Known: {sorted(DENSITY_G_PER_ML)}"
        )
    ml = convert_volume(value, unit, "ml")
    return ml * DENSITY_G_PER_ML[ingredient]
