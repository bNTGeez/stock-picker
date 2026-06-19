"""Manual investment memo generation service."""

from __future__ import annotations

import json
from datetime import date
from typing import Protocol

from pydantic import Field, ValidationError

from backend.models.schemas import InvestmentMemo, StrictSchema


REASONING_CHAIN = (
    "Evidence -> Observations -> Market Expectations -> Variant Hypothesis -> "
    "Adversarial Research Reasoning -> Research Verdict -> Investment Stance"
)


class ManualMemoGenerationError(ValueError):
    """Base error for manual memo generation failures."""


class InvalidMemoJSONError(ManualMemoGenerationError):
    """Raised when the LLM response is not valid JSON."""


class InvalidMemoSchemaError(ManualMemoGenerationError):
    """Raised when the LLM response does not match InvestmentMemo."""


class ManualMemoLLM(Protocol):
    """Minimal LLM interface for easy test stubbing."""

    def generate(self, prompt: str) -> str:
        """Return the raw model response for a prompt."""
        ...


class CompanyMetadata(StrictSchema):
    """Company facts supplied by the operator."""

    company_name: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    memo_date: date
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = Field(default=None, min_length=1, max_length=3)
    market_price: float | None = Field(default=None, ge=0)
    notes: str | None = None


class ManualSourceExcerpt(StrictSchema):
    """Source text supplied directly by the operator."""

    source: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    section: str | None = None
    published_date: date | None = None


class ManualMemoRequest(StrictSchema):
    """Inputs for manual memo generation."""

    company: CompanyMetadata
    ten_k_excerpts: list[ManualSourceExcerpt] = Field(..., min_length=1)
    transcript_excerpts: list[ManualSourceExcerpt] = Field(..., min_length=1)
    consensus_notes: list[str] = Field(default_factory=list)


class ManualMemoGenerator:
    """Generate an InvestmentMemo from manually supplied source material."""

    def __init__(self, llm: ManualMemoLLM) -> None:
        self._llm = llm

    def generate(self, request: ManualMemoRequest) -> InvestmentMemo:
        prompt = build_manual_memo_prompt(request)
        response = self._llm.generate(prompt)
        return parse_investment_memo_response(response)


def build_manual_memo_prompt(request: ManualMemoRequest) -> str:
    """Build the constrained prompt for the manual research copilot."""

    memo_schema = json.dumps(InvestmentMemo.model_json_schema(), indent=2)
    request_json = request.model_dump_json(indent=2)

    return f"""You are a manual investment research copilot.

Return only valid JSON. Do not include markdown, prose, comments, or code fences.
The JSON object must match the InvestmentMemo schema exactly.

Use only the company metadata, local 10-K excerpts, local transcript excerpts, and
optional consensus notes supplied below. Do not use outside knowledge or live
external services.

Preserve this reasoning chain in the memo:
{REASONING_CHAIN}

Reflect the chain in the InvestmentMemo fields:
- Evidence: source-backed EvidenceItem entries using the supplied excerpts.
- Observations: ObservationItem analysis grouped into observation_sections.
- Market Expectations: what consensus notes and market-implied inputs appear to
  assume; capture this in observation_sections and expectations_gap scoring.
- Variant Hypothesis: the thesis that differs from those expectations.
- Adversarial Research Reasoning: bear case, disconfirming evidence, unresolved
  challenges, and unknowns.
- Research Verdict: verdict and confidence.
- Investment Stance: stance and monitoring rules.

Do not perform reverse DCF calculations. Set reverse_dcf_expectations to null
unless explicit reverse DCF outputs are supplied in the manual inputs. Set
valuation_range to null unless explicit downside/base/upside valuation outputs
are supplied in the manual inputs. Do not add an overall score.

InvestmentMemo JSON schema:
{memo_schema}

Manual inputs:
{request_json}
"""


def parse_investment_memo_response(response: str) -> InvestmentMemo:
    """Parse an LLM response into InvestmentMemo with clear failure modes."""

    try:
        payload = json.loads(response)
    except json.JSONDecodeError as error:
        raise InvalidMemoJSONError(
            "LLM response was not valid JSON: "
            f"{error.msg} at line {error.lineno}, column {error.colno}"
        ) from error

    try:
        return InvestmentMemo.model_validate(payload)
    except ValidationError as error:
        raise InvalidMemoSchemaError(
            "LLM response did not match InvestmentMemo schema: "
            f"{error.errors(include_url=False)}"
        ) from error


__all__ = [
    "CompanyMetadata",
    "InvalidMemoJSONError",
    "InvalidMemoSchemaError",
    "ManualMemoGenerationError",
    "ManualMemoGenerator",
    "ManualMemoLLM",
    "ManualMemoRequest",
    "ManualSourceExcerpt",
    "REASONING_CHAIN",
    "build_manual_memo_prompt",
    "parse_investment_memo_response",
]
