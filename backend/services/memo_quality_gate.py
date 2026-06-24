"""Manual Phase 3 memo quality evaluation gate."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from backend.models.schemas import (
    ManualMemoQualityReview,
    MemoEvidenceValidationStatus,
    MemoQualityCriterion,
)


MINIMUM_AVERAGE_SCORE = 4.0
MINIMUM_CRITERION_SCORE = 3
MINIMUM_PHASE_3_REVIEW_COUNT = 5
MAXIMUM_PHASE_3_REVIEW_COUNT = 10

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


@dataclass(frozen=True)
class Phase3MemoQualityGateResult:
    """Deterministic pass/fail result for the full Phase 3 review set."""

    passed: bool
    review_count: int
    aggregate_average_score: float
    review_results: tuple[MemoQualityGateResult, ...]
    failing_reasons: tuple[str, ...]


def evaluate_single_memo_quality_review(
    review: ManualMemoQualityReview,
) -> MemoQualityGateResult:
    """Apply the manual rubric thresholds to one reviewer-entered memo review."""

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


def evaluate_memo_quality_gate(
    reviews: Sequence[ManualMemoQualityReview],
) -> Phase3MemoQualityGateResult:
    """Apply the Phase 3 gate across the required 5-10 manual memo reviews."""

    if isinstance(reviews, ManualMemoQualityReview):
        raise TypeError(
            "evaluate_memo_quality_gate expects a sequence of 5-10 manual "
            "memo quality reviews; use evaluate_single_memo_quality_review "
            "for one memo."
        )

    review_results = tuple(
        evaluate_single_memo_quality_review(review) for review in reviews
    )
    review_count = len(review_results)
    all_scores = [
        score
        for review_result in review_results
        for score in review_result.criterion_scores.values()
    ]
    aggregate_average_score = (
        sum(all_scores) / len(all_scores) if all_scores else 0.0
    )

    failing_reasons: list[str] = []
    if review_count < MINIMUM_PHASE_3_REVIEW_COUNT:
        failing_reasons.append(
            "Phase 3 quality gate requires at least "
            f"{MINIMUM_PHASE_3_REVIEW_COUNT} reviewed memos; got {review_count}."
        )
    if review_count > MAXIMUM_PHASE_3_REVIEW_COUNT:
        failing_reasons.append(
            "Phase 3 quality gate supports at most "
            f"{MAXIMUM_PHASE_3_REVIEW_COUNT} reviewed memos; got {review_count}."
        )

    memo_identifier_counts = Counter(review.memo_identifier for review in reviews)
    duplicate_memo_identifiers = sorted(
        memo_identifier
        for memo_identifier, count in memo_identifier_counts.items()
        if count > 1
    )
    if duplicate_memo_identifiers:
        failing_reasons.append(
            "Phase 3 quality gate requires distinct memo identifiers; duplicates: "
            f"{', '.join(duplicate_memo_identifiers)}."
        )

    for review, review_result in zip(reviews, review_results, strict=True):
        if not review_result.passed:
            failing_reasons.append(
                f"{review.memo_identifier} failed manual memo quality review."
            )

    return Phase3MemoQualityGateResult(
        passed=not failing_reasons,
        review_count=review_count,
        aggregate_average_score=aggregate_average_score,
        review_results=review_results,
        failing_reasons=tuple(failing_reasons),
    )


__all__ = [
    "MAXIMUM_PHASE_3_REVIEW_COUNT",
    "MINIMUM_AVERAGE_SCORE",
    "MINIMUM_CRITERION_SCORE",
    "MINIMUM_PHASE_3_REVIEW_COUNT",
    "MemoQualityGateResult",
    "PHASE_3_RUBRIC",
    "Phase3MemoQualityGateResult",
    "QUALITATIVE_ONLY_CRITERIA_UNTIL_PHASE_4",
    "evaluate_memo_quality_gate",
    "evaluate_single_memo_quality_review",
]
