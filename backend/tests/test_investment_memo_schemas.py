from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    CategoryScore,
    InvestmentMemo,
    ResearchVerdict,
)


def complete_memo_data() -> dict:
    evidence = {
        "source": "FY2026 annual report",
        "quote": "Revenue grew as retention improved.",
        "url": "https://example.com/report",
        "published_date": "2026-03-01",
    }
    observation = {
        "observation": "Retention is improving.",
        "analysis": "Improving retention supports more durable revenue.",
        "evidence": [evidence],
    }

    return {
        "company_name": "Example Corp",
        "ticker": "EXM",
        "memo_date": "2026-06-18",
        "verdict": "investable",
        "stance": "long",
        "confidence": "medium",
        "thesis": "The market underestimates the durability of growth.",
        "observation_sections": [
            {
                "title": "Business quality",
                "observations": [observation],
            }
        ],
        "adversarial_research": {
            "bear_case": [observation],
            "disconfirming_evidence": [evidence],
            "unresolved_challenges": ["Customer concentration remains unclear."],
        },
        "unknowns": {
            "open_questions": ["Can margins hold through a cycle?"],
            "data_gaps": ["Segment-level retention history is incomplete."],
        },
        "category_scores": {
            "business_quality": {"score": "strong", "weight": 0.30},
            "risk_profile": {"score": "medium", "weight": 0.20},
            "expectations_gap": {"score": "strong", "weight": 0.20},
            "variant_perception": {"score": "medium", "weight": 0.15},
            "valuation": {"score": "medium", "weight": 0.10},
            "catalyst": {"score": "weak", "weight": 0.05},
        },
        "reverse_dcf_expectations": None,
        "valuation_range": {
            "currency": "USD",
            "downside": {
                "name": "Downside",
                "intrinsic_value_per_share": 80,
                "assumptions": {"growth": "slows materially"},
            },
            "base": {
                "name": "Base",
                "intrinsic_value_per_share": 120,
                "assumptions": {"growth": "normalizes"},
            },
            "upside": {
                "name": "Upside",
                "intrinsic_value_per_share": 160,
                "assumptions": {"growth": "persists"},
            },
        },
        "monitoring_rules": [
            {
                "metric": "Net revenue retention",
                "condition": "falls below",
                "threshold": "110%",
                "action": "Revisit durability thesis.",
            }
        ],
    }


def test_valid_complete_memo_construction() -> None:
    memo = InvestmentMemo.model_validate(complete_memo_data())

    assert memo.verdict is ResearchVerdict.INVESTABLE
    assert memo.reverse_dcf_expectations is None
    assert memo.category_scores.business_quality.weight == 0.30


def test_enum_validation_rejects_unknown_values() -> None:
    data = complete_memo_data()
    data["verdict"] = "maybe"

    with pytest.raises(ValidationError):
        InvestmentMemo.model_validate(data)


def test_required_field_validation_rejects_missing_fields() -> None:
    data = complete_memo_data()
    del data["thesis"]

    with pytest.raises(ValidationError):
        InvestmentMemo.model_validate(data)


def test_fixed_category_weight_enforcement() -> None:
    data = complete_memo_data()
    data["category_scores"]["business_quality"]["weight"] = 0.25

    with pytest.raises(ValidationError):
        InvestmentMemo.model_validate(data)


def test_missing_category_score_is_rejected() -> None:
    data = complete_memo_data()
    del data["category_scores"]["catalyst"]

    with pytest.raises(ValidationError):
        InvestmentMemo.model_validate(data)


def test_overall_score_field_is_not_allowed() -> None:
    data = complete_memo_data()
    data["overall_score"] = 87

    with pytest.raises(ValidationError):
        InvestmentMemo.model_validate(data)


def test_category_score_contains_no_analysis_field() -> None:
    score_data = deepcopy(complete_memo_data()["category_scores"]["business_quality"])
    score_data["analysis"] = "This belongs in observations, not the score label."

    with pytest.raises(ValidationError):
        CategoryScore.model_validate(score_data)
