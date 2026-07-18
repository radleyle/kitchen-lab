"""Tests for the pure diagnosis scoring -- the part that must never be an
LLM's opinion. No database, no network: priors and verdicts in, ranking out.
"""

from types import SimpleNamespace

import pytest

from app.diagnosis.evidence import apply_hard_evidence
from app.diagnosis.scoring import confidence_category, score_causes


def test_no_evidence_returns_normalized_priors():
    scores = score_causes({1: 0.5, 2: 0.3, 3: 0.2}, {})
    assert scores[1] == pytest.approx(0.5)
    assert scores[2] == pytest.approx(0.3)
    assert sum(scores.values()) == pytest.approx(1.0)


def test_support_raises_contradiction_lowers():
    priors = {1: 0.5, 2: 0.5}
    scores = score_causes(priors, {1: ["supports"], 2: ["contradicts"]})
    assert scores[1] > 0.8  # 2.2 vs 0.25 -> strong separation
    assert sum(scores.values()) == pytest.approx(1.0)


def test_evidence_can_overturn_priors():
    # An unlikely cause with strong support should beat a likely cause
    # that the answers contradict -- evidence outranks base rates.
    priors = {1: 0.6, 2: 0.1}
    scores = score_causes(
        priors,
        {1: ["contradicts", "contradicts"], 2: ["supports", "supports"]},
    )
    assert scores[2] > scores[1]


def test_neutral_changes_nothing():
    priors = {1: 0.5, 2: 0.5}
    scores = score_causes(priors, {1: ["neutral", "neutral"]})
    assert scores[1] == pytest.approx(scores[2])


def test_zero_prior_is_not_a_black_hole():
    # Even a cause seeded at 0 must stay recoverable by evidence.
    scores = score_causes({1: 0.0, 2: 0.5}, {1: ["supports"] * 5})
    assert scores[1] > 0


def test_confidence_high_needs_dominance_and_margin():
    assert confidence_category({1: 0.7, 2: 0.2, 3: 0.1}) == "high"
    # High top score but a close runner-up -> not high confidence.
    assert confidence_category({1: 0.5, 2: 0.45, 3: 0.05}) != "high"


def test_confidence_low_when_flat():
    assert confidence_category({1: 0.26, 2: 0.25, 3: 0.25, 4: 0.24}) == "low"


def test_confidence_single_cause():
    assert confidence_category({1: 1.0}) == "high"
    assert confidence_category({}) == "low"


def test_hard_rule_marinade_contradicts_no_presalting():
    # The live-eval failure mode: LLM said "supports"; Python must override.
    causes = [
        SimpleNamespace(id=4, cause="No pre-salting or brining"),
        SimpleNamespace(id=2, cause="Sliced with the grain instead of against it"),
    ]
    answers = [
        {"question": "Did you salt ahead?", "answer": "Salty marinade for 4 hours"},
        {"question": "How did you slice?", "answer": "Lengthwise along the grain"},
    ]
    verdicts = {4: ["supports"], 2: ["neutral"]}
    notes: dict[int, str] = {}
    fixed = apply_hard_evidence(causes, answers, verdicts, notes)
    assert fixed[4] == ["contradicts"]
    assert fixed[2] == ["supports"]
    assert "Hard rule" in notes[4]


def test_hard_rule_skipped_salt_supports_absence_cause():
    causes = [SimpleNamespace(id=4, cause="No pre-salting or brining")]
    answers = [{"question": "Salt?", "answer": "I salted right before it hit the pan"}]
    notes: dict[int, str] = {}
    fixed = apply_hard_evidence(causes, answers, {4: ["neutral"]}, notes)
    assert fixed[4] == ["supports"]
