"""Serve and attach photos. Storage key lives in Attachment.s3_key even
for local files -- the name stays so S3 is a drop-in later.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.db import get_db
from app.models import Attachment, NotebookEntry, User
from app.schemas.lab import AttachmentOut
from app.storage import get_storage

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.get("/{attachment_id}/content")
def get_content(
    attachment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None or attachment.user_id != user.id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    try:
        data = get_storage().load(attachment.s3_key)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="File missing") from exc

    suffix = attachment.s3_key.rsplit(".", 1)[-1].lower()
    media = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    return Response(content=data, media_type=media)


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove the DB row and the file on disk / S3."""
    attachment = db.get(Attachment, attachment_id)
    if attachment is None or attachment.user_id != user.id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    key = attachment.s3_key
    db.delete(attachment)
    db.commit()
    try:
        get_storage().delete(key)
    except (FileNotFoundError, ValueError):
        # Row is gone; orphan file is acceptable for a learning stack.
        pass


@router.post(
    "/notebook/{entry_id}",
    response_model=AttachmentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_notebook_photo(
    entry_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Attachment:
    entry = db.get(NotebookEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notebook entry not found")

    data = await file.read()
    content_type = file.content_type or "application/octet-stream"
    try:
        key = get_storage().save(user.id, content_type, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    attachment = Attachment(
        user_id=user.id,
        s3_key=key,
        kind="photo",
        notebook_entry_id=entry.id,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment
