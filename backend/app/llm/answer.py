"""Compose a grounded, layered answer from retrieved evidence.

The system prompt below is a CONTRACT, not a suggestion. Every rule in it
exists to keep the LLM inside the trust boundary:
  - only provided evidence  -> no hallucinated facts
  - no new numbers          -> quantities come from calculators/safety/passages
  - admit insufficiency     -> a thin dossier produces "I can't answer", not fiction
  - cite by index           -> we attach real citations to the final answer
"""

from sqlalchemy.orm import Session

from app.kitchen.personalize import kitchen_prompt_block
from app.llm.client import complete_json
from app.rag.retrieval import search_passages
from app.safety.temps import find_temp_rule, rule_to_response

SYSTEM_PROMPT = """\
You are the explanation layer of KitchenLab, an evidence-based cooking app.
You will receive a user's cooking question, numbered EVIDENCE passages from
a curated food-science knowledge base, and possibly an authoritative SAFETY
record.

Rules you must never break:
1. Use ONLY the provided evidence and safety record. Do not add facts,
   temperatures, times, or quantities from anywhere else.
2. If a safety record is provided, its numbers are authoritative -- repeat
   them exactly.
3. If the evidence is insufficient to answer the question, set
   "sufficient" to false and briefly say what kind of information is
   missing. Do not attempt a partial guess.
4. Respect the confidence field of each passage: if a passage you rely on
   is marked "low" or its content says the claim is debated, say so in
   "caveats".
5. Respect each passage's scope; do not apply a claim outside it.

Respond with JSON exactly in this shape:
{
  "sufficient": true/false,
  "action": "what the user should do, concise and practical",
  "reason": "why it works, one short paragraph in plain language",
  "science": "the underlying mechanism, for the curious",
  "caveats": "uncertainty, scope limits, or safety notes; empty string if none",
  "citations_used": [list of evidence numbers you actually relied on]
}
"""


def answer_question(
    db: Session,
    question: str,
    top_k: int = 5,
    kitchen_snapshot: dict | None = None,
) -> dict:
    # 1. Gather evidence: semantic retrieval + deterministic safety lookup.
    passages = search_passages(db, question, top_k)
    safety_rule = find_temp_rule(db, question)
    safety = rule_to_response(safety_rule) if safety_rule else None

    # 2. Build the dossier the LLM is allowed to use.
    evidence_lines = []
    for i, p in enumerate(passages, start=1):
        evidence_lines.append(
            f"[{i}] (confidence: {p['confidence']}; scope: {p['scope']})\n"
            f"Claim: {p['claim']}\n{p['content']}"
        )
    user_prompt = f"QUESTION: {question}\n\nEVIDENCE:\n" + "\n\n".join(evidence_lines)
    kitchen = kitchen_prompt_block(kitchen_snapshot)
    if kitchen:
        user_prompt += f"\n\n{kitchen}"
    if safety:
        user_prompt += (
            f"\n\nSAFETY (authoritative, from {safety['source']['title']}): "
            f"{safety['food']}: minimum internal temperature "
            f"{safety['min_internal_temp_f']}F / {safety['min_internal_temp_c']}C"
            + (f", rest {safety['rest_time_min']:.0f} min" if safety["rest_time_min"] else "")
        )

    # 3. The LLM phrases; we attach the real citation objects afterwards.
    result = complete_json(SYSTEM_PROMPT, user_prompt)

    used = result.get("citations_used") or []
    citations = [
        {
            "claim": passages[i - 1]["claim"],
            "confidence": passages[i - 1]["confidence"],
            "scope": passages[i - 1]["scope"],
            "source": passages[i - 1]["source"],
        }
        for i in used
        if isinstance(i, int) and 1 <= i <= len(passages)
    ]

    return {
        "sufficient": result.get("sufficient", False),
        "action": result.get("action", ""),
        "reason": result.get("reason", ""),
        "science": result.get("science", ""),
        "caveats": result.get("caveats", ""),
        "citations": citations,
        "safety": safety,
    }
