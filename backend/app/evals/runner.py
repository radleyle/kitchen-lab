"""Execute a scenario against the matching subsystem and return a result dict.

Runners are pure/deterministic: they call the same functions production uses,
never the LLM. That keeps CI free, fast, and flake-free.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import app.recipes.generator as recipe_gen
from app.diagnosis.evidence import apply_hard_evidence
from app.diagnosis.scoring import score_causes
from app.evals.scenarios import Scenario
from app.kitchen.personalize import (
    apply_oven_offset_to_text,
    dietary_conflicts,
)
from app.recipes.generator import _standardize_ingredients
from app.safety.allergens import detect_allergens
from app.substitution.engine import best_ingredient_match

# Same candidate set the seed uses (subset sufficient for match scenarios).
INGREDIENT_CANDIDATES = [
    ("egg", ["eggs", "whole egg", "large egg"]),
    ("egg white", ["egg whites"]),
    ("cornstarch", ["corn starch", "cornflour (UK)"]),
    ("all-purpose flour", ["ap flour", "plain flour"]),
    ("butter", ["unsalted butter"]),
    ("table salt", ["salt"]),
]


def run_scenario(scenario: Scenario) -> dict[str, Any]:
    dispatch = {
        "diagnosis_scoring": _run_diagnosis_scoring,
        "hard_evidence": _run_hard_evidence,
        "safety_floor": _run_safety_floor,
        "standardize_ingredients": _run_standardize,
        "ingredient_match": _run_ingredient_match,
        "oven_offset": _run_oven_offset,
        "dietary_conflicts": _run_dietary,
        "allergen_detect": _run_allergens,
    }
    fn = dispatch.get(scenario.subsystem)
    if fn is None:
        raise ValueError(f"Unknown subsystem: {scenario.subsystem}")
    return fn(scenario.input)


def _run_hard_evidence(inp: dict) -> dict:
    causes = [SimpleNamespace(**c) for c in inp["causes"]]
    notes: dict[int, str] = {}
    llm = {int(k): list(v) for k, v in inp["llm_verdicts"].items()}
    fixed = apply_hard_evidence(causes, inp["answers"], llm, notes)
    # JSON-friendly keys for the grader's dotted paths.
    return {"verdicts": {str(k): v for k, v in fixed.items()}, "notes": notes}


def _run_diagnosis_scoring(inp: dict) -> dict:
    priors: dict[int, float] = {int(k): float(v) for k, v in inp["priors"].items()}
    verdicts = {
        int(k): list(v) for k, v in inp.get("verdicts", {}).items()
    }
    names: dict[int, str] = {
        int(k): v for k, v in inp.get("cause_names", {}).items()
    }
    scores = score_causes(priors, verdicts)
    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    return {
        "ranked_causes": [
            {
                "cause": names.get(cid, str(cid)),
                "score": round(scores[cid], 3),
                "cause_id": cid,
            }
            for cid in ranked_ids
        ]
    }


def _run_safety_floor(inp: dict) -> dict:
    floor = float(inp["floor_c"])
    fake_rule = SimpleNamespace(
        min_internal_temp_c=floor, food=inp.get("rule_food", "food")
    )
    # Patch just for this call; restore afterward.
    original_find = recipe_gen.find_temp_rule
    original_resp = recipe_gen.rule_to_response
    recipe_gen.find_temp_rule = lambda db, q: fake_rule  # type: ignore[assignment]
    recipe_gen.rule_to_response = lambda r: {"food": r.food}  # type: ignore[assignment]
    try:
        steps = [dict(s) for s in inp["steps"]]
        enforcement = recipe_gen._enforce_safety_floor(None, inp["food_query"], steps)
    finally:
        recipe_gen.find_temp_rule = original_find  # type: ignore[assignment]
        recipe_gen.rule_to_response = original_resp  # type: ignore[assignment]
    return {
        "steps": steps,
        "safety_overrides": enforcement["overrides"],
        "safety": enforcement["safety"],
    }


def _run_standardize(inp: dict) -> dict:
    return {"ingredients": _standardize_ingredients(inp["ingredients"])}


def _run_ingredient_match(inp: dict) -> dict:
    return {
        "match": best_ingredient_match(inp["query"], INGREDIENT_CANDIDATES)
    }


def _run_oven_offset(inp: dict) -> dict:
    text, adj = apply_oven_offset_to_text(inp["text"], int(inp["offset_f"]))
    return {"text": text, "adjustments": adj}


def _run_dietary(inp: dict) -> dict:
    conflicts = dietary_conflicts(inp["ingredients"], inp["restrictions"])
    return {
        "conflicts": conflicts,
        "has_milk_conflict": any(
            c.get("kind") == "allergen" and c.get("name") == "milk"
            for c in conflicts
        ),
    }


def _run_allergens(inp: dict) -> dict:
    found = detect_allergens(inp["ingredients"])["allergens_detected"]
    return {
        "allergens_detected": found,
        "has_wheat": "wheat" in found,
        "has_milk": "milk" in found,
        "has_tree_nuts": "tree_nuts" in found,
    }
