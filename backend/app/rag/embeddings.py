"""Text -> vector, via OpenAI's embedding API."""

from openai import OpenAI

from app.core.config import settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to the .env file at the "
                "project root (see .env.example)."
            )
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts in one API call (batching is cheaper/faster)."""
    response = get_client().embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )
    # The API returns items in input order; each has a 1536-float vector.
    return [item.embedding for item in response.data]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
