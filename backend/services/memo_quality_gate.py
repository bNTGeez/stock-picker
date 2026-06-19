"""Manual Phase 3 memo quality evaluation gate."""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.schemas import (
    ManualMemoQualityReview,
    MemoEvidenceValidationStatus,
    MemoQualityCriterion,
)


MINIMUM_AVERAGE_SCORE = 4.0
MINIMUM_CRITERION_SCORE = 3

PHASE_3_RUBRIC: dict[MemoQualityCriterion, str] = {
    MemoQualityCriterion.REAL_VARIANT_HYPOTHESIS: (
        "Did it identify the real variant hypothesis?"
    ),
    MemoQualityCriterion.OBVIOUS_RISKS: "Did it miss obvious risks?",
    MemoQualityCriterion.CONFIDENCE_CALIBRATION: "Did it overstate confidence?",
    MemoQualityCriterion.PRICED_IN_EXPLANATION: (
        "Did it correctly explain what is priced in?"
    ),
    MemoQualityCriterion.MONITORING_RULES: (
        "Were the monitoring rules useful and specific?"
    ),
    MemoQualityCriterion.EVIDENCE_SUPPORT: (
        "Did the evidence actually support the conclusion?"
    ),
    MemoQualityCriterion.OPPOSING_CASE: (
        "Did it fairly present the strongest opposing case?"
    ),
    MemoQualityCriterion.FINAL_SYNTHESIS: (
        "Did the final synthesis explain why one argument was better supported?"
    ),
}

QUALITATIVE_ONLY_CRITERIA_UNTIL_PHASE_4: tuple[MemoQualityCriterion, ...] = (
    MemoQualityCriterion.PRICED_IN_EXPLANATION,
)


@dataclass(frozen=True)
class MemoQualityGateResult:
    """Deterministic pass/fail result for one manual memo quality review."""

    passed: bool
    average_score: float
    criterion_scores: dict[MemoQualityCriterion, int]
    failing_reasons: tuple[str, ...]


def evaluate_memo_quality_gate(
    review: ManualMemoQualityReview,
) -> MemoQualityGateResult:
    """Apply the Phase 3 manual rubric gate to reviewer-entered scores."""

    criterion_scores = {
        criterion_score.criterion: criterion_score.score
        for criterion_score in review.criterion_scores
    }
    average_score = sum(criterion_scores.values()) / len(criterion_scores)

    failing_reasons: list[str] = []
    if average_score < MINIMUM_AVERAGE_SCORE:
        failing_reasons.append(
            "Average score "
            f"{average_score:.2f} is below {MINIMUM_AVERAGE_SCORE:.1f}."
        )

    low_scores = {
        criterion: score
        for criterion, score in criterion_scores.items()
        if score < MINIMUM_CRITERION_SCORE
    }
    for criterion, score in sorted(low_scores.items(), key=lambda item: item[0].value):
        failing_reasons.append(
            f"{criterion.value} score {score} is below "
            f"{MINIMUM_CRITERION_SCORE}."
        )

    if review.evidence_validation_status is not MemoEvidenceValidationStatus.VALIDATED:
        failing_reasons.append(
            "Evidence validation status must be validated; got "
            f"{review.evidence_validation_status.value}."
        )

    return MemoQualityGateResult(
        passed=not failing_reasons,
        average_score=average_score,
        criterion_scores=criterion_scores,
        failing_reasons=tuple(failing_reasons),
    )


__all__ = [
    "MINIMUM_AVERAGE_SCORE",
    "MINIMUM_CRITERION_SCORE",
    "MemoQualityGateResult",
    "PHASE_3_RUBRIC",
    "QUALITATIVE_ONLY_CRITERIA_UNTIL_PHASE_4",
    "evaluate_memo_quality_gate",
]
