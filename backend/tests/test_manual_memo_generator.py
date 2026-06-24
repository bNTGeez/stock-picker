import json

import pytest

from backend.models.schemas import InvestmentMemo
from backend.services.manual_memo_generator import (
    CompanyMetadata,
    InvalidMemoEvidenceError,
    InvalidMemoJSONError,
    InvalidMemoSchemaError,
    ManualMemoGenerator,
    ManualMemoRequest,
    ManualSourceExcerpt,
    REASONING_CHAIN,
    build_manual_memo_prompt,
    parse_investment_memo_response,
    reverse_dcf_expectations_from_request,
    source_documents_from_request,
)
from backend.services.reverse_dcf import (
    ReverseDCFInputs,
    ReverseDCFScenarioValues,
    ReverseDCFTerminalAssumptions,
)


class StubLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


def complete_memo_data() -> dict:
    evidence = {
        "source_type": "10-K Item 1",
        "source_tier": 1,
        "source_id": "FY2026 Form 10-K",
        "quote": "Revenue grew as retention improved.",
    }
    transcript_evidence = {
        "source_type": "earnings_transcript",
        "source_tier": 2,
        "source_id": "Q1 2026 earnings call",
        "quote": "Management said retention remained strong.",
    }
    risk_evidence = {
        "source_type": "10-K Item 1A",
        "source_tier": 1,
        "source_id": "FY2026 Form 10-K",
        "quote": "A small number of customers represent a significant share of revenue.",
    }
    observation = {
        "statement": "Retention is improving.",
        "supporting_evidence": [evidence, transcript_evidence],
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
        "research_verdict": "Research Further",
        "investment_stance": "Neutral",
        "confidence": "Medium",
        "category_scores": {
            "business_quality": {
                "score": 78,
                "weight": 0.30,
                "rationale": "Retention improvement supports business quality.",
            },
            "risk_profile": {
                "score": 52,
                "weight": 0.20,
                "rationale": "Customer concentration remains a material risk.",
            },
            "expectations_gap": {
                "score": 70,
                "weight": 0.20,
                "rationale": "Consensus expects normalization despite retention evidence.",
            },
            "variant_perception": {
                "score": 68,
                "weight": 0.15,
                "rationale": "The variant view is plausible but still incomplete.",
            },
            "valuation": {
                "score": 60,
                "weight": 0.10,
                "rationale": "The valuation range is not enough without reverse DCF work.",
            },
            "catalyst": {
                "score": 50,
                "weight": 0.05,
                "rationale": "More disclosures are needed to force convergence.",
            },
        },
        "market_expectations": "Consensus expects growth to normalize.",
        "observations": {"observations": [observation]},
        "variant_hypothesis": "Growth may be more durable than consensus expects.",
        "why_consensus_may_be_wrong": (
            "Consensus may be over-extrapolating near-term normalization and "
            "underweighting retention evidence."
        ),
        "adversarial_research": {
            "bull_case": "Retention improvement supports durable revenue growth.",
            "bear_case": "Customer concentration could offset retention gains.",
            "key_disagreement": "Whether retention durability offsets concentration risk.",
            "evidence_for_variant_view": [evidence, transcript_evidence],
            "evidence_against_variant_view": [risk_evidence],
            "rebuttal": "Retention evidence is current, but concentration still needs sizing.",
            "disconfirming_evidence": [
                "Retention below 100% or weaker renewal disclosures."
            ],
            "final_synthesis": "The variant view deserves more research, not conviction yet.",
        },
        "unknowns": {
            "unknowns": [
                "Can margins hold through a cycle?",
                "Segment-level retention history is incomplete.",
            ],
        },
        "top_risks": ["Customer concentration", "Multiple compression"],
        "valuation_range": {
            "bear": {
                "label": "Bear",
                "assumptions": ["Retention falls below 100%."],
                "implied_outcome": "Growth slows and the valuation case weakens.",
                "supporting_evidence": [risk_evidence],
            },
            "base": {
                "label": "Base",
                "assumptions": ["Retention remains above peer levels."],
                "implied_outcome": "Durable growth supports a mid-range outcome.",
                "supporting_evidence": [evidence],
            },
            "bull": {
                "label": "Bull",
                "assumptions": ["Retention remains strong and margins expand."],
                "implied_outcome": "Growth durability supports upside to expectations.",
                "supporting_evidence": [evidence, transcript_evidence],
            },
        },
        "reverse_dcf_expectations": None,
        "monitoring_rules": {
            "green_flags": [monitoring_rule],
            "yellow_flags": [
                {
                    "trigger": "Retention slips but remains above 100%.",
                    "rationale": "This would require closer monitoring.",
                    "evidence": [],
                }
            ],
            "red_flags": [
                {
                    "trigger": "Retention falls below 100%.",
                    "rationale": "This would materially damage the variant view.",
                    "evidence": [],
                }
            ],
        },
        "recommended_next_step": "Research further before any capital allocation decision.",
    }


def manual_request() -> ManualMemoRequest:
    return ManualMemoRequest(
        company=CompanyMetadata(
            company_name="Example Corp",
            ticker="EXM",
            memo_date="2026-06-18",
            currency="USD",
            market_price=100,
        ),
        ten_k_excerpts=[
            ManualSourceExcerpt(
                source="FY2026 Form 10-K",
                section="Business",
                text=(
                    "Revenue grew as retention improved. A small number of "
                    "customers represent a significant share of revenue."
                ),
                published_date="2026-03-01",
            )
        ],
        transcript_excerpts=[
            ManualSourceExcerpt(
                source="Q1 2026 earnings call",
                text="Management said retention remained strong.",
                published_date="2026-05-01",
            )
        ],
        consensus_notes=["Consensus expects growth to normalize."],
    )


def reverse_dcf_inputs() -> ReverseDCFInputs:
    return ReverseDCFInputs(
        share_price=20,
        shares_outstanding=100,
        net_debt=200,
        current_revenue=500,
        fcf_margin_assumptions=ReverseDCFScenarioValues(
            low=0.18,
            mid=0.20,
            high=0.22,
        ),
        wacc_range=ReverseDCFScenarioValues(
            low=0.08,
            mid=0.10,
            high=0.12,
        ),
        terminal_assumptions=ReverseDCFTerminalAssumptions(
            projection_years=5,
            terminal_growth_rate=ReverseDCFScenarioValues(
                low=0.02,
                mid=0.025,
                high=0.03,
            ),
            revenue_cagr_assumptions=ReverseDCFScenarioValues(
                low=0.04,
                mid=0.07,
                high=0.10,
            ),
        ),
    )


def test_stub_llm_response_parses_into_investment_memo() -> None:
    stub = StubLLM(json.dumps(complete_memo_data()))
    generator = ManualMemoGenerator(stub)

    memo = generator.generate(manual_request())

    assert isinstance(memo, InvestmentMemo)
    assert memo.company_name == "Example Corp"
    assert memo.ticker == "EXM"
    assert memo.research_verdict.value == "Research Further"
    assert memo.valuation_range.bull.label == "Bull"
    assert memo.reverse_dcf_expectations is None
    assert memo.observations.observations[0].supporting_evidence[0].normalized_quote == (
        "Revenue grew as retention improved."
    )
    assert (
        memo.observations.observations[0].supporting_evidence[0].located_start_offset
        == 0
    )
    assert (
        memo.observations.observations[0].supporting_evidence[0].located_end_offset
        == 35
    )
    assert memo.observations.observations[0].supporting_evidence[0].match_score == 1.0
    assert stub.prompts


def test_generator_populates_reverse_dcf_from_deterministic_output() -> None:
    data = complete_memo_data()
    data["reverse_dcf_expectations"] = {
        "implied_revenue_cagr_low": 0.0,
        "implied_revenue_cagr_mid": 0.0,
        "implied_revenue_cagr_high": 0.0,
        "implied_fcf_margin_low": 0.0,
        "implied_fcf_margin_mid": 0.0,
        "implied_fcf_margin_high": 0.0,
    }
    request = manual_request().model_copy(
        update={"reverse_dcf_inputs": reverse_dcf_inputs()}
    )
    stub = StubLLM(json.dumps(data))
    generator = ManualMemoGenerator(stub)

    memo = generator.generate(request)
    expected = reverse_dcf_expectations_from_request(request)

    assert memo.reverse_dcf_expectations == expected
    assert expected is not None
    assert expected.implied_revenue_cagr_mid == 0.141


def test_invalid_json_fails_clearly() -> None:
    with pytest.raises(InvalidMemoJSONError, match="not valid JSON"):
        parse_investment_memo_response("{not-json")


def test_schema_invalid_json_fails_clearly() -> None:
    with pytest.raises(InvalidMemoSchemaError, match="InvestmentMemo schema"):
        parse_investment_memo_response(json.dumps({"company_name": "Example Corp"}))


def test_unlocatable_evidence_fails_clearly() -> None:
    data = complete_memo_data()
    data["observations"]["observations"][0]["supporting_evidence"][0][
        "quote"
    ] = "Fabricated growth proof."

    with pytest.raises(InvalidMemoEvidenceError, match="could not be located"):
        parse_investment_memo_response(
            json.dumps(data),
            source_documents=source_documents_from_request(manual_request()),
        )


def test_prompt_includes_corrected_schema_and_reasoning_chain() -> None:
    prompt = build_manual_memo_prompt(manual_request())

    assert REASONING_CHAIN in prompt
    assert "Return only valid JSON" in prompt
    assert "InvestmentMemo JSON schema" in prompt
    assert "research_verdict" in prompt
    assert "investment_stance" in prompt
    assert "market_expectations" in prompt
    assert "variant_hypothesis" in prompt
    assert "why_consensus_may_be_wrong" in prompt
    assert "evidence_for_variant_view" in prompt
    assert "evidence_against_variant_view" in prompt
    assert "final_synthesis" in prompt
    assert "Bear, Base, and Bull" in prompt
    assert "Do not perform reverse DCF calculations" in prompt
    assert "reverse_dcf_expectations to null" in prompt
    assert "overall score" in prompt
    assert "composite score" in prompt
    assert "weighted aggregate" in prompt
    assert "fabricated or unlocatable quotes are invalid" in prompt
    assert "Insufficient Evidence" in prompt


def test_prompt_supplies_only_deterministic_reverse_dcf_outputs() -> None:
    request = manual_request().model_copy(
        update={"reverse_dcf_inputs": reverse_dcf_inputs()}
    )

    prompt = build_manual_memo_prompt(request)

    assert "Deterministic reverse DCF outputs" in prompt
    assert "implied_revenue_cagr_mid" in prompt
    assert "0.141" in prompt
    assert "do not recalculate" in prompt
    assert "Set reverse_dcf_expectations to null" not in prompt
    assert "shares_outstanding" not in prompt
