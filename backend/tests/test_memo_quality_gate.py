import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    ManualMemoQualityReview,
    MemoEvidenceValidationStatus,
    MemoQualityCriterion,
)
from backend.services.memo_quality_gate import (
    QUALITATIVE_ONLY_CRITERIA_UNTIL_PHASE_4,
    evaluate_memo_quality_gate,
)


def review_data(
    scores: dict[MemoQualityCriterion, int] | None = None,
    evidence_validation_status: MemoEvidenceValidationStatus = (
        MemoEvidenceValidationStatus.VALIDATED
    ),
) -> dict:
    criterion_scores = scores or {
        criterion: 4 for criterion in MemoQualityCriterion
    }
    return {
        "memo_identifier": "EXM-2026-06-18",
        "reviewer": "Human Reviewer",
        "criterion_scores": [
            {
                "criterion": criterion.value,
                "score": score,
                "notes": f"Manual review note for {criterion.value}.",
            }
            for criterion, score in criterion_scores.items()
        ],
        "evidence_validation_status": evidence_validation_status.value,
        "evidence_notes": "All memo evidence quotes were validated by Phase 2.",
        "overall_notes": "Memo is good enough to proceed.",
    }


def build_review(
    scores: dict[MemoQualityCriterion, int] | None = None,
    evidence_validation_status: MemoEvidenceValidationStatus = (
        MemoEvidenceValidationStatus.VALIDATED
    ),
) -> ManualMemoQualityReview:
    return ManualMemoQualityReview.model_validate(
        review_data(
            scores=scores,
            evidence_validation_status=evidence_validation_status,
        )
    )


def test_passing_review_passes_gate() -> None:
    result = evaluate_memo_quality_gate(build_review())

    assert result.passed is True
    assert result.average_score == 4.0
    assert result.failing_reasons == ()


def test_failing_average_score_fails_gate() -> None:
    scores = {criterion: 3 for criterion in MemoQualityCriterion}
    scores[MemoQualityCriterion.REAL_VARIANT_HYPOTHESIS] = 5

    result = evaluate_memo_quality_gate(build_review(scores=scores))

    assert result.passed is False
    assert result.average_score == 3.25
    assert result.failing_reasons == ("Average score 3.25 is below 4.0.",)


def test_failing_individual_criterion_fails_gate() -> None:
    scores = {criterion: 5 for criterion in MemoQualityCriterion}
    scores[MemoQualityCriterion.OPPOSING_CASE] = 2

    result = evaluate_memo_quality_gate(build_review(scores=scores))

    assert result.passed is False
    assert result.average_score == 4.625
    assert result.failing_reasons == ("opposing_case score 2 is below 3.",)


@pytest.mark.parametrize(
    "status",
    [
        MemoEvidenceValidationStatus.UNVALIDATED,
        MemoEvidenceValidationStatus.FABRICATED,
    ],
)
def test_failing_evidence_validation_status_fails_gate(
    status: MemoEvidenceValidationStatus,
) -> None:
    result = evaluate_memo_quality_gate(
        build_review(evidence_validation_status=status)
    )

    assert result.passed is False
    assert result.failing_reasons == (
        f"Evidence validation status must be validated; got {status.value}.",
    )


def test_review_requires_each_rubric_criterion_once() -> None:
    data = review_data()
    data["criterion_scores"] = data["criterion_scores"][:-1]

    with pytest.raises(ValidationError, match="missing criteria"):
        ManualMemoQualityReview.model_validate(data)

    data = review_data()
    data["criterion_scores"][-1]["criterion"] = data["criterion_scores"][0][
        "criterion"
    ]

    with pytest.raises(ValidationError, match="duplicate criteria"):
        ManualMemoQualityReview.model_validate(data)


def test_priced_in_criterion_is_qualitative_only_until_phase_4() -> None:
    assert QUALITATIVE_ONLY_CRITERIA_UNTIL_PHASE_4 == (
        MemoQualityCriterion.PRICED_IN_EXPLANATION,
    )
