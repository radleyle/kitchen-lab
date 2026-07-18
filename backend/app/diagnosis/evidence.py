"""Hard evidence rules that outrank the LLM assessor on clear cases.

The assessor is good at messy language, but consistently trips on
negatively-phrased causes ("No pre-salting") when the user describes
doing the opposite ("salty marinade"). Same lesson as recipe grams:
when a failure mode is known and detectable with keywords, Python decides.

Rules only *override* when a signal is clear. Vague answers stay with
whatever the LLM said (or neutral).
"""

from __future__ import annotations

import re

from app.models import SymptomCause

# Cause text that means "the cook skipped salting/brining ahead".
ABSENCE_OF_SALT = re.compile(
    r"(no pre-?salt|not (pre-?)?salt|skipped .{0,20}salt|without .{0,20}brin"
    r"|unbrined|never salt)",
    re.I,
)

# Answers that prove the cook DID salt/brine ahead.
DID_SALT_AHEAD = (
    "marinade",
    "marinated",
    "brine",
    "brined",
    "dry-brin",
    "dry brin",
    "salted ahead",
    "salted for",
    "salted overnight",
    "pre-salt",
    "presalt",
    "salted the night",
)

# Answers that prove they skipped ahead-of-time salting.
SKIPPED_SALT_AHEAD = (
    "didn't salt",
    "did not salt",
    "no salt",
    "never salted",
    "salted right before",
    "salted just before",
    "salted at the end",
    "salted after",
    "only salted when",
)

WITH_THE_GRAIN = re.compile(
    r"with the grain|along the (grain|lines|fibers?)|lengthwise along",
    re.I,
)
AGAINST_THE_GRAIN = re.compile(
    r"against the grain|across the (grain|lines|fibers?)",
    re.I,
)


def _answers_text(answers: list[dict]) -> str:
    return " ".join(
        f"{a.get('question', '')} {a.get('answer', '')}" for a in answers
    ).lower()


def apply_hard_evidence(
    causes: list[SymptomCause],
    answers: list[dict],
    verdicts: dict[int, list[str]],
    evidence_notes: dict[int, str],
) -> dict[int, list[str]]:
    """Return verdicts with hard-rule overrides applied (may mutate notes)."""
    if not answers:
        return verdicts

    text = _answers_text(answers)
    out = {cid: list(vs) for cid, vs in verdicts.items()}

    for cause in causes:
        cid = cause.id
        name = cause.cause

        if ABSENCE_OF_SALT.search(name):
            if any(sig in text for sig in DID_SALT_AHEAD):
                out[cid] = ["contradicts"]
                evidence_notes[cid] = (
                    "Hard rule: answer indicates salting/brining ahead "
                    "(negates 'no pre-salting')."
                )
            elif any(sig in text for sig in SKIPPED_SALT_AHEAD):
                out[cid] = ["supports"]
                evidence_notes[cid] = (
                    "Hard rule: answer indicates salting was skipped ahead."
                )

        if re.search(r"with the grain", name, re.I):
            if WITH_THE_GRAIN.search(text):
                out[cid] = ["supports"]
                evidence_notes[cid] = (
                    "Hard rule: answer describes slicing with/along the grain."
                )
            elif AGAINST_THE_GRAIN.search(text):
                out[cid] = ["contradicts"]
                evidence_notes[cid] = (
                    "Hard rule: answer describes slicing against the grain."
                )

    return out
