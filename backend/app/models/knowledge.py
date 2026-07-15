"""The cited science layer: the product's trust backbone.

Three levels of authority (stored in KnowledgeSource.authority_level):
  "safety"    -> regulatory/public-health guidance (USDA, FDA)
  "science"   -> textbooks, peer-reviewed studies
  "culinary"  -> tested procedures and expert consensus
"""

from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base

# Dimension of OpenAI's text-embedding-3-small vectors.
EMBEDDING_DIM = 1536


class ScientificMechanism(Base):
    """A physical/chemical process: Maillard browning, gelatinization..."""

    __tablename__ = "scientific_mechanisms"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)  # "maillard-browning"
    name: Mapped[str] = mapped_column(String(120))
    explanation: Mapped[str] = mapped_column(Text)  # the deep "Science" layer


class Technique(Base):
    """A procedure cooks perform: velveting, brining, emulsifying..."""

    __tablename__ = "techniques"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)  # the "Reason" layer
    procedure: Mapped[list] = mapped_column(JSONB, default=list)  # ordered steps
    common_mistakes: Mapped[list] = mapped_column(JSONB, default=list)
    applicable_foods: Mapped[list] = mapped_column(JSONB, default=list)
    mechanism_id: Mapped[int | None] = mapped_column(
        ForeignKey("scientific_mechanisms.id")
    )

    mechanism: Mapped[ScientificMechanism | None] = relationship()


class KnowledgeSource(Base):
    """A book, paper, or agency document we cite from."""

    __tablename__ = "knowledge_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    author: Mapped[str | None] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(30))  # book/paper/agency/article
    authority_level: Mapped[str] = mapped_column(String(20))  # safety/science/culinary
    published_at: Mapped[date | None] = mapped_column(Date)
    reviewed_at: Mapped[date | None] = mapped_column(Date)  # when WE last checked it

    passages: Mapped[list["SourcePassage"]] = relationship(back_populates="source")


class SourcePassage(Base):
    """One claim-sized chunk of a source. This is what RAG retrieves.

    The embedding column stores the passage's meaning as a list of numbers;
    pgvector finds passages whose numbers are 'close' to the question's.
    """

    __tablename__ = "source_passages"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_sources.id"), index=True)
    claim: Mapped[str] = mapped_column(Text)  # one-sentence takeaway
    content: Mapped[str] = mapped_column(Text)  # the supporting passage
    scope: Mapped[str | None] = mapped_column(Text)  # "applies to flour breading only"
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    source: Mapped[KnowledgeSource] = relationship(back_populates="passages")


class SafetyRule(Base):
    """Deterministic food-safety thresholds. The LLM NEVER generates these."""

    __tablename__ = "safety_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    food: Mapped[str] = mapped_column(String(120), index=True)  # "chicken, whole cuts"
    rule_type: Mapped[str] = mapped_column(String(40))  # internal_temp / storage / allergen
    min_internal_temp_c: Mapped[float | None] = mapped_column()
    rest_time_min: Mapped[float | None] = mapped_column()
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    source_id: Mapped[int] = mapped_column(ForeignKey("knowledge_sources.id"))

    source: Mapped[KnowledgeSource] = relationship()
