"""Look up a related food photo for a recipe title (Unsplash).

Analogy: after you invent a dish name, you ask a photo library for a
matching plate shot — you don't ask the LLM to paint one. If the library
is closed (no API key) or nothing scores well enough, we return None and
the UI falls back to local stock images.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import settings

logger = logging.getLogger(__name__)

# Words that don't help a food photo search.
_STOP = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "with",
    "for",
    "to",
    "of",
    "in",
    "on",
    "my",
    "your",
    "easy",
    "quick",
    "simple",
    "best",
    "homemade",
    "weeknight",
    "beginner",
    "beginners",
    "classic",
    "style",
    "recipe",
    "dish",
    "plated",
    "food",
}

# Require at least this many meaningful title tokens to appear in the
# photo's text/tags — otherwise we'd rather show stock than a random salad.
_MIN_SCORE = 1.5


def _tokens(text: str) -> list[str]:
    cleaned = re.sub(r"[^\w\s-]", " ", text.lower())
    cleaned = cleaned.replace("-", " ")
    return [w for w in cleaned.split() if w and w not in _STOP and len(w) > 2]


def food_search_queries(title: str) -> list[str]:
    """Build ordered Unsplash queries from most specific → broader."""
    queries: list[str] = []

    # Prefer parenthetical names: "Korean Army Stew (Budae Jjigae)" → budae jjigae
    for paren in re.findall(r"\(([^)]+)\)", title):
        words = _tokens(paren)
        if words:
            queries.append(" ".join(words[:4]))

    words = _tokens(title)
    if words:
        # Tight dish name first (better match than stuffing "food dish plated").
        queries.append(" ".join(words[:4]))
        if len(words) >= 2:
            queries.append(f"{' '.join(words[:3])} recipe")
        # Broader last resort.
        queries.append(f"{words[0]} meal plated")

    # Dedupe while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out or ["homemade meal plated"]


def food_search_query(title: str) -> str:
    """Primary query (kept for tests / logging)."""
    return food_search_queries(title)[0]


def _photo_text(photo: dict) -> str:
    bits = [
        photo.get("alt_description") or "",
        photo.get("description") or "",
    ]
    for tag in photo.get("tags") or []:
        if isinstance(tag, dict):
            bits.append(str(tag.get("title") or ""))
        else:
            bits.append(str(tag))
    return " ".join(bits).lower()


def _score_photo(photo: dict, keywords: list[str]) -> float:
    """How well a photo's text mentions the dish keywords."""
    if not keywords:
        return 0.0
    blob = _photo_text(photo)
    if not blob.strip():
        # No caption — weak signal; only accept if we have nothing better.
        return 0.25
    score = 0.0
    for kw in keywords:
        if kw in blob:
            # Longer / rarer tokens count more.
            score += 1.0 + min(len(kw), 12) / 12.0
    return score


def _search_unsplash(query: str, key: str, per_page: int = 8) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "query": query,
            "per_page": str(per_page),
            "orientation": "landscape",
            "content_filter": "high",
        }
    )
    url = f"https://api.unsplash.com/search/photos?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Client-ID {key}",
            "Accept-Version": "v1",
            "User-Agent": "KitchenLab/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return list(payload.get("results") or [])


def _pack_photo(photo: dict) -> dict[str, str] | None:
    urls = photo.get("urls") or {}
    image_url = urls.get("regular") or urls.get("small")
    if not image_url:
        return None
    user = photo.get("user") or {}
    name = user.get("name") or "Unsplash photographer"
    links = user.get("links") or {}
    credit_url = links.get("html") or (photo.get("links") or {}).get("html") or ""
    if credit_url and "utm_source" not in credit_url:
        credit_url = f"{credit_url}?utm_source=kitchenlab&utm_medium=referral"
    return {
        "url": image_url,
        "credit": f"Photo by {name} on Unsplash",
        "credit_url": credit_url,
    }


def fetch_recipe_image(title: str) -> dict[str, str] | None:
    """Return {url, credit, credit_url} or None if unavailable / poor match.

    Never raises into the recipe pipeline — photo failure must not block cooking.
    """
    key = (settings.unsplash_access_key or "").strip()
    if not key:
        return None

    keywords = _tokens(title)
    # Parenthetical tokens first for scoring (often the real dish name).
    for paren in re.findall(r"\(([^)]+)\)", title):
        for w in reversed(_tokens(paren)):
            if w not in keywords:
                keywords.insert(0, w)

    best_photo: dict | None = None
    best_score = -1.0
    best_query = ""

    try:
        for query in food_search_queries(title):
            results = _search_unsplash(query, key)
            if not results:
                continue
            for photo in results:
                score = _score_photo(photo, keywords)
                if score > best_score:
                    best_score = score
                    best_photo = photo
                    best_query = query
            # Good enough on a specific query — stop early.
            if best_score >= 2.5:
                break
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as err:
        logger.warning("Unsplash lookup failed for %r: %s", title, err)
        return None

    if best_photo is None:
        logger.info("Unsplash: no results for %r", title)
        return None

    if best_score < _MIN_SCORE:
        logger.info(
            "Unsplash: weak match for %r (score=%.2f query=%r) — skipping",
            title,
            best_score,
            best_query,
        )
        return None

    packed = _pack_photo(best_photo)
    if packed:
        logger.info(
            "Unsplash: picked score=%.2f query=%r for %r",
            best_score,
            best_query,
            title,
        )
    return packed
