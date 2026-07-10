"""
Demo API Route — /api/demo
===========================
Step 9: Polish, testing, demo prep

Serves pre-cached query responses from data/demo_cache.json to ensure
demo stability without requiring live LLM inference.

Endpoints:
  GET  /api/demo/questions      → list all 5 demo questions
  GET  /api/demo/answer/{index} → get the full cached response for question #index
"""

from fastapi import APIRouter, HTTPException
from typing import Any
import json
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Load demo cache at module import time (fast, fail-safe)
# ---------------------------------------------------------------------------
_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "demo_cache.json",
)

_demo_cache: list[dict[str, Any]] = []

try:
    with open(_CACHE_PATH, "r", encoding="utf-8") as f:
        _demo_cache = json.load(f)
    logger.info(f"Demo cache loaded: {len(_demo_cache)} pre-cached responses from '{_CACHE_PATH}'")
except FileNotFoundError:
    logger.warning(f"Demo cache file not found at '{_CACHE_PATH}'. Demo endpoints will return 503.")
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse demo cache JSON: {e}")


# ---------------------------------------------------------------------------
# Endpoint helpers
# ---------------------------------------------------------------------------

def _cache_unavailable() -> None:
    """Raises a 503 if the cache failed to load."""
    if not _demo_cache:
        raise HTTPException(
            status_code=503,
            detail="Demo cache is unavailable. Ensure 'backend/data/demo_cache.json' exists and is valid JSON.",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/demo/questions")
def get_demo_questions() -> dict[str, Any]:
    """
    Returns the list of pre-built demo question strings.
    Clients use the index to fetch the full cached response.
    """
    _cache_unavailable()
    return {
        "questions": [entry["question"] for entry in _demo_cache],
        "count": len(_demo_cache),
        "note": "Use GET /api/demo/answer/{index} to retrieve a full cached response."
    }


@router.get("/demo/answer/{index}")
def get_demo_answer(index: int) -> dict[str, Any]:
    """
    Returns the full pre-cached response for the demo question at position `index`
    (0-based). The response has the same schema as POST /api/query for seamless
    frontend compatibility:
      {
        question, answer, citations, plan, elapsed_seconds,
        _cached: true   ← extra field to signal cache origin
      }
    """
    _cache_unavailable()

    if index < 0 or index >= len(_demo_cache):
        raise HTTPException(
            status_code=404,
            detail=f"Demo index {index} out of range. Valid range: 0–{len(_demo_cache) - 1}.",
        )

    entry = dict(_demo_cache[index])
    entry["_cached"] = True        # Signal to the frontend that this is a cached response
    entry["chunks_used"] = []      # Maintain schema compatibility with live /api/query
    return entry
