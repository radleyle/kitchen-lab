"""Mode dispatch: route a classified message to the right pipeline.

The HANDLERS table is the extension point. As dedicated engines are built
(diagnosis, substitution, recipe generation), they replace the fallback
entries here without changing anything else.

Every response includes "handler" naming what actually served the request,
so no mode pretends to be more capable than it currently is.

When a kitchen_snapshot is provided (logged-in user with a profile), every
handler that can personalize receives it -- oven offsets, equipment, and
dietary facts are applied in deterministic code, not invented by the LLM.
"""

from collections.abc import Callable

from sqlalchemy.orm import Session

from sqlalchemy import or_, select

from app.agent.intent import classify
from app.diagnosis.engine import start_diagnosis
from app.lab.experiments import design_experiment
from app.llm.answer import answer_question
from app.models import Experiment, ExperimentTrial, Technique
from app.recipes.generator import adapt_recipe, generate_recipe
from app.substitution.engine import suggest_substitutes

# handler(db, message, intent, kitchen_snapshot, user_id) -> dict
Handler = Callable[[Session, str, dict, dict | None, int | None], dict]


def _lookup_technique(db: Session, name: str | None) -> dict | None:
    if not name:
        return None
    q = name.strip().lower().replace(" ", "-")
    technique = db.scalar(
        select(Technique).where(
            or_(Technique.slug == q, Technique.name.ilike(name.strip()))
        )
    )
    if technique is None:
        return None
    return {
        "slug": technique.slug,
        "name": technique.name,
        "summary": technique.summary,
        "procedure": technique.procedure,
        "common_mistakes": technique.common_mistakes,
    }


def handle_learn(
    db: Session,
    message: str,
    intent: dict,
    kitchen_snapshot: dict | None,
    user_id: int | None,
) -> dict:
    result = answer_question(db, message, kitchen_snapshot=kitchen_snapshot)
    technique = _lookup_technique(db, intent.get("technique"))
    if technique:
        result["technique"] = technique
        result["handler"] = "grounded_answer+technique_library"
    else:
        result["handler"] = "grounded_answer"
    return result


def handle_diagnose(
    db: Session,
    message: str,
    intent: dict,
    kitchen_snapshot: dict | None,
    user_id: int | None,
) -> dict:
    result = start_diagnosis(db, message)
    if not result.get("matched"):
        result = answer_question(db, message, kitchen_snapshot=kitchen_snapshot)
        result["handler"] = "grounded_answer (no taxonomy match)"
        return result
    result["handler"] = "diagnosis_engine"
    return result


def handle_cook(
    db: Session,
    message: str,
    intent: dict,
    kitchen_snapshot: dict | None,
    user_id: int | None,
) -> dict:
    result = generate_recipe(
        db, message, kitchen_snapshot=kitchen_snapshot, user_id=user_id
    )
    if not result.get("feasible"):
        result = answer_question(db, message, kitchen_snapshot=kitchen_snapshot)
        result["handler"] = "grounded_answer (not a recipe request)"
        return result
    result["handler"] = "recipe_generator"
    return result


def handle_adapt(
    db: Session,
    message: str,
    intent: dict,
    kitchen_snapshot: dict | None,
    user_id: int | None,
) -> dict:
    result = adapt_recipe(
        db, message, kitchen_snapshot=kitchen_snapshot, user_id=user_id
    )
    if not result.get("feasible"):
        result = answer_question(db, message, kitchen_snapshot=kitchen_snapshot)
        result["handler"] = "grounded_answer (no recipe text found)"
        return result
    result["handler"] = "recipe_adapter"
    return result


def handle_substitute(
    db: Session,
    message: str,
    intent: dict,
    kitchen_snapshot: dict | None,
    user_id: int | None,
) -> dict:
    ingredient = intent.get("ingredient_to_replace") or intent.get("food")
    if ingredient:
        result = suggest_substitutes(
            db, message, ingredient, kitchen_snapshot=kitchen_snapshot
        )
        if result.get("found"):
            result["handler"] = "substitution_engine"
            return result
    result = answer_question(db, message, kitchen_snapshot=kitchen_snapshot)
    result["handler"] = "grounded_answer (no vetted substitution data)"
    return result


def handle_experiment(
    db: Session,
    message: str,
    intent: dict,
    kitchen_snapshot: dict | None,
    user_id: int | None,
) -> dict:
    draft = design_experiment(message)
    if not draft.get("feasible"):
        result = answer_question(db, message, kitchen_snapshot=kitchen_snapshot)
        result["handler"] = "grounded_answer (not an experiment request)"
        return result

    draft["handler"] = "experiment_designer"
    draft["persisted"] = False
    if user_id is None:
        draft["note"] = (
            "Log in and POST /experiments/design with persist=true "
            "(or use this draft with POST /experiments) to save it."
        )
        return draft

    experiment = Experiment(
        user_id=user_id,
        question=draft["question"],
        hypothesis=draft.get("hypothesis"),
        independent_variable=draft["independent_variable"],
        constants=draft.get("constants") or [],
        status="planned",
    )
    db.add(experiment)
    db.flush()
    for trial in draft["trials"]:
        db.add(
            ExperimentTrial(
                experiment_id=experiment.id,
                label=trial.get("label", "trial"),
                variable_value=trial.get("variable_value", ""),
            )
        )
    db.commit()
    draft["persisted"] = True
    draft["experiment_id"] = experiment.id
    return draft


HANDLERS: dict[str, Handler] = {
    "learn": handle_learn,
    "diagnose": handle_diagnose,
    "cook": handle_cook,
    "adapt": handle_adapt,
    "substitute": handle_substitute,
    "experiment": handle_experiment,
}


def handle_message(
    db: Session,
    message: str,
    kitchen_snapshot: dict | None = None,
    user_id: int | None = None,
) -> dict:
    intent = classify(message)
    handler = HANDLERS[intent["mode"]]
    result = handler(db, message, intent, kitchen_snapshot, user_id)
    return {
        "mode": intent["mode"],
        "entities": {
            "food": intent.get("food"),
            "technique": intent.get("technique"),
            "problem": intent.get("problem"),
            "ingredient_to_replace": intent.get("ingredient_to_replace"),
        },
        "classification_confidence": intent.get("confidence", "low"),
        "personalized": kitchen_snapshot is not None,
        "result": result,
    }
