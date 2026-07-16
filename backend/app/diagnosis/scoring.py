"""Deterministic cause ranking: priors updated by evidence verdicts.

Informal Bayesian updating. Each cause starts at its prior weight; every
piece of evidence multiplies the score by a factor:

    supports     x 2.2   (answer points at this cause)
    contradicts  x 0.25  (answer rules against it)
    neutral      x 1.0   (answer says nothing about it)

Scores are then normalized to sum to 1 so they read as relative
plausibility WITHIN the causes we know about -- not absolute probability.

Confidence is a category, never a percentage: the app's rule is that exact
numbers appear only where they are calibrated, and these aren't.
"""

SUPPORT_FACTOR = 2.2
CONTRADICT_FACTOR = 0.25

VERDICTS = ("supports", "contradicts", "neutral")


def score_causes(
    priors: dict[int, float], verdicts: dict[int, list[str]]
) -> dict[int, float]:
    """Combine prior weights with per-cause evidence verdicts.

    priors:   {cause_id: prior_weight}
    verdicts: {cause_id: ["supports", "neutral", ...]} -- one verdict per
              answered follow-up question; missing cause_ids mean no evidence.
    Returns normalized scores {cause_id: 0..1} summing to 1.
    """
    scores: dict[int, float] = {}
    for cause_id, prior in priors.items():
        score = max(prior, 1e-6)  # a zero prior would be unrecoverable
        for verdict in verdicts.get(cause_id, []):
            if verdict == "supports":
                score *= SUPPORT_FACTOR
            elif verdict == "contradicts":
                score *= CONTRADICT_FACTOR
            # neutral: x1, no-op
        scores[cause_id] = score

    total = sum(scores.values())
    return {cid: s / total for cid, s in scores.items()}


def confidence_category(scores: dict[int, float]) -> str:
    """How sure are we about the TOP cause? high / medium / low.

    Based on the top score and its margin over the runner-up: a diagnosis
    is only convincing if one cause both dominates and clearly beats the
    alternatives.
    """
    if not scores:
        return "low"
    ranked = sorted(scores.values(), reverse=True)
    top = ranked[0]
    second = ranked[1] if len(ranked) > 1 else 0.0

    if top >= 0.55 and (second == 0 or top / second >= 1.8):
        return "high"
    if top >= 0.35 and (second == 0 or top / second >= 1.2):
        return "medium"
    return "low"
