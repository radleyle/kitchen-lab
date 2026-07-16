"""LLM call #1: classify the message and extract structured entities.

Small, fast, near-deterministic. Returns facts only -- the answering happens
elsewhere. If classification is unsure, it falls back to "learn" (a grounded
explanation is the safest default response).
"""

from app.llm.client import complete_json

MODES = ("learn", "cook", "adapt", "diagnose", "substitute", "experiment")

SYSTEM_PROMPT = """\
You classify messages sent to KitchenLab, a science-based cooking assistant.

Modes:
- "learn":      user wants a concept or technique explained ("what is Maillard?")
- "cook":       user wants a recipe or cooking plan generated ("how should I cook X tonight?")
- "adapt":      user has an existing recipe to modify/convert ("make this work in an air fryer")
- "diagnose":   something went wrong and they want to know why ("my sauce broke")
- "substitute": user wants to replace an ingredient ("potato starch instead of cornstarch?")
- "experiment": user wants to design a controlled cooking test ("does resting steak matter? how do I test it?")

Respond with JSON exactly in this shape (use null when not present):
{
  "mode": "one of the six modes above",
  "food": "the main food involved, or null",
  "technique": "named technique if any, or null",
  "problem": "the failure described, or null",
  "ingredient_to_replace": "for substitute mode, or null",
  "confidence": "high" | "medium" | "low"
}
"""


def classify(message: str) -> dict:
    result = complete_json(SYSTEM_PROMPT, message)
    if result.get("mode") not in MODES:
        result["mode"] = "learn"
        result["confidence"] = "low"
    return result
