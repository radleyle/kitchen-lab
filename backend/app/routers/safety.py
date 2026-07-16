"""Safety endpoints: temperature lookup and allergen detection."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.safety.allergens import detect_allergens
from app.safety.temps import find_temp_rule, rule_to_response

router = APIRouter(prefix="/safety", tags=["safety"])


@router.get("/internal-temp")
def internal_temp(food: str, db: Session = Depends(get_db)) -> dict:
    """e.g. GET /safety/internal-temp?food=chicken thigh"""
    rule = find_temp_rule(db, food)
    if rule is None:
        raise HTTPException(
            status_code=404,
            detail=f"No temperature rule matched {food!r}. "
            "Rather than guess, we don't answer safety questions without a match.",
        )
    return rule_to_response(rule)


class AllergenRequest(BaseModel):
    ingredients: list[str]


@router.post("/allergens")
def allergens(body: AllergenRequest) -> dict:
    return detect_allergens(body.ingredients)
