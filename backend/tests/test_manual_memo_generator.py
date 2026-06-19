import json

import pytest

from backend.models.schemas import InvestmentMemo
from backend.services.manual_memo_generator import (
    CompanyMetadata,
    InvalidMemoJSONError,
    InvalidMemoSchemaError,
    ManualMemoGenerator,
    ManualMemoRequest,
    ManualSourceExcerpt,
    REASONING_CHAIN,
    build_manual_memo_prompt,
    parse_investment_memo_response,
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
        "source": "FY2026 Form 10-K",
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
                "title": "Evidence and observations",
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
        "valuation_range": None,
        "monitoring_rules": [
            {
                "metric": "Net revenue retention",
                "condition": "falls below",
                "threshold": "110%",
                "action": "Revisit durability thesis.",
            }
        ],
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
                text="Revenue grew as retention improved.",
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


def test_stub_llm_response_parses_into_investment_memo() -> None:
    stub = StubLLM(json.dumps(complete_memo_data()))
    generator = ManualMemoGenerator(stub)

    memo = generator.generate(manual_request())

    assert isinstance(memo, InvestmentMemo)
    assert memo.company_name == "Example Corp"
    assert memo.ticker == "EXM"
    assert memo.valuation_range is None
    assert stub.prompts


def test_invalid_json_fails_clearly() -> None:
    with pytest.raises(InvalidMemoJSONError, match="not valid JSON"):
        parse_investment_memo_response("{not-json")


def test_schema_invalid_json_fails_clearly() -> None:
    with pytest.raises(InvalidMemoSchemaError, match="InvestmentMemo schema"):
        parse_investment_memo_response(json.dumps({"company_name": "Example Corp"}))


def test_prompt_includes_reasoning_chain() -> None:
    prompt = build_manual_memo_prompt(manual_request())

    assert REASONING_CHAIN in prompt
    assert "Return only valid JSON" in prompt
    assert "InvestmentMemo JSON schema" in prompt
    assert "Do not perform reverse DCF calculations" in prompt
    assert "valuation_range to null" in prompt
