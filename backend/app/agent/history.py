"""Persist Ask turns into assistant_conversations for signed-in users.

Think of each conversation as a labeled shelf of index cards: one card per
question+answer. We don't feed old cards back into the LLM in v1 — history
is for the cook to reopen, not for the agent to "remember."
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AssistantConversation

MAX_TURNS = 40


def _title_from_question(question: str) -> str:
    q = " ".join(question.strip().split())
    if len(q) <= 80:
        return q
    return q[:77].rstrip() + "…"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_conversations(db: Session, user_id: int) -> list[AssistantConversation]:
    return list(
        db.scalars(
            select(AssistantConversation)
            .where(AssistantConversation.user_id == user_id)
            .order_by(AssistantConversation.updated_at.desc())
        )
    )


def get_owned(
    db: Session, user_id: int, conversation_id: int
) -> AssistantConversation | None:
    conv = db.get(AssistantConversation, conversation_id)
    if conv is None or conv.user_id != user_id:
        return None
    return conv


def append_turn(
    db: Session,
    user_id: int,
    question: str,
    agent_response: dict,
    conversation_id: int | None = None,
    turn_id: str | None = None,
    diagnose_slug: str | None = None,
    error: str | None = None,
) -> AssistantConversation:
    """Create or append a turn; returns the conversation row."""
    mode = str(agent_response.get("mode") or "ask")[:20]
    turn = {
        "id": turn_id or f"{int(_now().timestamp() * 1000)}",
        "question": question,
        "response": agent_response,
        "diagnose_slug": diagnose_slug,
        "error": error,
        "ts": _now().isoformat(),
    }

    if conversation_id is not None:
        conv = get_owned(db, user_id, conversation_id)
        if conv is None:
            # Unknown / not owned → start a fresh thread rather than 404 the ask.
            conv = None
    else:
        conv = None

    if conv is None:
        conv = AssistantConversation(
            user_id=user_id,
            mode=mode,
            title=_title_from_question(question),
            messages=[turn],
            updated_at=_now(),
        )
        db.add(conv)
    else:
        messages = list(conv.messages or [])
        messages.insert(0, turn)  # newest first, matching the UI
        if len(messages) > MAX_TURNS:
            messages = messages[:MAX_TURNS]
        conv.messages = messages
        conv.mode = mode
        conv.updated_at = _now()
        if not conv.title:
            conv.title = _title_from_question(question)
        # Flag JSONB mutation for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(conv, "messages")

    db.commit()
    db.refresh(conv)
    return conv


def replace_messages(
    db: Session,
    conv: AssistantConversation,
    messages: list,
) -> AssistantConversation:
    trimmed = messages[:MAX_TURNS]
    conv.messages = trimmed
    if trimmed:
        # Newest-first: title from the oldest turn (end of list) if missing.
        oldest = trimmed[-1] if isinstance(trimmed[-1], dict) else None
        newest = trimmed[0] if isinstance(trimmed[0], dict) else None
        if oldest and isinstance(oldest.get("question"), str) and not conv.title:
            conv.title = _title_from_question(oldest["question"])
        if newest and isinstance(newest.get("response"), dict):
            mode = newest["response"].get("mode")
            if isinstance(mode, str):
                conv.mode = mode[:20]
    conv.updated_at = _now()
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(conv, "messages")
    db.commit()
    db.refresh(conv)
    return conv
