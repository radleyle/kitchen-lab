"""Thin, provider-agnostic chat client.

Everything else in the app calls complete_json(); only this file knows the
provider is OpenAI. Swapping providers (Anthropic, local model) later means
changing this one function.
"""

import json

from app.core.config import settings
from app.rag.embeddings import get_client  # reuse the configured OpenAI client


def complete_json(system: str, user: str) -> dict:
    """Send a system+user prompt; get back parsed JSON.

    temperature=0.2: nearly deterministic. The explanation layer should be
    consistent, not creative.
    response_format json_object: the API guarantees syntactically valid JSON.
    """
    response = get_client().chat.completions.create(
        model=settings.chat_model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(response.choices[0].message.content)
