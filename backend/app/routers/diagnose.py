"""Diagnose-my-dish: two-round structured troubleshooting.

POST /diagnose/start     description -> symptom match, prior-ranked causes,
                         targeted follow-up questions
POST /diagnose/conclude  answers -> evidence-adjusted ranking, confidence
                         category, cited fix

Stateless by design: the client carries the symptom slug and answers between
the two calls, so no server-side session is needed.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.diagnosis.engine import conclude_diagnosis, start_diagnosis

router = APIRouter(prefix="/diagnose", tags=["diagnose"])


class StartRequest(BaseModel):
    description: str = Field(min_length=5, max_length=2000)


class AnswerItem(BaseModel):
    question: str
    answer: str = Field(max_length=1000)


class ConcludeRequest(BaseModel):
    symptom_slug: str
    description: str = Field(min_length=5, max_length=2000)
    answers: list[AnswerItem] = Field(default_factory=list, max_length=10)


@router.post("/start")
def start(body: StartRequest, db: Session = Depends(get_db)) -> dict:
    return start_diagnosis(db, body.description)


@router.post("/conclude")
def conclude(body: ConcludeRequest, db: Session = Depends(get_db)) -> dict:
    return conclude_diagnosis(
        db,
        body.symptom_slug,
        body.description,
        [a.model_dump() for a in body.answers],
    )
