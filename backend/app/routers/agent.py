"""The unified agent endpoint + Ask conversation history."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.history import (
    append_turn,
    get_owned,
    list_conversations,
    replace_messages,
)
from app.agent.orchestrator import handle_message
from app.core.auth import get_current_user, get_optional_user
from app.core.db import get_db
from app.kitchen.context import load_kitchen_snapshot
from app.models import AssistantConversation, User
from app.schemas.agent import (
    AgentAskRequest,
    ConversationMessagesUpdate,
    ConversationOut,
    ConversationSummary,
)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/ask")
def ask(
    body: AgentAskRequest,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    """Classify intent, dispatch to the right mode pipeline, return the result.

    Send a Bearer token to personalize from the user's kitchen profile;
    anonymous requests still work without it. When signed in, the turn is
    saved to Ask history (new thread or append to conversation_id).
    """
    snapshot = load_kitchen_snapshot(db, user)
    result = handle_message(
        db,
        body.message,
        kitchen_snapshot=snapshot,
        user_id=user.id if user else None,
    )

    if user is None:
        return result

    diagnose_slug = None
    if result.get("mode") == "diagnose":
        symptom = (result.get("result") or {}).get("symptom")
        if isinstance(symptom, dict) and isinstance(symptom.get("slug"), str):
            diagnose_slug = symptom["slug"]

    conv = append_turn(
        db,
        user_id=user.id,
        question=body.message,
        agent_response=result,
        conversation_id=body.conversation_id,
        diagnose_slug=diagnose_slug,
    )
    return {**result, "conversation_id": conv.id}


@router.get("/conversations", response_model=list[ConversationSummary])
def conversations_list(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssistantConversation]:
    return list_conversations(db, user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def conversations_get(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssistantConversation:
    conv = get_owned(db, user.id, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.put("/conversations/{conversation_id}", response_model=ConversationOut)
def conversations_sync(
    conversation_id: int,
    body: ConversationMessagesUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssistantConversation:
    """Overwrite turns (used after diagnose conclude updates a result)."""
    conv = get_owned(db, user.id, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return replace_messages(db, conv, body.messages)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def conversations_delete(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    conv = get_owned(db, user.id, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
