"""Function-aware substitution endpoint.

POST /substitute  {message, ingredient} -> vetted options for the job the
ingredient does in that dish, or grouped options + a clarifying question.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.substitution.engine import suggest_substitutes

router = APIRouter(prefix="/substitute", tags=["substitute"])


class SubstituteRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    ingredient: str = Field(min_length=1, max_length=120)


@router.post("")
def substitute(body: SubstituteRequest, db: Session = Depends(get_db)) -> dict:
    return suggest_substitutes(db, body.message, body.ingredient)
