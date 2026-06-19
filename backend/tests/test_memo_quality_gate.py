import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    ManualMemoQualityReview,
    MemoEvidenceValidationStatus,
    MemoQualityCriterion,
)
from backend.services.memo_quality_gate import (
    MAXIMUM_PHASE_3_REVIEW_COUNT,
    MINIMUM_PHASE_3_REVIEW_COUNT,
    QUALITATIVE_ONLY_CRITERIA_UNTIL_PHASE_4,
    evaluate_memo_quality_gate,
    evaluate_single_memo_quality_review,
)


def review_data(
    memo_identifier: str = "EXM-2026-06-18",
    scores: dict[MemoQualityCriterion, int] | None = None,
    evidence_validation_status: MemoEvidenceValidationStatus = (
        MemoEvidenceValidationStatus.VALIDATED
    ),
) -> dict:
    criterion_scores = scores or {
        criterion: 4 for criterion in MemoQualityCriterion
    }
    return {
        "memo_identifier": memo_identifier,
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
    memo_identifier: str = "EXM-2026-06-18",
    scores: dict[MemoQualityCriterion, int] | None = None,
    evidence_validation_status: MemoEvidenceValidationStatus = (
        MemoEvidenceValidationStatus.VALIDATED
    ),
) -> ManualMemoQualityReview:
    return ManualMemoQualityReview.model_validate(
        review_data(
            memo_identifier=memo_identifier,
            scores=scores,
            evidence_validation_status=evidence_validation_status,
        )
    )


def build_reviews(
    count: int = MINIMUM_PHASE_3_REVIEW_COUNT,
) -> list[ManualMemoQualityReview]:
    return [
        build_review(memo_identifier=f"EXM-{index}-2026-06-18")
        for index in range(count)
    ]


def test_passing_review_passes_gate() -> None:
    result = evaluate_single_memo_quality_review(build_review())

    assert result.passed is True
    assert result.average_score == 4.0
    assert result.failing_reasons == ()


def test_failing_average_score_fails_gate() -> None:
    scores = {criterion: 3 for criterion in MemoQualityCriterion}
    scores[MemoQualityCriterion.REAL_VARIANT_HYPOTHESIS] = 5

    result = evaluate_single_memo_quality_review(build_review(scores=scores))

    assert result.passed is False
    assert result.average_score == 3.25
    assert result.failing_reasons == ("Average score 3.25 is below 4.0.",)


def test_failing_individual_criterion_fails_gate() -> None:
    scores = {criterion: 5 for criterion in MemoQualityCriterion}
    scores[MemoQualityCriterion.OPPOSING_CASE] = 2

    result = evaluate_single_memo_quality_review(build_review(scores=scores))

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
    result = evaluate_single_memo_quality_review(
        build_review(evidence_validation_status=status)
    )

    assert result.passed is False
    assert result.failing_reasons == (
        f"Evidence validation status must be validated; got {status.value}.",
    )


def test_phase_3_quality_gate_requires_five_to_ten_reviewed_memos() -> None:
    too_few_reviews = build_reviews(1)

    result = evaluate_memo_quality_gate(too_few_reviews)

    assert result.passed is False
    assert result.review_count == 1
    assert result.failing_reasons == (
        "Phase 3 quality gate requires at least 5 reviewed memos; got 1.",
    )

    too_many_reviews = build_reviews(MAXIMUM_PHASE_3_REVIEW_COUNT + 1)

    result = evaluate_memo_quality_gate(too_many_reviews)

    assert result.passed is False
    assert result.review_count == 11
    assert result.failing_reasons == (
        "Phase 3 quality gate supports at most 10 reviewed memos; got 11.",
    )


def test_phase_3_quality_gate_rejects_single_review_object() -> None:
    with pytest.raises(TypeError, match="expects a sequence of 5-10"):
        evaluate_memo_quality_gate(build_review())  # type: ignore[arg-type]


def test_phase_3_quality_gate_passes_complete_review_set() -> None:
    result = evaluate_memo_quality_gate(build_reviews())

    assert result.passed is True
    assert result.review_count == MINIMUM_PHASE_3_REVIEW_COUNT
    assert result.aggregate_average_score == 4.0
    assert len(result.review_results) == MINIMUM_PHASE_3_REVIEW_COUNT
    assert result.failing_reasons == ()


def test_phase_3_quality_gate_fails_when_any_review_fails() -> None:
    reviews = build_reviews()
    scores = {criterion: 4 for criterion in MemoQualityCriterion}
    scores[MemoQualityCriterion.EVIDENCE_SUPPORT] = 2
    reviews[2] = build_review(
        memo_identifier="EXM-2-2026-06-18",
        scores=scores,
    )

    result = evaluate_memo_quality_gate(reviews)

    assert result.passed is False
    assert result.review_results[2].passed is False
    assert result.failing_reasons == (
        "EXM-2-2026-06-18 failed manual memo quality review.",
    )


def test_phase_3_quality_gate_requires_distinct_memo_identifiers() -> None:
    reviews = build_reviews()
    reviews[-1] = build_review(memo_identifier=reviews[0].memo_identifier)

    result = evaluate_memo_quality_gate(reviews)

    assert result.passed is False
    assert result.failing_reasons == (
        "Phase 3 quality gate requires distinct memo identifiers; duplicates: "
        "EXM-0-2026-06-18.",
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
