"""Semantic search over the knowledge base."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SourcePassage
from app.rag.embeddings import embed_query


def search_passages(db: Session, query: str, top_k: int = 5) -> list[dict]:
    """Return the top_k most relevant passages, each with its citation.

    cosine_distance: 0 = identical meaning, 2 = opposite. We also convert
    to similarity (1 - distance) because "higher = better" reads naturally.
    """
    query_vector = embed_query(query)

    distance = SourcePassage.embedding.cosine_distance(query_vector)
    rows = db.execute(
        select(SourcePassage, distance.label("distance"))
        .where(SourcePassage.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    ).all()

    results = []
    for passage, dist in rows:
        results.append(
            {
                "claim": passage.claim,
                "content": passage.content,
                "scope": passage.scope,
                "confidence": passage.confidence,
                "similarity": round(1 - dist, 3),
                "source": {
                    "title": passage.source.title,
                    "author": passage.source.author,
                    "url": passage.source.url,
                    "authority_level": passage.source.authority_level,
                },
            }
        )
    return results
