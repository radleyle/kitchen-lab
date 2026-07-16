"""Brine and pre-salting math.

A brine's strength is expressed as salt mass / water mass * 100.
Typical ranges (surfaced to users as validated guidance, with sources
attached at the knowledge layer):
  - 3.5-5%: standard poultry brine, 1-12 hours depending on cut
  - 5-8%:   quick brines for thin cuts
  - ~2%:    equilibrium brining / pre-salting by total mass
"""

from app.calculators.units import DENSITY_G_PER_ML


def salt_for_brine(water_g: float, brine_percent: float) -> float:
    """Grams of salt needed for a given water mass and brine strength."""
    if water_g <= 0:
        raise ValueError("Water mass must be positive")
    if not 0 < brine_percent <= 26:  # ~26% is saturation; beyond is impossible
        raise ValueError("Brine percent must be between 0 and 26")
    return round(water_g * brine_percent / 100, 1)


def equilibrium_salt(total_mass_g: float, target_percent: float = 2.0) -> float:
    """Salt for equilibrium brining: percent of TOTAL (meat + water) mass.

    Unlike a strong soak-and-rinse brine, equilibrium brining can't
    over-salt -- the whole system settles at the target concentration.
    """
    if total_mass_g <= 0:
        raise ValueError("Total mass must be positive")
    if not 0 < target_percent <= 5:
        raise ValueError("Equilibrium target is typically 0.5-2.5%; max 5")
    return round(total_mass_g * target_percent / 100, 1)


# Salt brands differ hugely in crystal density -- "1 tbsp of salt" is
# ambiguous. We convert brand-specific volume to grams for accuracy.
SALT_TYPES = ("table_salt", "morton_kosher_salt", "diamond_kosher_salt")


def salt_grams_to_tbsp(grams: float, salt_type: str) -> float:
    """How many tablespoons of a specific salt equal this many grams."""
    if salt_type not in SALT_TYPES:
        raise ValueError(f"salt_type must be one of {SALT_TYPES}")
    grams_per_tbsp = DENSITY_G_PER_ML[salt_type] * 14.7868  # ml per tbsp
    return round(grams / grams_per_tbsp, 2)
