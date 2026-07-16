"""The unified agent endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.orchestrator import handle_message
from app.core.db import get_db

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    message: str = Field(min_length=5, max_length=1000)


@router.post("/ask")
def ask(body: AgentRequest, db: Session = Depends(get_db)) -> dict:
    """Classify intent, dispatch to the right mode pipeline, return the result."""
    return handle_message(db, body.message)
