"""Baker's percentages and dough hydration.

Bakers express every ingredient as a percentage OF THE FLOUR WEIGHT
(flour itself = 100%). This makes recipes scale-free and comparable:
a "75% hydration" dough is recognizably wet whether it's 500 g or 5 kg
of flour.
"""


def bakers_percentages(ingredients_g: dict[str, float]) -> dict[str, float]:
    """Convert {'flour': 500, 'water': 375, ...} to percentages of flour.

    Any key containing 'flour' counts toward the flour total (so bread
    flour + rye flour recipes work).
    """
    flour_total = sum(g for name, g in ingredients_g.items() if "flour" in name.lower())
    if flour_total <= 0:
        raise ValueError("Recipe must contain flour to compute baker's percentages")
    return {
        name: round(grams / flour_total * 100, 1)
        for name, grams in ingredients_g.items()
    }


def hydration_percent(ingredients_g: dict[str, float]) -> float:
    """Water (and milk's water content) as a percent of flour weight."""
    pcts = bakers_percentages(ingredients_g)
    hydration = 0.0
    for name, pct in pcts.items():
        lowered = name.lower()
        if "water" in lowered:
            hydration += pct
        elif "milk" in lowered:
            hydration += pct * 0.87  # milk is ~87% water
    return round(hydration, 1)
