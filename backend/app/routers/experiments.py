"""Controlled cooking experiments: design, run, observe, conclude.

Auth required. Photos attach to trials as evidence (local disk for now;
s3_key is the storage key either way).
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_current_user
from app.core.db import get_db
from app.lab.experiments import can_transition, design_experiment
from app.models import (
    Attachment,
    Experiment,
    ExperimentTrial,
    Observation,
    User,
)
from app.schemas.lab import (
    AttachmentOut,
    ExperimentCreate,
    ExperimentDesignRequest,
    ExperimentOut,
    ExperimentUpdate,
    ObservationCreate,
    ObservationOut,
)
from app.storage import get_storage

router = APIRouter(prefix="/experiments", tags=["experiments"])


def _load_owned(db: Session, experiment_id: int, user_id: int) -> Experiment:
    experiment = db.scalar(
        select(Experiment)
        .where(Experiment.id == experiment_id)
        .options(
            joinedload(Experiment.trials).joinedload(ExperimentTrial.observations)
        )
    )
    if experiment is None or experiment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.get("", response_model=list[ExperimentOut])
def list_experiments(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Experiment]:
    return list(
        db.scalars(
            select(Experiment)
            .where(Experiment.user_id == user.id)
            .options(
                joinedload(Experiment.trials).joinedload(ExperimentTrial.observations)
            )
            .order_by(Experiment.created_at.desc())
        ).unique()
    )


@router.post("", response_model=ExperimentOut, status_code=status.HTTP_201_CREATED)
def create_experiment(
    body: ExperimentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Experiment:
    experiment = Experiment(
        user_id=user.id,
        question=body.question,
        hypothesis=body.hypothesis,
        independent_variable=body.independent_variable,
        constants=body.constants,
        status="planned",
    )
    db.add(experiment)
    db.flush()
    for trial in body.trials:
        db.add(
            ExperimentTrial(
                experiment_id=experiment.id,
                label=trial.label,
                variable_value=trial.variable_value,
                notes=trial.notes,
            )
        )
    db.commit()
    return _load_owned(db, experiment.id, user.id)


@router.post("/design")
def design(
    body: ExperimentDesignRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """LLM drafts a controlled experiment; optionally persist it."""
    draft = design_experiment(body.message)
    if not draft.get("feasible"):
        return draft
    if not body.persist:
        draft["persisted"] = False
        return draft

    experiment = Experiment(
        user_id=user.id,
        question=draft["question"],
        hypothesis=draft.get("hypothesis"),
        independent_variable=draft["independent_variable"],
        constants=draft.get("constants") or [],
        status="planned",
    )
    db.add(experiment)
    db.flush()
    for trial in draft["trials"]:
        db.add(
            ExperimentTrial(
                experiment_id=experiment.id,
                label=trial.get("label", "trial"),
                variable_value=trial.get("variable_value", ""),
                notes=(
                    "Suggested metrics: "
                    + ", ".join(trial.get("suggested_metrics") or [])
                    if trial.get("suggested_metrics")
                    else None
                ),
            )
        )
    db.commit()
    draft["persisted"] = True
    draft["experiment_id"] = experiment.id
    return draft


@router.get("/{experiment_id}", response_model=ExperimentOut)
def get_experiment(
    experiment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Experiment:
    return _load_owned(db, experiment_id, user.id)


@router.patch("/{experiment_id}", response_model=ExperimentOut)
def update_experiment(
    experiment_id: int,
    body: ExperimentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Experiment:
    experiment = _load_owned(db, experiment_id, user.id)
    if body.hypothesis is not None:
        experiment.hypothesis = body.hypothesis
    if body.conclusion is not None:
        experiment.conclusion = body.conclusion
    if body.status is not None:
        if not can_transition(experiment.status, body.status):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot move status from {experiment.status!r} "
                    f"to {body.status!r}"
                ),
            )
        experiment.status = body.status
        if body.status == "done" and not (body.conclusion or experiment.conclusion):
            raise HTTPException(
                status_code=400,
                detail="Write a conclusion before marking the experiment done.",
            )
    db.commit()
    return _load_owned(db, experiment.id, user.id)


@router.post(
    "/{experiment_id}/trials/{trial_id}/observations",
    response_model=ObservationOut,
    status_code=status.HTTP_201_CREATED,
)
def add_observation(
    experiment_id: int,
    trial_id: int,
    body: ObservationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Observation:
    experiment = _load_owned(db, experiment_id, user.id)
    trial = next((t for t in experiment.trials if t.id == trial_id), None)
    if trial is None:
        raise HTTPException(status_code=404, detail="Trial not found")
    if body.value is None and not body.text_value:
        raise HTTPException(
            status_code=400, detail="Provide a numeric value or text_value"
        )
    obs = Observation(
        trial_id=trial.id,
        metric=body.metric,
        value=body.value,
        text_value=body.text_value,
        unit=body.unit,
    )
    db.add(obs)
    if experiment.status == "planned":
        experiment.status = "running"
    db.commit()
    db.refresh(obs)
    return obs


@router.post(
    "/{experiment_id}/trials/{trial_id}/photos",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_trial_photo(
    experiment_id: int,
    trial_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Attachment:
    experiment = _load_owned(db, experiment_id, user.id)
    trial = next((t for t in experiment.trials if t.id == trial_id), None)
    if trial is None:
        raise HTTPException(status_code=404, detail="Trial not found")

    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    storage = get_storage()
    try:
        key = storage.save(user.id, content_type, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    attachment = Attachment(
        user_id=user.id,
        s3_key=key,
        kind="photo",
        trial_id=trial.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment
