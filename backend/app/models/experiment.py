"""Controlled cooking experiments and the personal notebook."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Experiment(Base):
    """A user's controlled test: 'Does 45-min pre-salting improve my steak?'"""

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    hypothesis: Mapped[str | None] = mapped_column(Text)
    independent_variable: Mapped[str] = mapped_column(String(200))  # what changes
    constants: Mapped[list] = mapped_column(JSONB, default=list)  # what stays fixed
    status: Mapped[str] = mapped_column(String(20), default="planned")  # planned/running/done
    conclusion: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    trials: Mapped[list["ExperimentTrial"]] = relationship(back_populates="experiment")


class ExperimentTrial(Base):
    """One arm of the experiment, e.g. 'salted 45 min before' vs 'salted at cook time'."""

    __tablename__ = "experiment_trials"

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id"), index=True)
    label: Mapped[str] = mapped_column(String(100))  # "control", "45-min salt"
    variable_value: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    experiment: Mapped[Experiment] = relationship(back_populates="trials")
    observations: Mapped[list["Observation"]] = relationship(back_populates="trial")


class Observation(Base):
    """One measurement in one trial: mass before/after, temp, texture rating..."""

    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("experiment_trials.id"), index=True)
    metric: Mapped[str] = mapped_column(String(80))  # "mass_g", "internal_temp_c"
    value: Mapped[float | None] = mapped_column()
    text_value: Mapped[str | None] = mapped_column(Text)  # for non-numeric notes
    unit: Mapped[str | None] = mapped_column(String(20))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    trial: Mapped[ExperimentTrial] = relationship(back_populates="observations")


class Attachment(Base):
    """A photo (stored in S3; we keep only its key/path here)."""

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    s3_key: Mapped[str] = mapped_column(String(500))
    kind: Mapped[str] = mapped_column(String(30), default="photo")
    trial_id: Mapped[int | None] = mapped_column(ForeignKey("experiment_trials.id"))
    notebook_entry_id: Mapped[int | None] = mapped_column(ForeignKey("notebook_entries.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NotebookEntry(Base):
    """Free-form journal: outcomes, tweaks that worked, things to remember."""

    __tablename__ = "notebook_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    recipe_id: Mapped[int | None] = mapped_column(ForeignKey("recipes.id"))
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("experiments.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
