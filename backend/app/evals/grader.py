"""Grade a scenario result against declarative checks.

Each check is a small assertion with a human-readable failure message.
The runner collects failures instead of raising on the first one, so one
broken scenario reports every contract it violated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Check:
    """One expected property of a scenario result."""

    kind: str
    # Kind-specific fields (only some are used per kind):
    key: str | None = None
    value: Any = None
    cause: str | None = None
    max_score: float | None = None
    min_score: float | None = None
    approx: float | None = None
    abs_tol: float = 0.5
    contains: str | None = None
    path: str | None = None  # dotted path into the result dict


@dataclass
class GradeResult:
    scenario_id: str
    passed: bool
    failures: list[str] = field(default_factory=list)


def _dig(data: Any, path: str | None) -> Any:
    if path is None:
        return data
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
    return cur


def grade(scenario_id: str, result: dict, checks: list[Check]) -> GradeResult:
    failures: list[str] = []
    for check in checks:
        msg = _evaluate(result, check)
        if msg:
            failures.append(msg)
    return GradeResult(
        scenario_id=scenario_id, passed=not failures, failures=failures
    )


def _evaluate(result: dict, check: Check) -> str | None:
    kind = check.kind

    if kind == "equals":
        actual = _dig(result, check.path or check.key)
        # JSON-style numeric dict keys are stored as strings in some runners.
        if actual != check.value:
            return (
                f"equals {check.path or check.key}: "
                f"expected {check.value!r}, got {actual!r}"
            )
        return None

    if kind == "truthy":
        actual = _dig(result, check.path or check.key)
        if not actual:
            return f"truthy {check.path or check.key}: got {actual!r}"
        return None

    if kind == "contains_text":
        actual = _dig(result, check.path or check.key)
        text = str(actual or "")
        needle = check.contains or check.value
        if needle not in text:
            return f"contains_text {check.path or check.key}: missing {needle!r} in {text!r}"
        return None

    if kind == "top_cause_is":
        ranked = result.get("ranked_causes") or []
        if not ranked:
            return "top_cause_is: no ranked_causes"
        top = ranked[0].get("cause")
        if top != check.cause:
            return f"top_cause_is: expected {check.cause!r}, got {top!r}"
        return None

    if kind == "cause_not_top":
        ranked = result.get("ranked_causes") or []
        if ranked and ranked[0].get("cause") == check.cause:
            return f"cause_not_top: {check.cause!r} won unexpectedly"
        return None

    if kind == "cause_score_at_most":
        ranked = result.get("ranked_causes") or []
        for row in ranked:
            if row.get("cause") == check.cause:
                score = float(row.get("score", 1))
                if check.max_score is not None and score > check.max_score:
                    return (
                        f"cause_score_at_most {check.cause!r}: "
                        f"{score} > {check.max_score}"
                    )
                return None
        return f"cause_score_at_most: cause {check.cause!r} not in ranking"

    if kind == "cause_score_at_least":
        ranked = result.get("ranked_causes") or []
        for row in ranked:
            if row.get("cause") == check.cause:
                score = float(row.get("score", 0))
                if check.min_score is not None and score < check.min_score:
                    return (
                        f"cause_score_at_least {check.cause!r}: "
                        f"{score} < {check.min_score}"
                    )
                return None
        return f"cause_score_at_least: cause {check.cause!r} not in ranking"

    if kind == "grams_approx":
        items = result.get("ingredients") or []
        name = check.key
        for item in items:
            if item.get("ingredient") == name:
                grams = item.get("grams")
                if grams is None:
                    return f"grams_approx {name}: grams is None"
                if abs(grams - (check.approx or 0)) > check.abs_tol:
                    return (
                        f"grams_approx {name}: {grams} not within "
                        f"{check.abs_tol} of {check.approx}"
                    )
                return None
        return f"grams_approx: ingredient {name!r} missing"

    if kind == "list_contains":
        actual = _dig(result, check.path or check.key)
        if not isinstance(actual, list) or check.value not in actual:
            return f"list_contains {check.path or check.key}: missing {check.value!r}"
        return None

    if kind == "override_enforced":
        overrides = result.get("safety_overrides") or []
        if not overrides:
            return "override_enforced: no safety_overrides"
        o = overrides[0]
        if check.min_score is not None and o.get("enforced_c") != check.min_score:
            # reuse min_score field as enforced temp for this check kind
            return (
                f"override_enforced: enforced_c={o.get('enforced_c')}, "
                f"expected {check.min_score}"
            )
        if check.max_score is not None and o.get("proposed_c") != check.max_score:
            return (
                f"override_enforced: proposed_c={o.get('proposed_c')}, "
                f"expected {check.max_score}"
            )
        return None

    return f"unknown check kind: {kind!r}"
