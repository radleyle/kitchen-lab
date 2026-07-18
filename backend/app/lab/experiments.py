"""Experiment design helpers and status rules.

A good home-kitchen experiment has one independent variable, a short list
of constants, and at least two trials (usually control + treatment). The
LLM can draft that structure; status transitions and ownership stay in code.
"""

from app.llm.client import complete_json

VALID_STATUSES = ("planned", "running", "done")

# planned -> running -> done; also planned -> done (skipped mid-run)
ALLOWED_TRANSITIONS = {
    "planned": {"running", "done"},
    "running": {"done"},
    "done": set(),
}

DESIGN_PROMPT = """\
You help a home cook design a small controlled cooking experiment for
KitchenLab. You will get their QUESTION or idea.

Design ONE independent variable and 2-3 trials (include a control when
sensible). Keep constants to things a home cook can actually hold fixed.
Do not invent measurement instruments they likely lack; prefer thermometer,
scale, timer, and simple 1-5 sensory ratings.

Respond with JSON exactly in this shape:
{
  "feasible": true/false,
  "question": "clear testable question",
  "hypothesis": "if X then Y, because...",
  "independent_variable": "the one thing that changes",
  "constants": ["list of things held fixed"],
  "trials": [
    {"label": "control or short name", "variable_value": "what this arm does",
     "suggested_metrics": ["mass_g", "internal_temp_c", "juiciness_1_to_5"]}
  ],
  "how_to_judge": "one sentence on comparing the trials fairly"
}
If the message is not an experiment request, set feasible to false and
fill question with a brief explanation.
"""


def can_transition(current: str, new: str) -> bool:
    if current not in VALID_STATUSES or new not in VALID_STATUSES:
        return False
    if current == new:
        return True
    return new in ALLOWED_TRANSITIONS[current]


def design_experiment(message: str) -> dict:
    """LLM drafts a structured experiment; caller may persist it."""
    result = complete_json(DESIGN_PROMPT, message)
    if not result.get("feasible", False):
        return {
            "feasible": False,
            "message": result.get("question")
            or "That doesn't look like an experiment request.",
        }
    trials = result.get("trials") or []
    if len(trials) < 2:
        return {
            "feasible": False,
            "message": "Need at least two trials (e.g. control + treatment).",
        }
    return {
        "feasible": True,
        "question": result.get("question", message),
        "hypothesis": result.get("hypothesis"),
        "independent_variable": result.get("independent_variable", ""),
        "constants": result.get("constants") or [],
        "trials": trials,
        "how_to_judge": result.get("how_to_judge", ""),
    }
