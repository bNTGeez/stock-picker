from copy import deepcopy

import pytest

from backend.models.schemas import EvidenceItem, InvestmentMemo
from backend.services.evidence_validator import (
    EvidenceValidationError,
    SourceDocument,
    locate_evidence_item,
    validate_memo_evidence,
)
from backend.tests.test_manual_memo_generator import complete_memo_data


def source_documents() -> list[SourceDocument]:
    return [
        SourceDocument(
            source="FY2026 Form 10-K",
            text=(
                "Revenue grew as retention improved. A small number of customers "
                "represent a significant share of revenue."
            ),
        ),
        SourceDocument(
            source="Q1 2026 earnings call",
            text="Management said retention remained strong.",
        ),
    ]


def test_exact_quote_match() -> None:
    evidence = EvidenceItem(
        source="FY2026 Form 10-K",
        quote="Revenue grew as retention improved.",
    )
    document = SourceDocument(
        source="FY2026 Form 10-K",
        text="Intro. Revenue grew as retention improved. Outro.",
    )

    located = locate_evidence_item(evidence, [document])

    assert located.normalized_quote == "Revenue grew as retention improved."
    assert located.located_start_offset == 7
    assert located.located_end_offset == 42
    assert located.match_score == 1.0


def test_whitespace_normalized_match() -> None:
    evidence = EvidenceItem(
        source="FY2026 Form 10-K",
        quote="Revenue grew as retention improved.",
    )
    document = SourceDocument(
        source="FY2026 Form 10-K",
        text="Revenue grew as\n\nretention   improved.",
    )

    located = locate_evidence_item(evidence, [document])

    assert located.normalized_quote == "Revenue grew as retention improved."
    assert located.match_score == 1.0
    assert located.located_start_offset == 0
    assert located.located_end_offset == len(located.normalized_quote)


def test_fuzzy_accepted_match() -> None:
    evidence = EvidenceItem(
        source="FY2026 Form 10-K",
        quote="Revenue grew as retentin improved.",
    )
    document = SourceDocument(
        source="FY2026 Form 10-K",
        text="Revenue grew as retention improved.",
    )

    located = locate_evidence_item(evidence, [document], threshold=0.90)

    assert located.match_score is not None
    assert 0.90 <= located.match_score < 1.0
    assert located.located_start_offset == 0


def test_fuzzy_rejected_match() -> None:
    evidence = EvidenceItem(
        source="FY2026 Form 10-K",
        quote="Revenue grew as retentin improved.",
    )
    document = SourceDocument(
        source="FY2026 Form 10-K",
        text="Revenue grew as retention improved.",
    )

    with pytest.raises(EvidenceValidationError, match="above threshold"):
        locate_evidence_item(evidence, [document], threshold=0.99)


def test_fabricated_quote_rejection() -> None:
    evidence = EvidenceItem(
        source="FY2026 Form 10-K",
        quote="Management announced a guaranteed margin expansion plan.",
    )

    with pytest.raises(EvidenceValidationError, match="could not be located"):
        locate_evidence_item(evidence, source_documents(), threshold=0.90)


@pytest.mark.parametrize(
    ("source_text", "quote"),
    [
        (
            "Revenue grew 5% as retention improved.",
            "Revenue grew 50% as retention improved.",
        ),
        (
            "Operating margin was 12.4% as scale improved.",
            "Operating margin was 42.4% as scale improved.",
        ),
        (
            "Revenue increased 5% as retention improved.",
            "Revenue decreased 5% as retention improved.",
        ),
        (
            "ACME revenue grew 5% as retention improved.",
            "ANME revenue grew 5% as retention improved.",
        ),
    ],
)
def test_high_similarity_material_changes_are_rejected(
    source_text: str,
    quote: str,
) -> None:
    evidence = EvidenceItem(source="FY2026 Form 10-K", quote=quote)
    document = SourceDocument(source="FY2026 Form 10-K", text=source_text)

    with pytest.raises(EvidenceValidationError, match="could not be located"):
        locate_evidence_item(evidence, [document], threshold=0.95)


def test_valid_memo_receives_offsets_and_match_scores() -> None:
    memo = InvestmentMemo.model_validate(complete_memo_data())

    located = validate_memo_evidence(
        memo,
        source_documents=source_documents(),
        threshold=0.95,
    )

    observation_evidence = located.observations[0].evidence[0]
    assert observation_evidence.normalized_quote == (
        "Revenue grew as retention improved."
    )
    assert observation_evidence.located_start_offset == 0
    assert observation_evidence.located_end_offset == 35
    assert observation_evidence.match_score == 1.0
    assert (
        located.adversarial_research.evidence_against_variant_view[0].match_score
        == 1.0
    )
    assert located.monitoring_rules.green_flags[0].evidence[0].match_score == 1.0


def test_insufficient_evidence_can_be_represented_without_inventing_conviction() -> None:
    data = deepcopy(complete_memo_data())
    data["research_verdict"] = "Insufficient Evidence"
    data["investment_stance"] = "Neutral"
    data["confidence"] = "Low"
    data["unknowns"]["data_gaps"].append("Only narrow excerpts were supplied.")
    data["recommended_next_step"] = (
        "Collect more source material before forming a higher-conviction view."
    )

    memo = InvestmentMemo.model_validate(data)
    located = validate_memo_evidence(
        memo,
        source_documents=source_documents(),
        threshold=0.95,
    )

    assert located.research_verdict.value == "Insufficient Evidence"
    assert located.confidence.value == "Low"
    assert located.investment_stance.value == "Neutral"
    assert located.observations[0].evidence[0].match_score == 1.0
