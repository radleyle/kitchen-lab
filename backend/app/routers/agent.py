"""The unified agent endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.orchestrator import handle_message
from app.core.auth import get_optional_user
from app.core.db import get_db
from app.kitchen.context import load_kitchen_snapshot
from app.models import User

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentRequest(BaseModel):
    message: str = Field(min_length=5, max_length=1000)


@router.post("/ask")
def ask(
    body: AgentRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    """Classify intent, dispatch to the right mode pipeline, return the result.

    Send a Bearer token to personalize from the user's kitchen profile;
    anonymous requests still work without it.
    """
    snapshot = load_kitchen_snapshot(db, user)
    return handle_message(
        db,
        body.message,
        kitchen_snapshot=snapshot,
        user_id=user.id if user else None,
    )
