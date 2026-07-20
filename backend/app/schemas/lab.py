"""Pydantic shapes for techniques, notebook, and experiments."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MechanismOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    explanation: str


class MechanismSummary(BaseModel):
    """Browse card for the mechanism library (no nested techniques)."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    explanation: str


class TechniqueSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    summary: str
    applicable_foods: list


class MechanismDetail(MechanismSummary):
    """One mechanism plus the techniques that teach it."""

    techniques: list[TechniqueSummary] = []


class TechniqueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    summary: str
    procedure: list
    common_mistakes: list
    applicable_foods: list
    mechanism: MechanismOut | None = None


class NotebookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str | None = None
    recipe_id: int | None = None
    experiment_id: int | None = None


class NotebookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = None


class NotebookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str | None
    recipe_id: int | None
    experiment_id: int | None
    created_at: datetime


class ObservationCreate(BaseModel):
    metric: str = Field(min_length=1, max_length=80)
    value: float | None = None
    text_value: str | None = None
    unit: str | None = Field(default=None, max_length=20)


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    metric: str
    value: float | None
    text_value: str | None
    unit: str | None
    recorded_at: datetime


class TrialCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    variable_value: str = Field(min_length=1, max_length=200)
    notes: str | None = None


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    s3_key: str
    kind: str
    trial_id: int | None
    notebook_entry_id: int | None
    created_at: datetime


class TrialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    variable_value: str
    notes: str | None
    observations: list[ObservationOut] = []
    attachments: list[AttachmentOut] = []


class ExperimentCreate(BaseModel):
    question: str = Field(min_length=5, max_length=2000)
    hypothesis: str | None = None
    independent_variable: str = Field(min_length=1, max_length=200)
    constants: list[str] = Field(default_factory=list)
    trials: list[TrialCreate] = Field(min_length=2, max_length=6)


class ExperimentUpdate(BaseModel):
    hypothesis: str | None = None
    status: str | None = Field(default=None, pattern="^(planned|running|done)$")
    conclusion: str | None = None


class ExperimentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    hypothesis: str | None
    independent_variable: str
    constants: list
    status: str
    conclusion: str | None
    created_at: datetime
    trials: list[TrialOut] = []


class ExperimentDesignRequest(BaseModel):
    message: str = Field(min_length=5, max_length=2000)
    persist: bool = False
