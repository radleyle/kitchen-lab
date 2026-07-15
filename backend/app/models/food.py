"""Ingredients and function-aware substitutions.

The key design idea: a substitution is not "X replaces Y" -- it is
"X replaces Y *when Y is doing this job*". Cornstarch-as-thickener and
cornstarch-as-frying-coating have different substitutes.
"""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str | None] = mapped_column(String(60))  # starch, protein, fat...
    aliases: Mapped[list] = mapped_column(JSONB, default=list)  # ["corn flour (UK)"]
    # Physical/chemical facts used by calculators and explanations,
    # e.g. {"gelatinization_temp_c": [62, 72], "amylose_pct": 25}
    properties: Mapped[dict] = mapped_column(JSONB, default=dict)


class IngredientFunction(Base):
    """A job an ingredient can do in a dish: thickening, binding, leavening..."""

    __tablename__ = "ingredient_functions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Substitution(Base):
    """original -> substitute, valid only for one specific function."""

    __tablename__ = "substitutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), index=True)
    substitute_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    function_id: Mapped[int] = mapped_column(ForeignKey("ingredient_functions.id"))

    # "1 tbsp cornstarch -> 2 tbsp flour" -> ratio 2.0
    ratio: Mapped[float] = mapped_column(default=1.0)
    texture_notes: Mapped[str | None] = mapped_column(Text)
    procedure_adjustments: Mapped[str | None] = mapped_column(Text)
    # low / medium / high -- honest uncertainty, shown to the user
    confidence: Mapped[str] = mapped_column(String(10), default="medium")
    # Where this claim comes from (nullable while the KB is being built)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("knowledge_sources.id"))

    original: Mapped[Ingredient] = relationship(foreign_keys=[original_id])
    substitute: Mapped[Ingredient] = relationship(foreign_keys=[substitute_id])
    function: Mapped[IngredientFunction] = relationship()
