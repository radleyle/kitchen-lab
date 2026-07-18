"""Substitution flow: resolve ingredient -> determine function -> join.

normalize() and best_ingredient_match() are pure and unit-tested; the LLM
call classifies the ingredient's function against the closed vocabulary
from the ingredient_functions table and can only answer from that list.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.kitchen.personalize import filter_substitutions_for_diet
from app.llm.client import complete_json
from app.models import Ingredient, IngredientFunction, Substitution

FUNCTION_PROMPT = """\
You classify which JOB an ingredient performs in a specific dish, for an
evidence-based cooking app. You will get the user's message, the
INGREDIENT being replaced, and a numbered list of FUNCTIONS.

Rules:
1. Choose the PRIMARY function the ingredient serves IN THE USER'S DISH.
   The same ingredient does different jobs in different dishes.
2. If the message names no dish or the job is genuinely ambiguous between
   two functions on the list, use 0 -- do not guess.
3. Common anchors (use when the dish matches and the function is on the
   list): egg in brownies/muffins/quick breads -> moisture; egg in
   cookies/meatballs/burgers -> binding; egg white in meringue/mousse ->
   aeration; cornstarch in gravy/sauce/pie filling -> thickening;
   butter in cakes/cookies (creaming or richness) -> tenderizing_fat;
   buttermilk in pancakes/biscuits -> acidity (or dairy_body if acidity
   is not listed).

Respond with JSON exactly in this shape:
{"function_number": <int, 0 if unclear>, "dish": "the dish mentioned, or null",
 "confidence": "high" | "medium" | "low"}
"""


def normalize(name: str) -> str:
    """Lowercase, trim, collapse simple plurals: 'Eggs ' -> 'egg'."""
    n = name.strip().lower()
    if n.endswith("es") and n[:-2] and not n.endswith("uses"):
        # tomatoes -> tomato, but leave 'molasses'-like words alone via length
        candidate = n[:-2]
        return candidate if n.endswith(("oes", "ches", "shes")) else n[:-1]
    if n.endswith("s") and not n.endswith("ss"):
        return n[:-1]
    return n


def best_ingredient_match(query: str, candidates: list[tuple[str, list[str]]]) -> str | None:
    """Match a user's ingredient phrase to a canonical name via aliases.

    candidates: [(canonical_name, [aliases])]. Exact normalized match on
    name or alias wins; then a containment check ("large egg" contains
    "egg") preferring the LONGEST candidate name so "egg white" beats
    "egg" for the query "egg whites".
    """
    q = normalize(query)
    for name, aliases in candidates:
        if q == normalize(name) or any(q == normalize(a) for a in aliases):
            return name

    containing = [
        name
        for name, aliases in candidates
        if normalize(name) in q or any(normalize(a) in q for a in aliases)
    ]
    if containing:
        return max(containing, key=len)
    return None


def _load_ingredient(db: Session, query: str) -> Ingredient | None:
    rows = db.scalars(select(Ingredient)).all()
    match = best_ingredient_match(query, [(r.name, r.aliases or []) for r in rows])
    if match is None:
        return None
    return next(r for r in rows if r.name == match)


def _sub_to_dict(sub: Substitution) -> dict:
    return {
        "substitute": sub.substitute.name,
        "ratio": sub.ratio,
        "texture_notes": sub.texture_notes,
        "procedure_adjustments": sub.procedure_adjustments,
        "confidence": sub.confidence,
        "source": (
            {"title": sub.source.title, "url": sub.source.url}
            if sub.source_id and sub.source
            else None
        ),
    }


def suggest_substitutes(
    db: Session,
    message: str,
    ingredient_query: str,
    kitchen_snapshot: dict | None = None,
) -> dict:
    """The full flow. Returns options for one function, or grouped options
    plus a clarifying question when the function can't be determined."""
    ingredient = _load_ingredient(db, ingredient_query)
    if ingredient is None:
        return {
            "found": False,
            "message": (
                f"'{ingredient_query}' is not in the substitution database "
                "yet, so no vetted swap can be offered."
            ),
        }

    subs = list(
        db.scalars(
            select(Substitution)
            .where(Substitution.original_id == ingredient.id)
            .options(
                joinedload(Substitution.substitute),
                joinedload(Substitution.function),
                joinedload(Substitution.source),
            )
        ).unique()
    )
    if not subs:
        return {
            "found": False,
            "message": (
                f"No vetted substitutions recorded for {ingredient.name} yet."
            ),
        }

    # Only functions this ingredient actually has substitutions for.
    functions = sorted(
        {s.function for s in subs}, key=lambda f: f.name
    )
    listing = "\n".join(
        f"[{i}] {f.name}: {f.description}" for i, f in enumerate(functions, start=1)
    )
    result = complete_json(
        FUNCTION_PROMPT,
        f"MESSAGE: {message}\nINGREDIENT: {ingredient.name}\n\nFUNCTIONS:\n{listing}",
    )

    n = result.get("function_number", 0)
    chosen: IngredientFunction | None = None
    if isinstance(n, int) and 1 <= n <= len(functions):
        chosen = functions[n - 1]

    diet = None
    if kitchen_snapshot and kitchen_snapshot.get("profile"):
        diet = kitchen_snapshot["profile"].get("dietary_restrictions")

    if chosen is None:
        # Honest uncertainty: group by job and ask, never guess.
        by_fn = {
            f.name: filter_substitutions_for_diet(
                [_sub_to_dict(s) for s in subs if s.function_id == f.id], diet
            )
            for f in functions
        }
        return {
            "found": True,
            "ingredient": ingredient.name,
            "function": None,
            "dish": result.get("dish"),
            "needs_clarification": True,
            "question": (
                f"What is the {ingredient.name} doing in your dish? "
                "The right swap depends on its job."
            ),
            "options_by_function": by_fn,
        }

    options = [s for s in subs if s.function_id == chosen.id]
    options.sort(key=lambda s: {"high": 0, "medium": 1, "low": 2}[s.confidence])
    return {
        "found": True,
        "ingredient": ingredient.name,
        "function": {"name": chosen.name, "description": chosen.description},
        "dish": result.get("dish"),
        "needs_clarification": False,
        "options": filter_substitutions_for_diet(
            [_sub_to_dict(s) for s in options], diet
        ),
    }
