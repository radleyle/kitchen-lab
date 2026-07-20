"""Pydantic shapes for the agent Ask API and conversation history."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentAskRequest(BaseModel):
    message: str = Field(min_length=5, max_length=1000)
    # When signed in, pass an existing thread id to append; omit to start new.
    conversation_id: int | None = None


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    mode: str
    created_at: datetime
    updated_at: datetime


class ConversationOut(ConversationSummary):
    messages: list = Field(default_factory=list)


class ConversationMessagesUpdate(BaseModel):
    """Replace stored turns (e.g. after diagnose conclude updates a result)."""

    messages: list = Field(min_length=1, max_length=40)
