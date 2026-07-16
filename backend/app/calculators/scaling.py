"""Recipe scaling: multiply a recipe up or down without LLM guesswork."""

from dataclasses import dataclass


@dataclass
class ScaledIngredient:
    name: str
    amount: float
    unit: str
    note: str | None = None


def scale_recipe(
    ingredients: list[dict],
    original_servings: int,
    target_servings: int,
) -> list[ScaledIngredient]:
    """Scale each ingredient linearly by target/original servings.

    Each input dict: {"name": str, "amount": float, "unit": str}.
    Linear scaling is correct for ingredients; cooking TIME and pan size
    do not scale linearly -- that caveat is flagged in the note so the
    explanation layer can surface it.
    """
    if original_servings <= 0 or target_servings <= 0:
        raise ValueError("Servings must be positive")

    factor = target_servings / original_servings
    scaled = []
    for ing in ingredients:
        amount = round(ing["amount"] * factor, 2)
        note = None
        # Leavening and salt become noticeably off when scaled far;
        # flag them rather than silently pretending linear is perfect.
        if factor > 2 or factor < 0.5:
            lowered = ing["name"].lower()
            if any(k in lowered for k in ("yeast", "baking soda", "baking powder", "salt")):
                note = (
                    "Leavening/seasoning may need adjustment at large scale "
                    "changes; taste and check rise."
                )
        scaled.append(
            ScaledIngredient(name=ing["name"], amount=amount, unit=ing["unit"], note=note)
        )
    return scaled
