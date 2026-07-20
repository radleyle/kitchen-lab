"""Recipes (generated or adapted), diagnosis taxonomy, and conversations."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable: seed/example recipes belong to no one; user recipes are owned.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    servings: Mapped[int | None] = mapped_column()
    source_url: Mapped[str | None] = mapped_column(String(500))  # for adapted recipes
    # Cover photo from Unsplash (or null → frontend uses local stock fallback).
    image_url: Mapped[str | None] = mapped_column(String(1000))
    image_credit: Mapped[str | None] = mapped_column(String(200))
    image_credit_url: Mapped[str | None] = mapped_column(String(500))
    # [{"ingredient": "chicken breast", "grams": 450, "note": "sliced thin"}]
    ingredients: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    steps: Mapped[list["RecipeStep"]] = relationship(
        back_populates="recipe",
        order_by="RecipeStep.position",
        cascade="all, delete-orphan",
    )


class RecipeStep(Base):
    """One step, carrying its science annotations (the Action/Reason/Science layers)."""

    __tablename__ = "recipe_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"), index=True)
    position: Mapped[int] = mapped_column()  # step 1, 2, 3...

    instruction: Mapped[str] = mapped_column(Text)  # Action: what to do
    why: Mapped[str | None] = mapped_column(Text)  # Reason: why it works
    science: Mapped[str | None] = mapped_column(Text)  # Science: the mechanism
    critical_temp_c: Mapped[float | None] = mapped_column()  # from safety/calculators
    visual_cues: Mapped[str | None] = mapped_column(Text)  # "edges turn opaque"
    technique_id: Mapped[int | None] = mapped_column(ForeignKey("techniques.id"))

    recipe: Mapped[Recipe] = relationship(back_populates="steps")


class Symptom(Base):
    """A cooking failure users report: 'meat is tough', 'sauce separated'."""

    __tablename__ = "symptoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(40))  # meat / sauces / baking


class SymptomCause(Base):
    """One possible cause of a symptom, with a question that helps confirm it."""

    __tablename__ = "symptom_causes"

    id: Mapped[int] = mapped_column(primary_key=True)
    symptom_id: Mapped[int] = mapped_column(ForeignKey("symptoms.id"), index=True)
    cause: Mapped[str] = mapped_column(String(200))  # "overcooked past 71C"
    explanation: Mapped[str] = mapped_column(Text)
    # How common this cause is before we know anything else (0-1).
    # Diagnosis starts here, then follow-up answers adjust the ranking.
    prior_weight: Mapped[float] = mapped_column(default=0.5)
    follow_up_question: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_sources.id"))

    symptom: Mapped[Symptom] = relationship()


class AssistantConversation(Base):
    """A chat with the agent, kept so users can look back (Ask history).

    messages JSON shape (append-only turns):
      [{"id", "question", "response", "diagnose_slug", "error", "ts"}, ...]
    response holds the full agent envelope so the UI can replay ResultView.
    """

    __tablename__ = "assistant_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20))  # last turn mode
    title: Mapped[str | None] = mapped_column(String(200))
    # [{"id", "question", "response", "diagnose_slug", "error", "ts"}, ...]
    messages: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
