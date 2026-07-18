"""Function-aware substitution endpoint.

POST /substitute  {message, ingredient} -> vetted options for the job the
ingredient does in that dish, or grouped options + a clarifying question.

Optional Bearer token marks options that conflict with dietary restrictions.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_optional_user
from app.core.db import get_db
from app.kitchen.context import load_kitchen_snapshot
from app.models import User
from app.substitution.engine import suggest_substitutes

router = APIRouter(prefix="/substitute", tags=["substitute"])


class SubstituteRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    ingredient: str = Field(min_length=1, max_length=120)


@router.post("")
def substitute(
    body: SubstituteRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    snapshot = load_kitchen_snapshot(db, user)
    return suggest_substitutes(
        db, body.message, body.ingredient, kitchen_snapshot=snapshot
    )
