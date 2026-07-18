"""The diagnosis flow: match symptom -> ask -> assess answers -> rank.

Two LLM calls, both kept away from the verdict math:
  1. match_symptom: pick which taxonomy entry the user's story describes
     (classification against a fixed list -- it cannot invent symptoms).
  2. assess_evidence: translate each free-text answer into
     supports/contradicts/neutral per cause. The multiplicative scoring in
     scoring.py then produces the ranking deterministically.

The final fix recommendation reuses the grounded answer pipeline, so it
arrives cited like everything else.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.diagnosis.evidence import apply_hard_evidence
from app.diagnosis.scoring import VERDICTS, confidence_category, score_causes
from app.llm.answer import answer_question
from app.llm.client import complete_json
from app.models import Symptom, SymptomCause

MATCH_PROMPT = """\
You match a user's description of a cooking failure to a known symptom.
You will get the description and a numbered list of symptoms. Pick the one
that best matches. If none plausibly matches, use 0.

Respond with JSON exactly in this shape:
{"symptom_number": <int, 0 if no match>, "confidence": "high" | "medium" | "low"}
"""

ASSESS_PROMPT = """\
You translate a home cook's answers to diagnostic questions into structured
evidence. You will get a cooking failure, a numbered list of CANDIDATE
CAUSES, and the QUESTIONS with the user's ANSWERS.

For EVERY candidate cause, decide what each answer implies:
- "supports": the answer indicates this cause ACTUALLY HAPPENED in the
  user's kitchen
- "contradicts": the answer indicates this cause did NOT happen
- "neutral": the answer says nothing about this cause, or is too vague

Rules:
1. Judge only from what the user actually said. Vague or uncertain answers
   ("I think so", "not sure") are "neutral".
2. Negatively-phrased causes flip carefully. Worked example:
   Cause: "No pre-salting or brining"
   Answer: "Salty marinade for 4 hours"
   Verdict: "contradicts"  (they DID salt/brine ahead, so this cause is false)
3. An answer can bear on causes other than the question it responded to.
4. Emit exactly one verdict per answer, in the same order as the answers.
5. Do not diagnose, rank, or recommend anything. Verdicts only.

Respond with JSON exactly in this shape:
{"assessments": [
  {"cause_number": <int>, "verdicts": ["supports" | "contradicts" | "neutral", ...one per answer],
   "key_evidence": "short quote or paraphrase of the decisive answer, or empty string"}
]}
"""


def _causes_for(db: Session, symptom: Symptom) -> list[SymptomCause]:
    return list(
        db.scalars(
            select(SymptomCause)
            .where(SymptomCause.symptom_id == symptom.id)
            .order_by(SymptomCause.prior_weight.desc())
        )
    )


def match_symptom(db: Session, description: str) -> Symptom | None:
    symptoms = list(db.scalars(select(Symptom).order_by(Symptom.id)))
    if not symptoms:
        return None
    listing = "\n".join(
        f"[{i}] {s.description} (domain: {s.domain})"
        for i, s in enumerate(symptoms, start=1)
    )
    result = complete_json(
        MATCH_PROMPT, f"DESCRIPTION: {description}\n\nSYMPTOMS:\n{listing}"
    )
    n = result.get("symptom_number", 0)
    if isinstance(n, int) and 1 <= n <= len(symptoms):
        return symptoms[n - 1]
    return None


def start_diagnosis(db: Session, description: str) -> dict:
    """Round 1: identify the symptom, return prior-ranked causes + questions."""
    symptom = match_symptom(db, description)
    if symptom is None:
        return {
            "matched": False,
            "message": (
                "This doesn't match a failure pattern in the taxonomy yet. "
                "Try describing what went wrong with the dish itself "
                "(texture, appearance, taste)."
            ),
        }

    causes = _causes_for(db, symptom)
    priors = {c.id: c.prior_weight for c in causes}
    normalized = score_causes(priors, {})  # no evidence yet: normalized priors

    return {
        "matched": True,
        "symptom": {"slug": symptom.slug, "description": symptom.description},
        "candidate_causes": [
            {
                "cause_id": c.id,
                "cause": c.cause,
                "prior_score": round(normalized[c.id], 3),
            }
            for c in causes
        ],
        "questions": [
            {"cause_id": c.id, "question": c.follow_up_question}
            for c in causes
            if c.follow_up_question
        ],
        "next_step": (
            "Answer the questions (any subset), then call /diagnose/conclude "
            "with the symptom slug and your answers."
        ),
    }


def conclude_diagnosis(
    db: Session, symptom_slug: str, description: str, answers: list[dict]
) -> dict:
    """Round 2: fold answers into the ranking, return diagnosis + cited fix.

    answers: [{"question": "...", "answer": "..."}]
    """
    symptom = db.scalar(select(Symptom).where(Symptom.slug == symptom_slug))
    if symptom is None:
        return {"matched": False, "message": f"Unknown symptom slug: {symptom_slug}"}

    causes = _causes_for(db, symptom)
    priors = {c.id: c.prior_weight for c in causes}

    verdicts: dict[int, list[str]] = {}
    evidence_notes: dict[int, str] = {}
    if answers:
        cause_listing = "\n".join(
            f"[{i}] {c.cause} -- {c.explanation}"
            for i, c in enumerate(causes, start=1)
        )
        qa_listing = "\n".join(
            f"Q{i}: {a.get('question', '')}\nA{i}: {a.get('answer', '')}"
            for i, a in enumerate(answers, start=1)
        )
        result = complete_json(
            ASSESS_PROMPT,
            f"FAILURE: {symptom.description}\nUSER'S STORY: {description}\n\n"
            f"CANDIDATE CAUSES:\n{cause_listing}\n\n"
            f"QUESTIONS AND ANSWERS:\n{qa_listing}",
        )
        for item in result.get("assessments", []):
            n = item.get("cause_number")
            if not (isinstance(n, int) and 1 <= n <= len(causes)):
                continue
            cause = causes[n - 1]
            # Keep only valid verdicts; anything malformed degrades to neutral.
            verdicts[cause.id] = [
                v if v in VERDICTS else "neutral"
                for v in item.get("verdicts", [])
                if isinstance(v, str)
            ]
            if item.get("key_evidence"):
                evidence_notes[cause.id] = item["key_evidence"]

        # Deterministic last word on clear keyword cases (e.g. marinade
        # cannot "support" a "no pre-salting" cause).
        verdicts = apply_hard_evidence(causes, answers, verdicts, evidence_notes)

    scores = score_causes(priors, verdicts)
    ranked = sorted(causes, key=lambda c: scores[c.id], reverse=True)
    top = ranked[0]
    confidence = confidence_category(scores) if answers else "low"

    # The fix arrives through the grounded pipeline -> cited like everything else.
    fix = answer_question(
        db, f"{symptom.description}: how to prevent and fix '{top.cause}'"
    )

    return {
        "matched": True,
        "symptom": {"slug": symptom.slug, "description": symptom.description},
        "diagnosis": {
            "most_likely_cause": top.cause,
            "explanation": top.explanation,
            "confidence": confidence,
            "key_evidence": evidence_notes.get(top.id, ""),
        },
        "ranked_causes": [
            {
                "cause": c.cause,
                "score": round(scores[c.id], 3),
                "evidence_verdicts": verdicts.get(c.id, []),
                "key_evidence": evidence_notes.get(c.id, ""),
            }
            for c in ranked
        ],
        "fix": fix,
    }
