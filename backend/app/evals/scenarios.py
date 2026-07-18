"""Declarative eval scenarios -- the regression catalog.

Each scenario is a trust contract written in plain data:
  subsystem + input -> checks that must pass.

IDs are stable; keep them when editing so CI blame stays readable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.evals.grader import Check


@dataclass
class Scenario:
    id: str
    title: str
    subsystem: str
    input: dict
    checks: list[Check] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


# Cause IDs are local to each diagnosis scenario (not DB ids).
# meat-tough-dry style priors from symptoms_seed.
MEAT_CAUSES = {
    1: "Overcooked past target temperature",
    2: "Sliced with the grain instead of against it",
    3: "Cut unsuited to the cooking method",
    4: "No pre-salting or brining",
}
MEAT_PRIORS = {1: 0.5, 2: 0.2, 3: 0.2, 4: 0.1}


SCENARIOS: list[Scenario] = [
    # ----- Diagnosis: the brine regression that bit us in Lesson 10 -----
    Scenario(
        id="diag-brine-must-not-boost-no-salt",
        title=(
            "User brined + sliced with the grain: slicing wins; "
            "'no pre-salting' must lose"
        ),
        subsystem="diagnosis_scoring",
        tags=["diagnosis", "regression"],
        input={
            "priors": MEAT_PRIORS,
            "cause_names": MEAT_CAUSES,
            # Correct verdicts for: thermometer@155F, sliced along grain, salty marinade
            "verdicts": {
                1: ["contradicts", "neutral", "contradicts"],  # overcooked
                2: ["neutral", "supports", "neutral"],  # with the grain
                3: ["neutral", "neutral", "neutral"],
                4: ["neutral", "neutral", "contradicts"],  # DID brine -> contradicts "no salt"
            },
        },
        checks=[
            Check(kind="top_cause_is", cause=MEAT_CAUSES[2]),
            Check(kind="cause_not_top", cause=MEAT_CAUSES[4]),
            Check(
                kind="cause_score_at_most",
                cause=MEAT_CAUSES[4],
                max_score=0.15,
            ),
            Check(
                kind="cause_score_at_most",
                cause=MEAT_CAUSES[1],
                max_score=0.15,
            ),
        ],
    ),
    Scenario(
        id="diag-overcook-wins-without-thermometer",
        title="No thermometer + long cook: overcooking stays most likely",
        subsystem="diagnosis_scoring",
        tags=["diagnosis"],
        input={
            "priors": MEAT_PRIORS,
            "cause_names": MEAT_CAUSES,
            "verdicts": {
                1: ["supports"],  # no thermometer, cooked a long time
                2: ["neutral"],
                3: ["neutral"],
                4: ["neutral"],
            },
        },
        checks=[
            Check(kind="top_cause_is", cause=MEAT_CAUSES[1]),
        ],
    ),
    Scenario(
        id="diag-hard-rule-overrides-llm-brine-support",
        title="Hard rule: marinade cannot support 'no pre-salting' even if LLM says so",
        subsystem="hard_evidence",
        tags=["diagnosis", "regression"],
        input={
            "causes": [
                {"id": 4, "cause": "No pre-salting or brining"},
                {"id": 2, "cause": "Sliced with the grain instead of against it"},
            ],
            "answers": [
                {"question": "Salt?", "answer": "Salty marinade for 4 hours"},
                {"question": "Slice?", "answer": "Lengthwise along the grain"},
            ],
            # Deliberately wrong LLM output -- the bug the live eval caught.
            "llm_verdicts": {4: ["supports"], 2: ["neutral"]},
        },
        checks=[
            Check(kind="equals", path="verdicts.4", value=["contradicts"]),
            Check(kind="equals", path="verdicts.2", value=["supports"]),
        ],
    ),
    # ----- Safety floor (Lesson 11) -----
    Scenario(
        id="safety-chicken-floor-raises-63c",
        title="Poultry target below USDA floor is raised and reported",
        subsystem="safety_floor",
        tags=["safety", "recipes", "regression"],
        input={
            "food_query": "chicken breast",
            "floor_c": 73.9,
            "rule_food": "All poultry (whole, parts, ground)",
            "steps": [
                {"instruction": "sear", "target_internal_temp_c": None},
                {"instruction": "cook until done", "target_internal_temp_c": 63},
            ],
        },
        checks=[
            Check(kind="override_enforced", max_score=63, min_score=73.9),
            Check(
                kind="contains_text",
                path="steps.1.instruction",
                contains="74C",
            ),
            Check(kind="equals", path="steps.0.target_internal_temp_c", value=None),
        ],
    ),
    Scenario(
        id="safety-compliant-pork-untouched",
        title="Target already at/above floor is left alone",
        subsystem="safety_floor",
        tags=["safety", "recipes"],
        input={
            "food_query": "pork loin",
            "floor_c": 62.8,
            "rule_food": "Pork (whole cuts)",
            "steps": [
                {"instruction": "roast", "target_internal_temp_c": 63},
            ],
        },
        checks=[
            Check(kind="equals", path="safety_overrides", value=[]),
            Check(kind="equals", path="steps.0.target_internal_temp_c", value=63),
        ],
    ),
    # ----- Adapt standardization (Lesson 11 LLM arithmetic bug) -----
    Scenario(
        id="adapt-tsp-salt-not-cup",
        title="1 tsp table salt converts to ~6g, never ~200g",
        subsystem="standardize_ingredients",
        tags=["recipes", "regression"],
        input={
            "ingredients": [
                {
                    "ingredient": "table salt",
                    "quantity": 1,
                    "unit": "tsp",
                    "density_key": "table_salt",
                    "amount": "1 tsp",
                    "note": "",
                },
                {
                    "ingredient": "all-purpose flour",
                    "quantity": 3,
                    "unit": "cups",
                    "density_key": None,
                    "amount": "3 cups",
                    "note": "",
                },
            ]
        },
        checks=[
            Check(kind="grams_approx", key="table salt", approx=6.0, abs_tol=0.2),
            Check(
                kind="grams_approx", key="all-purpose flour", approx=362, abs_tol=2
            ),
        ],
    ),
    # ----- Substitution matching -----
    Scenario(
        id="sub-egg-whites-not-egg",
        title="'egg whites' resolves to egg white, not egg",
        subsystem="ingredient_match",
        tags=["substitution", "regression"],
        input={"query": "egg whites"},
        checks=[Check(kind="equals", key="match", value="egg white")],
    ),
    Scenario(
        id="sub-cornflour-alias",
        title="UK cornflour alias maps to cornstarch",
        subsystem="ingredient_match",
        tags=["substitution"],
        input={"query": "cornflour (UK)"},
        checks=[Check(kind="equals", key="match", value="cornstarch")],
    ),
    # ----- Kitchen personalization -----
    Scenario(
        id="kitchen-oven-cold-dial",
        title="Oven runs 15F cold: dial 350 -> 365",
        subsystem="oven_offset",
        tags=["kitchen"],
        input={"text": "Bake at 350F until golden", "offset_f": -15},
        checks=[
            Check(kind="contains_text", key="text", contains="365F"),
            Check(kind="equals", path="adjustments.0.desired_f", value=350.0),
            Check(kind="equals", path="adjustments.0.dial_f", value=365.0),
        ],
    ),
    Scenario(
        id="kitchen-milk-allergy-flags-butter",
        title="Milk allergen profile flags butter in a recipe",
        subsystem="dietary_conflicts",
        tags=["kitchen", "safety"],
        input={
            "ingredients": ["butter", "flour", "sugar"],
            "restrictions": {"allergens": ["milk"]},
        },
        checks=[
            Check(kind="truthy", key="has_milk_conflict"),
        ],
    ),
    # ----- Allergen false friends -----
    Scenario(
        id="allergen-buckwheat-not-wheat",
        title="Buckwheat flour must not flag wheat",
        subsystem="allergen_detect",
        tags=["safety", "regression"],
        input={"ingredients": ["buckwheat flour", "sugar"]},
        checks=[
            Check(kind="equals", path="has_wheat", value=False),
        ],
    ),
    Scenario(
        id="allergen-almond-milk-is-tree-nut",
        title="Almond milk is tree nut, not dairy milk",
        subsystem="allergen_detect",
        tags=["safety"],
        input={"ingredients": ["almond milk"]},
        checks=[
            Check(kind="equals", path="has_milk", value=False),
            Check(kind="equals", path="has_tree_nuts", value=True),
        ],
    ),
]


def scenarios_by_id() -> dict[str, Scenario]:
    return {s.id: s for s in SCENARIOS}
