"""The assistant endpoint: grounded, layered, cited answers."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.llm.answer import answer_question

router = APIRouter(prefix="/assistant", tags=["assistant"])


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)


@router.post("/ask")
def ask(body: AskRequest, db: Session = Depends(get_db)) -> dict:
    """Full pipeline: retrieve -> safety lookup -> LLM phrasing -> citations."""
    return answer_question(db, body.question)
