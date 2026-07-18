"""Personal cooking notebook (auth required)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models import NotebookEntry, User
from app.schemas.lab import NotebookCreate, NotebookOut, NotebookUpdate

router = APIRouter(prefix="/notebook", tags=["notebook"])


@router.get("", response_model=list[NotebookOut])
def list_entries(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[NotebookEntry]:
    return list(
        db.scalars(
            select(NotebookEntry)
            .where(NotebookEntry.user_id == user.id)
            .order_by(NotebookEntry.created_at.desc())
        )
    )


@router.post("", response_model=NotebookOut, status_code=status.HTTP_201_CREATED)
def create_entry(
    body: NotebookCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotebookEntry:
    entry = NotebookEntry(
        user_id=user.id,
        title=body.title,
        body=body.body,
        recipe_id=body.recipe_id,
        experiment_id=body.experiment_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{entry_id}", response_model=NotebookOut)
def get_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotebookEntry:
    entry = db.get(NotebookEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.patch("/{entry_id}", response_model=NotebookOut)
def update_entry(
    entry_id: int,
    body: NotebookUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotebookEntry:
    entry = db.get(NotebookEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Entry not found")
    if body.title is not None:
        entry.title = body.title
    if body.body is not None:
        entry.body = body.body
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    entry = db.get(NotebookEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(entry)
    db.commit()
