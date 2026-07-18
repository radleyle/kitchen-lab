"""Mode dispatch: route a classified message to the right pipeline.

The HANDLERS table is the extension point. As dedicated engines are built
(diagnosis, substitution, recipe generation), they replace the fallback
entries here without changing anything else.

Every response includes "handler" naming what actually served the request,
so no mode pretends to be more capable than it currently is.
"""

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.agent.intent import classify
from app.diagnosis.engine import start_diagnosis
from app.llm.answer import answer_question
from app.recipes.generator import adapt_recipe, generate_recipe
from app.substitution.engine import suggest_substitutes


def handle_learn(db: Session, message: str, intent: dict) -> dict:
    result = answer_question(db, message)
    result["handler"] = "grounded_answer"
    return result


def handle_diagnose(db: Session, message: str, intent: dict) -> dict:
    # Round 1 of the structured flow: symptom match + prior-ranked causes
    # + follow-up questions. Round 2 happens via POST /diagnose/conclude.
    result = start_diagnosis(db, message)
    if not result.get("matched"):
        # Symptom not in the taxonomy yet -> honest grounded answer instead.
        result = answer_question(db, message)
        result["handler"] = "grounded_answer (no taxonomy match)"
        return result
    result["handler"] = "diagnosis_engine"
    return result


def handle_cook(db: Session, message: str, intent: dict) -> dict:
    result = generate_recipe(db, message)
    if not result.get("feasible"):
        # Not actually a recipe request -> honest grounded answer instead.
        result = answer_question(db, message)
        result["handler"] = "grounded_answer (not a recipe request)"
        return result
    result["handler"] = "recipe_generator"
    return result


def handle_adapt(db: Session, message: str, intent: dict) -> dict:
    # Adapt messages usually carry the pasted recipe in the message itself.
    result = adapt_recipe(db, message)
    if not result.get("feasible"):
        result = answer_question(db, message)
        result["handler"] = "grounded_answer (no recipe text found)"
        return result
    result["handler"] = "recipe_adapter"
    return result


def handle_substitute(db: Session, message: str, intent: dict) -> dict:
    ingredient = intent.get("ingredient_to_replace") or intent.get("food")
    if ingredient:
        result = suggest_substitutes(db, message, ingredient)
        if result.get("found"):
            result["handler"] = "substitution_engine"
            return result
    # Ingredient missing from the vetted database -> honest grounded answer.
    result = answer_question(db, message)
    result["handler"] = "grounded_answer (no vetted substitution data)"
    return result


def handle_fallback(db: Session, message: str, intent: dict) -> dict:
    # The experiment engine is not built yet;
    # a grounded, cited answer is the honest interim behavior.
    result = answer_question(db, message)
    result["handler"] = "grounded_answer (fallback; dedicated engine coming)"
    return result


HANDLERS: dict[str, Callable[[Session, str, dict], dict]] = {
    "learn": handle_learn,
    "diagnose": handle_diagnose,
    "cook": handle_cook,
    "adapt": handle_adapt,
    "substitute": handle_substitute,
    "experiment": handle_fallback,
}


def handle_message(db: Session, message: str) -> dict:
    intent = classify(message)
    handler = HANDLERS[intent["mode"]]
    result = handler(db, message, intent)
    return {
        "mode": intent["mode"],
        "entities": {
            "food": intent.get("food"),
            "technique": intent.get("technique"),
            "problem": intent.get("problem"),
            "ingredient_to_replace": intent.get("ingredient_to_replace"),
        },
        "classification_confidence": intent.get("confidence", "low"),
        "result": result,
    }
