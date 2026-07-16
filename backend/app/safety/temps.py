"""Safe internal temperature lookup against the seeded USDA rules."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SafetyRule


def keyword_score(query: str, keywords: list[str]) -> int:
    """How many of the rule's keywords appear in the user's food description.

    Pure function (no database) so it's trivially unit-testable.
    """
    q = query.lower()
    return sum(1 for kw in keywords if kw in q)


def find_temp_rule(db: Session, food_query: str) -> SafetyRule | None:
    """Return the best-matching internal-temperature rule, or None.

    Multi-word keywords like "ground beef" naturally outscore single words,
    because "ground beef burger" matches both "ground beef" and "burger".
    """
    rules = db.scalars(
        select(SafetyRule).where(SafetyRule.rule_type == "internal_temp")
    ).all()

    best, best_score = None, 0
    for rule in rules:
        score = keyword_score(food_query, rule.details.get("keywords", []))
        if score > best_score:
            best, best_score = rule, score
    return best


def rule_to_response(rule: SafetyRule) -> dict:
    """Shape a rule (with its citation) for the API and, later, the LLM."""
    return {
        "food": rule.food,
        "min_internal_temp_c": rule.min_internal_temp_c,
        "min_internal_temp_f": rule.details.get("temp_f"),
        "rest_time_min": rule.rest_time_min,
        "source": {
            "title": rule.source.title,
            "url": rule.source.url,
            "authority_level": rule.source.authority_level,
            "reviewed_at": str(rule.source.reviewed_at),
        },
    }
