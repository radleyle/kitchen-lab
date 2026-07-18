"""Seed ingredients, ingredient functions, and function-aware substitutions.

Run inside the container:
    docker compose exec backend python -m app.seeds.food_seed

Additively idempotent: existing functions/ingredients/substitution triples
are skipped.

Every substitution answers: "X replaces Y when Y is doing THIS job."
ratio = amount of substitute per 1 unit of original (by the unit named in
the notes; for eggs the 'unit' is one egg and the recipe is spelled out).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import Ingredient, IngredientFunction, KnowledgeSource, Substitution

FUNCTIONS = {
    "thickening": "Gives body and viscosity to liquids (sauces, pie fillings).",
    "binding": "Holds a mixture together so it doesn't crumble or fall apart.",
    "moisture": "Contributes water content for a soft, tender result.",
    "aeration": "Traps air or foam that gives lift and light texture.",
    "leavening": "Produces or enables gas that makes baked goods rise.",
    "tenderizing_fat": "Coats flour proteins to limit gluten; richness and tenderness.",
    "acidity": "Lowers pH: brightness, tang, and activating baking soda.",
    "dairy_body": "Provides dairy richness, body, and tang in batters and sauces.",
}

# name, category, aliases
INGREDIENTS = [
    ("egg", "protein", ["eggs", "whole egg", "large egg"]),
    ("egg white", "protein", ["egg whites"]),
    ("ground flaxseed", "seed", ["flax meal", "flaxseed meal", "ground flax"]),
    ("applesauce", "fruit", ["apple sauce", "unsweetened applesauce"]),
    ("aquafaba", "legume", ["chickpea brine", "chickpea liquid"]),
    ("mashed banana", "fruit", ["banana"]),
    ("cornstarch", "starch", ["corn starch", "cornflour (UK)"]),
    ("all-purpose flour", "starch", ["ap flour", "plain flour", "all purpose flour"]),
    ("arrowroot", "starch", ["arrowroot powder", "arrowroot starch"]),
    ("potato starch", "starch", []),
    ("butter", "fat", ["unsalted butter"]),
    ("vegetable oil", "fat", ["canola oil", "neutral oil"]),
    ("coconut oil", "fat", []),
    ("buttermilk", "dairy", []),
    ("milk", "dairy", ["whole milk"]),
    ("plain yogurt", "dairy", ["yogurt", "greek yogurt"]),
    ("sour cream", "dairy", []),
    ("baking powder", "leavener", []),
    ("baking soda", "leavener", ["bicarbonate of soda", "sodium bicarbonate"]),
    ("cream of tartar", "leavener", ["potassium bitartrate"]),
    ("lemon juice", "acid", ["fresh lemon juice"]),
]

# original, substitute, function, ratio, texture_notes, procedure_adjustments,
# confidence, source_title_contains (matched against knowledge_sources, or None)
SUBSTITUTIONS = [
    ("egg", "ground flaxseed", "binding", 1.0,
     "Chewier and slightly denser; visible specks. Best in cookies, "
     "pancakes, and quick breads; not for custards.",
     "Per egg: mix 1 tbsp (7 g) ground flaxseed with 3 tbsp (45 ml) water "
     "and rest 5-10 minutes until gelled before adding.",
     "medium", "King Arthur"),
    ("egg", "applesauce", "moisture", 1.0,
     "Denser, more tender crumb with mild sweetness. Fine in brownies and "
     "muffins where eggs mainly add moisture; weak as a binder.",
     "Per egg: use 60 g (1/4 cup) unsweetened applesauce. Consider adding "
     "1/4 tsp extra baking powder to offset the density.",
     "medium", "King Arthur"),
    ("egg", "mashed banana", "moisture", 1.0,
     "Adds clear banana flavor and density; good in pancakes and muffins "
     "that suit the flavor.",
     "Per egg: use 60 g (1/4 cup) well-mashed ripe banana.",
     "low", None),
    ("egg white", "aquafaba", "aeration", 1.0,
     "Whips to foam like egg whites but less stable; softer peaks and "
     "quicker to deflate. Works for meringues and mousses.",
     "Per egg white: use 3 tbsp (45 ml) aquafaba. Whip longer than whites; "
     "a pinch of cream of tartar helps stability.",
     "medium", None),
    ("cornstarch", "all-purpose flour", "thickening", 2.0,
     "Slightly cloudy, more opaque sauce versus cornstarch's gloss.",
     "Use 2x the amount. Cook several minutes after thickening to lose the "
     "raw flour taste; mix into a slurry or roux first.",
     "high", "King Arthur"),
    ("cornstarch", "arrowroot", "thickening", 1.0,
     "Clearer, glossier than cornstarch; turns slimy with dairy and "
     "breaks down on reheating.",
     "Swap 1:1. Add near the end of cooking; avoid prolonged boiling and "
     "dairy-based sauces.",
     "medium", None),
    ("cornstarch", "potato starch", "thickening", 1.0,
     "Similar gloss; thickens at a lower temperature.",
     "Swap 1:1 but add late and avoid long boiling -- it thins if "
     "overheated.",
     "medium", None),
    ("butter", "vegetable oil", "tenderizing_fat", 0.8,
     "Moister but denser: no solid fat means no creaming aeration, and no "
     "butter flavor. Fine in muffins/quick breads; poor in creamed cakes.",
     "Use 0.8x by weight. If the recipe creams butter with sugar, expect "
     "less rise; compensate with the recipe's chemical leavener, not more oil.",
     "medium", "Food Lab"),
    ("butter", "coconut oil", "tenderizing_fat", 1.0,
     "Solid at room temperature so creaming still works; adds coconut "
     "flavor unless refined.",
     "Swap 1:1 by weight, matched temperature (soft-solid for creaming, "
     "melted for melted).",
     "medium", None),
    ("buttermilk", "milk", "acidity", 1.0,
     "Slightly thinner than true buttermilk; tang is close.",
     "Per cup: stir 1 tbsp (15 ml) lemon juice or white vinegar into 1 cup "
     "(240 ml) milk and rest 5-10 minutes until it curdles slightly.",
     "high", "King Arthur"),
    ("buttermilk", "plain yogurt", "dairy_body", 1.0,
     "Thicker and richer; excellent in pancakes and marinades.",
     "Thin yogurt with milk (about 3 parts yogurt to 1 part milk) to "
     "buttermilk consistency.",
     "high", None),
    ("sour cream", "plain yogurt", "dairy_body", 1.0,
     "Slightly tangier and lighter; whole-milk Greek yogurt is closest.",
     "Swap 1:1. For hot sauces, temper it in off the heat to avoid "
     "curdling -- yogurt breaks more easily than sour cream.",
     "high", None),
    ("baking powder", "baking soda", "leavening", 0.25,
     "Same lift when paired with an acid; without acid you get soapy "
     "flavor and poor rise.",
     "Per tsp baking powder: use 1/4 tsp baking soda plus 1/2 tsp cream "
     "of tartar (or another acid in the recipe).",
     "high", "King Arthur"),
]


def _find_source(db: Session, title_contains: str | None) -> int | None:
    if not title_contains:
        return None
    src = db.scalar(
        select(KnowledgeSource).where(
            KnowledgeSource.title.ilike(f"%{title_contains}%")
        )
    )
    return src.id if src else None


def run(db: Session) -> str:
    functions: dict[str, IngredientFunction] = {}
    for name, description in FUNCTIONS.items():
        fn = db.scalar(
            select(IngredientFunction).where(IngredientFunction.name == name)
        )
        if fn is None:
            fn = IngredientFunction(name=name, description=description)
            db.add(fn)
            db.flush()
        functions[name] = fn

    ingredients: dict[str, Ingredient] = {}
    for name, category, aliases in INGREDIENTS:
        ing = db.scalar(select(Ingredient).where(Ingredient.name == name))
        if ing is None:
            ing = Ingredient(name=name, category=category, aliases=aliases)
            db.add(ing)
            db.flush()
        ingredients[name] = ing

    added = 0
    for orig, sub, fn_name, ratio, texture, procedure, conf, src_hint in SUBSTITUTIONS:
        original = ingredients[orig]
        substitute = ingredients[sub]
        fn = functions[fn_name]
        exists = db.scalar(
            select(Substitution).where(
                Substitution.original_id == original.id,
                Substitution.substitute_id == substitute.id,
                Substitution.function_id == fn.id,
            )
        )
        if exists is not None:
            continue
        db.add(
            Substitution(
                original_id=original.id,
                substitute_id=substitute.id,
                function_id=fn.id,
                ratio=ratio,
                texture_notes=texture,
                procedure_adjustments=procedure,
                confidence=conf,
                source_id=_find_source(db, src_hint),
            )
        )
        added += 1
    db.commit()
    return (
        f"Functions: {len(functions)}, ingredients: {len(ingredients)}, "
        f"new substitutions: {added} ({len(SUBSTITUTIONS)} in seed file)."
    )


if __name__ == "__main__":
    with SessionLocal() as session:
        print(run(session))
