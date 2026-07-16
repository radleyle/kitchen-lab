"""Embed any knowledge passages that don't have vectors yet.

Run inside the container (after seeding passages):
    docker compose exec backend python -m app.rag.ingestion
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import SourcePassage
from app.rag.embeddings import embed_texts


def embed_pending_passages(db: Session, batch_size: int = 64) -> int:
    """Find passages with no embedding, embed them, save. Returns count."""
    pending = db.scalars(
        select(SourcePassage).where(SourcePassage.embedding.is_(None))
    ).all()

    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        # Embed claim + content together: the claim is a distilled summary,
        # and including it improves matching for question-shaped queries.
        vectors = embed_texts([f"{p.claim}\n{p.content}" for p in batch])
        for passage, vector in zip(batch, vectors):
            passage.embedding = vector
        db.commit()

    return len(pending)


if __name__ == "__main__":
    with SessionLocal() as session:
        count = embed_pending_passages(session)
        print(f"Embedded {count} passages.")
