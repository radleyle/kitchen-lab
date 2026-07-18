"""Optional live evals that call OpenAI. Not run in default CI.

Enable locally against a seeded stack:
    LIVE_EVALS=1 docker compose exec -e LIVE_EVALS=1 -e OPENAI_API_KEY \
      backend pytest -v -m live tests/test_live_evals.py

These catch prompt regressions the deterministic harness cannot
(e.g. the assessor wrongly marking 'I brined' as supporting 'no salt').
"""

import os

import pytest

from app.core.db import SessionLocal
from app.diagnosis.engine import conclude_diagnosis
from app.substitution.engine import suggest_substitutes

pytestmark = pytest.mark.live


def _live_enabled() -> bool:
    return os.getenv("LIVE_EVALS") == "1" and bool(os.getenv("OPENAI_API_KEY"))


require_live = pytest.mark.skipif(
    not _live_enabled(),
    reason="Set LIVE_EVALS=1 and OPENAI_API_KEY to run live evals",
)


@require_live
def test_live_diagnosis_brine_assessor():
    """The exact regression from Lesson 10: marinade must contradict 'no salt'."""
    with SessionLocal() as db:
        result = conclude_diagnosis(
            db,
            "meat-tough-dry",
            "Pan-fried chicken breast came out dry and chewy",
            [
                {
                    "question": "Did you use a thermometer?",
                    "answer": "Yes, pulled at 155F and rested",
                },
                {
                    "question": "How did you slice it?",
                    "answer": "Lengthwise along the grain into long strips",
                },
                {
                    "question": "Did you salt ahead?",
                    "answer": "Salty marinade for 4 hours",
                },
            ],
        )
    ranked = result["ranked_causes"]
    by_name = {r["cause"]: r for r in ranked}
    no_salt = by_name.get("No pre-salting or brining")
    assert no_salt is not None
    # Must not be treated as supported by a marinade answer.
    assert "supports" not in no_salt.get("evidence_verdicts", []), (
        f"Assessor wrongly supported 'no pre-salting' from a brine answer: "
        f"{no_salt}"
    )
    assert ranked[0]["cause"] == "Sliced with the grain instead of against it"


@require_live
def test_live_substitute_brownies_moisture():
    with SessionLocal() as db:
        result = suggest_substitutes(
            db,
            "out of eggs for my brownie recipe",
            "eggs",
        )
    assert result.get("found")
    assert result.get("function", {}).get("name") == "moisture"
    names = [o["substitute"] for o in result.get("options", [])]
    assert "applesauce" in names
