"""Generate and adapt science-annotated recipes.

Both flows share one shape and one post-processing pass:

  1. Retrieve evidence relevant to the dish/technique.
  2. LLM drafts the structured recipe. Its science annotations may use ONLY
     the evidence (cited by index); the skeleton is its culinary competence
     and is labeled as such.
  3. _enforce_safety_floor: deterministic. Look up the USDA rule for the
     food; any step doneness temperature below the floor is raised, with a
     visible note. The LLM cannot ship an unsafe temperature.
  4. Real citation objects are attached; the recipe is persisted.
"""

from sqlalchemy.orm import Session

from app.calculators.units import (
    DENSITY_G_PER_ML,
    GRAMS_PER,
    ML_PER,
    convert_mass,
    volume_to_grams,
)
from app.kitchen.personalize import kitchen_prompt_block, personalize_recipe
from app.llm.client import complete_json
from app.models import Recipe, RecipeStep
from app.rag.retrieval import search_passages
from app.safety.temps import find_temp_rule, rule_to_response

STEPS_SHAPE = """\
  "steps": [
    {"instruction": "what to do (the Action)",
     "why": "why this step works, ONLY from evidence, or empty string",
     "science": "the mechanism, ONLY from evidence, or empty string",
     "visual_cues": "what done looks/sounds/smells like, or empty string",
     "target_internal_temp_c": <number or null, only for doneness steps>,
     "citations_used": [evidence numbers backing why/science]}
  ]\
"""

RECIPE_SHAPE = f"""\
Respond with JSON exactly in this shape:
{{
  "feasible": true/false,
  "title": "recipe title",
  "description": "one or two sentences on the approach and why",
  "servings": <int>,
  "ingredients": [
    {{"ingredient": "name", "grams": <number or null>,
     "amount": "original measure if grams is null, e.g. '2 tbsp'",
     "note": "prep note or empty string"}}
  ],
{STEPS_SHAPE}
}}
"""

# Adapt mode: the LLM PARSES measures; it never converts them. Python does
# the arithmetic with the calculators (an early test showed the model
# applying per-cup gram figures to teaspoons).
ADAPT_SHAPE = f"""\
Respond with JSON exactly in this shape:
{{
  "feasible": true/false,
  "title": "recipe title",
  "description": "one or two sentences on the dish",
  "servings": <int or null if the recipe does not say>,
  "ingredients": [
    {{"ingredient": "name",
     "quantity": <number, or null if not a measurable quantity>,
     "unit": "one of: g, kg, oz, lb, ml, l, tsp, tbsp, cup, fl_oz, quart -- or null",
     "amount": "free-text measure when quantity/unit do not apply, e.g. '2 large' or 'a splash', else empty string",
     "density_key": "the DENSITY KEY matching this ingredient, or null if none matches",
     "note": "prep note or empty string"}}
  ],
{STEPS_SHAPE}
}}
"""

GENERATE_PROMPT = f"""\
You draft recipes for KitchenLab, an evidence-based cooking app. You will
get a recipe REQUEST and numbered EVIDENCE passages from a curated
food-science knowledge base.

Rules you must never break:
1. The "why" and "science" fields may contain ONLY information from the
   EVIDENCE passages, cited by number in "citations_used". If no passage
   supports an annotation, leave it as an empty string -- never invent a
   scientific explanation. Steps without annotations are fine.
2. Do not state safe minimum temperatures from memory. If a step cooks
   meat/poultry/fish/eggs to doneness, put your intended target in
   "target_internal_temp_c"; it will be checked against an authoritative
   safety table after you respond.
3. Prefer grams for ingredients (use whole sensible numbers); use "amount"
   only where grams are unnatural (e.g. "1 large egg", "1 bay leaf").
4. Steps must be in executable order, each doing one thing, with visual
   cues wherever a home cook could use them.
5. If the request is not actually a recipe request, set "feasible" to false.

{RECIPE_SHAPE}
"""

ADAPT_PROMPT_TEMPLATE = f"""\
You standardize and annotate a user's pasted recipe for KitchenLab, an
evidence-based cooking app. You will get the RECIPE TEXT, numbered EVIDENCE
passages, and a list of DENSITY KEYS.

Rules you must never break:
1. Keep the user's recipe faithfully: same dish, same ingredients, same
   method. You are standardizing and annotating, not rewriting. Fix only
   clear errors (impossible order, missing steps implied by the text).
2. PARSE each ingredient's measure into "quantity" and "unit". Do NOT
   convert units and do NOT compute grams -- that arithmetic happens in
   code after you respond. If the ingredient matches one of the DENSITY
   KEYS, put that exact key in "density_key".
3. The "why" and "science" fields may contain ONLY information from the
   EVIDENCE passages, cited by number in "citations_used". If no passage
   applies, leave them empty -- never invent an explanation.
4. Do not state safe minimum temperatures from memory. If a step cooks
   meat/poultry/fish/eggs to doneness, put the recipe's stated or implied
   target in "target_internal_temp_c"; it will be checked against an
   authoritative safety table after you respond.
5. If the text is not actually a recipe, set "feasible" to false.

{ADAPT_SHAPE}
"""


def _standardize_ingredients(items: list[dict]) -> list[dict]:
    """Deterministic unit conversion for parsed ingredients.

    The LLM only parsed (quantity, unit, density_key); every gram figure
    is computed here with the tested calculators. Anything unparseable
    keeps its original measure with grams=None.
    """
    out = []
    for item in items:
        qty = item.get("quantity")
        unit = item.get("unit")
        density_key = item.get("density_key")
        # Fallback if the LLM missed the key: "all-purpose flour" is
        # all_purpose_flour after normalization. Cheap and deterministic.
        if density_key not in DENSITY_G_PER_ML:
            normalized = (
                str(item.get("ingredient", "")).lower().replace("-", "_").replace(" ", "_")
            )
            density_key = normalized if normalized in DENSITY_G_PER_ML else None
        # LLMs return "cups" as often as "cup"; plural must not break math.
        if isinstance(unit, str):
            unit = unit.strip().lower()
            if unit not in GRAMS_PER and unit not in ML_PER and unit.endswith("s"):
                unit = unit[:-1]
        grams = None
        if isinstance(qty, (int, float)) and isinstance(unit, str):
            if unit in GRAMS_PER:
                grams = convert_mass(qty, unit, "g")
            elif unit in ML_PER and density_key in DENSITY_G_PER_ML:
                grams = volume_to_grams(qty, unit, density_key)
        amount = item.get("amount") or ""
        if not amount and qty is not None:
            amount = f"{qty:g} {unit}" if unit else f"{qty:g}"
        out.append(
            {
                "ingredient": item.get("ingredient", ""),
                "grams": round(grams, 1) if grams is not None else None,
                "amount": amount,
                "note": item.get("note", ""),
            }
        )
    return out


def _evidence_block(passages: list[dict]) -> str:
    lines = []
    for i, p in enumerate(passages, start=1):
        lines.append(
            f"[{i}] (confidence: {p['confidence']}; scope: {p['scope']})\n"
            f"Claim: {p['claim']}\n{p['content']}"
        )
    return "\n\n".join(lines)


def _attach_citations(steps: list[dict], passages: list[dict]) -> None:
    for step in steps:
        used = step.pop("citations_used", []) or []
        step["citations"] = [
            {
                "claim": passages[i - 1]["claim"],
                "confidence": passages[i - 1]["confidence"],
                "source": passages[i - 1]["source"],
            }
            for i in used
            if isinstance(i, int) and 1 <= i <= len(passages)
        ]


def _enforce_safety_floor(db: Session, food_query: str, steps: list[dict]) -> dict:
    """Deterministic last word on doneness temperatures.

    Any step target below the USDA floor for this food is raised to the
    floor, and the override is reported so nothing changes silently.
    """
    rule = find_temp_rule(db, food_query)
    if rule is None:
        return {"safety": None, "overrides": []}

    floor = rule.min_internal_temp_c
    overrides = []
    for i, step in enumerate(steps, start=1):
        target = step.get("target_internal_temp_c")
        if isinstance(target, (int, float)) and target < floor:
            step["target_internal_temp_c"] = floor
            step["instruction"] += (
                f" (Safety: cook to at least {floor:.0f}C / "
                f"{floor * 9 / 5 + 32:.0f}F internal.)"
            )
            overrides.append(
                {
                    "step": i,
                    "proposed_c": target,
                    "enforced_c": floor,
                    "rule": rule.food,
                }
            )
    return {"safety": rule_to_response(rule), "overrides": overrides}


def _persist(
    db: Session,
    data: dict,
    source_url: str | None = None,
    user_id: int | None = None,
) -> int:
    recipe = Recipe(
        user_id=user_id,
        title=data["title"],
        description=data.get("description"),
        servings=data.get("servings"),
        source_url=source_url,
        ingredients=data["ingredients"],
    )
    db.add(recipe)
    db.flush()
    for pos, step in enumerate(data["steps"], start=1):
        db.add(
            RecipeStep(
                recipe_id=recipe.id,
                position=pos,
                instruction=step["instruction"],
                why=step.get("why") or None,
                science=step.get("science") or None,
                critical_temp_c=step.get("target_internal_temp_c"),
                visual_cues=step.get("visual_cues") or None,
            )
        )
    db.commit()
    return recipe.id


def _finalize(
    db: Session,
    result: dict,
    passages: list[dict],
    safety_query: str,
    source_url: str | None = None,
    kitchen_snapshot: dict | None = None,
    user_id: int | None = None,
) -> dict:
    if not result.get("feasible", False):
        return {"feasible": False, "message": result.get("description", "")}

    steps = result.get("steps", [])
    _attach_citations(steps, passages)
    enforcement = _enforce_safety_floor(db, safety_query, steps)
    recipe_id = _persist(db, result, source_url, user_id=user_id)

    out = {
        "feasible": True,
        "recipe_id": recipe_id,
        "title": result["title"],
        "description": result.get("description", ""),
        "servings": result.get("servings"),
        "ingredients": result.get("ingredients", []),
        "steps": steps,
        "safety": enforcement["safety"],
        "safety_overrides": enforcement["overrides"],
        "grounding_note": (
            "Step-by-step science annotations are cited to the knowledge "
            "base. The recipe skeleton (amounts, order, times) is standard "
            "culinary practice and is not individually cited."
        ),
    }
    return personalize_recipe(out, kitchen_snapshot)


def generate_recipe(
    db: Session,
    request: str,
    servings: int | None = None,
    kitchen_snapshot: dict | None = None,
    user_id: int | None = None,
) -> dict:
    passages = search_passages(db, request, top_k=8)
    user_prompt = f"REQUEST: {request}\n"
    if servings:
        user_prompt += f"SERVINGS: {servings}\n"
    kitchen = kitchen_prompt_block(kitchen_snapshot)
    if kitchen:
        user_prompt += f"\n{kitchen}\n"
    user_prompt += f"\nEVIDENCE:\n{_evidence_block(passages)}"

    result = complete_json(GENERATE_PROMPT, user_prompt)
    # Safety lookup keys off request + title: "crispy thighs" alone would
    # miss the chicken rule if the user only said "thighs".
    safety_query = f"{request} {result.get('title', '')}"
    return _finalize(
        db, result, passages, safety_query,
        kitchen_snapshot=kitchen_snapshot, user_id=user_id,
    )


def adapt_recipe(
    db: Session,
    recipe_text: str,
    source_url: str | None = None,
    kitchen_snapshot: dict | None = None,
    user_id: int | None = None,
) -> dict:
    passages = search_passages(db, recipe_text[:1500], top_k=8)
    density_keys = ", ".join(sorted(DENSITY_G_PER_ML))
    kitchen = kitchen_prompt_block(kitchen_snapshot)
    user_prompt = (
        f"RECIPE TEXT:\n{recipe_text}\n\n"
        f"DENSITY KEYS: {density_keys}\n\n"
    )
    if kitchen:
        user_prompt += f"{kitchen}\n\n"
    user_prompt += f"EVIDENCE:\n{_evidence_block(passages)}"
    result = complete_json(ADAPT_PROMPT_TEMPLATE, user_prompt)
    if result.get("feasible"):
        result["ingredients"] = _standardize_ingredients(
            result.get("ingredients", [])
        )
    safety_query = f"{recipe_text[:300]} {result.get('title', '')}"
    return _finalize(
        db, result, passages, safety_query, source_url,
        kitchen_snapshot=kitchen_snapshot, user_id=user_id,
    )
