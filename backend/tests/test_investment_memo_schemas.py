from copy import deepcopy

import pytest
from pydantic import ValidationError

from backend.models.schemas import (
    AdversarialResearchSection,
    CategoryScore,
    EvidenceItem,
    InvestmentMemo,
    InvestmentStance,
    ResearchVerdict,
)


def complete_memo_data() -> dict:
    evidence = {
        "source": "FY2026 annual report",
        "quote": "Revenue grew as retention improved.",
        "url": "https://example.com/report",
        "published_date": "2026-03-01",
    }
    risk_evidence = {
        "source": "FY2026 annual report",
        "quote": "A small number of customers represent a significant share of revenue.",
        "published_date": "2026-03-01",
    }
    observation = {
        "observation": "Retention is improving.",
        "analysis": "Improving retention supports more durable revenue.",
        "evidence": [evidence],
    }
    category_score = {
        "score": 76,
        "weight": 0.20,
        "rationale": "The score summarizes improving retention offset by concentration risk.",
    }
    valuation_scenario = {
        "label": "Base",
        "assumptions": ["Retention remains above peer levels."],
        "implied_outcome": "Durable growth supports a mid-range valuation outcome.",
        "supporting_evidence": [evidence],
    }
    monitoring_rule = {
        "trigger": "Retention remains above 110%.",
        "rationale": "Sustained retention would strengthen the durability thesis.",
        "evidence": [evidence],
    }

    return {
        "company_name": "Example Corp",
        "ticker": "EXM",
        "memo_date": "2026-06-18",
        "research_verdict": "Candidate",
        "investment_stance": "Lean Bullish",
        "confidence": "Medium",
        "category_scores": {
            "business_quality": {
                "score": 82,
                "weight": 0.30,
                "rationale": "Retention and pricing power appear above average.",
            },
            "risk_profile": {
                "score": 58,
                "weight": 0.20,
                "rationale": "Customer concentration keeps the risk profile elevated.",
            },
            "expectations_gap": category_score,
            "variant_perception": {
                "score": 80,
                "weight": 0.15,
                "rationale": "Consensus appears to underweight the retention evidence.",
            },
            "valuation": {
                "score": 64,
                "weight": 0.10,
                "rationale": "The range is favorable but not decisive without reverse DCF work.",
            },
            "catalyst": {
                "score": 55,
                "weight": 0.05,
                "rationale": "Upcoming disclosures may clarify retention durability.",
            },
        },
        "market_expectations": "Consensus expects growth to normalize over the next year.",
        "observations": [observation],
        "variant_hypothesis": "Growth durability may be stronger than consensus expects.",
        "why_consensus_may_be_wrong": (
            "Consensus may extrapolate cyclical slowdown while retention data points "
            "to more durable demand."
        ),
        "adversarial_research": {
            "bull_case": "Retention and pricing power support durable growth.",
            "bear_case": "Customer concentration could overwhelm retention improvements.",
            "key_disagreement": "Whether retention durability offsets concentration risk.",
            "evidence_for_variant_view": [evidence],
            "evidence_against_variant_view": [risk_evidence],
            "rebuttal": "The retention evidence is direct, while concentration risk still needs sizing.",
            "disconfirming_evidence": [
                "Retention below 100% or evidence that growth was pulled forward."
            ],
            "final_synthesis": "The variant view is plausible but still needs monitoring.",
        },
        "unknowns": {
            "open_questions": ["Can margins hold through a cycle?"],
            "data_gaps": ["Segment-level retention history is incomplete."],
        },
        "top_risks": [
            "Customer concentration",
            "Multiple compression",
            "Execution risk",
        ],
        "valuation_range": {
            "bear": {
                "label": "Bear",
                "assumptions": ["Retention falls below 100%."],
                "implied_outcome": "Growth slows and the valuation case weakens.",
                "supporting_evidence": [risk_evidence],
            },
            "base": valuation_scenario,
            "bull": {
                "label": "Bull",
                "assumptions": ["Retention remains strong and margins expand."],
                "implied_outcome": "Growth durability supports upside to expectations.",
                "supporting_evidence": [evidence],
            },
        },
        "reverse_dcf_expectations": None,
        "monitoring_rules": {
            "green_flags": [monitoring_rule],
            "yellow_flags": [
                {
                    "trigger": "Retention slips but remains above 100%.",
                    "rationale": "This would require closer monitoring of the thesis.",
                    "evidence": [],
                }
            ],
            "red_flags": [
                {
                    "trigger": "Retention falls below 100%.",
                    "rationale": "This would materially damage the variant hypothesis.",
                    "evidence": [],
                }
            ],
        },
        "recommended_next_step": "Research further before any capital allocation decision.",
    }


def test_valid_complete_memo_construction() -> None:
    memo = InvestmentMemo.model_validate(complete_memo_data())

    assert memo.research_verdict is ResearchVerdict.CANDIDATE
    assert memo.investment_stance is InvestmentStance.LEAN_BULLISH
    assert memo.reverse_dcf_expectations is None
    assert memo.category_scores.business_quality.weight == 0.30
    assert memo.valuation_range.bear.label == "Bear"


def test_research_verdict_values_match_plan() -> None:
    assert [verdict.value for verdict in ResearchVerdict] == [
        "Insufficient Evidence",
        "Reject",
        "Watchlist",
        "Research Further",
        "Candidate",
        "High Conviction Candidate",
    ]


def test_investment_stance_values_match_plan() -> None:
    assert [stance.value for stance in InvestmentStance] == [
        "Bearish",
        "Lean Bearish",
        "Neutral",
        "Lean Bullish",
        "Bullish",
    ]


def test_enum_validation_rejects_unknown_values() -> None:
    data = complete_memo_data()
    data["research_verdict"] = "investable"

    with pytest.raises(ValidationError):
        InvestmentMemo.model_validate(data)


@pytest.mark.parametrize(
    "field_name",
    [
        "research_verdict",
        "investment_stance",
        "confidence",
        "category_scores",
        "market_expectations",
        "observations",
        "variant_hypothesis",
        "why_consensus_may_be_wrong",
        "adversarial_research",
        "unknowns",
        "top_risks",
        "valuation_range",
        "reverse_dcf_expectations",
        "monitoring_rules",
        "recommended_next_step",
    ],
)
def test_required_top_level_fields_are_enforced(field_name: str) -> None:
    data = complete_memo_data()
    del data[field_name]

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


def test_category_score_requires_numeric_score_and_rationale() -> None:
    score_data = deepcopy(complete_memo_data()["category_scores"]["business_quality"])
    del score_data["rationale"]

    with pytest.raises(ValidationError):
        CategoryScore.model_validate(score_data)

    score_data = deepcopy(complete_memo_data()["category_scores"]["business_quality"])
    score_data["score"] = "strong"

    with pytest.raises(ValidationError):
        CategoryScore.model_validate(score_data)


def test_overall_score_fields_are_not_allowed() -> None:
    for field_name in (
        "overall_score",
        "composite_score",
        "weighted_aggregate_score",
    ):
        data = complete_memo_data()
        data[field_name] = 87

        with pytest.raises(ValidationError):
            InvestmentMemo.model_validate(data)

    for field_name in (
        "overall_score",
        "composite_score",
        "weighted_aggregate_score",
    ):
        data = complete_memo_data()
        data["category_scores"][field_name] = 87

        with pytest.raises(ValidationError):
            InvestmentMemo.model_validate(data)


def test_partial_evidence_location_metadata_is_rejected() -> None:
    data = {
        "source": "FY2026 annual report",
        "quote": "Revenue grew as retention improved.",
        "normalized_quote": "Revenue grew as retention improved.",
    }

    with pytest.raises(ValidationError):
        EvidenceItem.model_validate(data)


def test_full_adversarial_section_is_required() -> None:
    adversarial_data = deepcopy(complete_memo_data()["adversarial_research"])

    section = AdversarialResearchSection.model_validate(adversarial_data)

    assert section.bull_case
    assert section.evidence_for_variant_view
    assert section.final_synthesis

    del adversarial_data["rebuttal"]

    with pytest.raises(ValidationError):
        AdversarialResearchSection.model_validate(adversarial_data)


def test_valuation_range_requires_bear_base_bull_labels() -> None:
    data = complete_memo_data()
    data["valuation_range"]["bear"]["label"] = "Downside"

    with pytest.raises(ValidationError):
        InvestmentMemo.model_validate(data)
