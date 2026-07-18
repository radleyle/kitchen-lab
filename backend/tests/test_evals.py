"""Eval harness: every scenario is a pytest case.

Run just these:
    pytest -v tests/test_evals.py

Or the full suite (CI does this):
    pytest -v
"""

import pytest

from app.evals.grader import grade
from app.evals.runner import run_scenario
from app.evals.scenarios import SCENARIOS


@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s.id for s in SCENARIOS],
)
def test_eval_scenario(scenario):
    result = run_scenario(scenario)
    report = grade(scenario.id, result, scenario.checks)
    assert report.passed, (
        f"{scenario.id} FAILED -- {scenario.title}\n"
        + "\n".join(f"  - {f}" for f in report.failures)
    )
