"""Manual investment memo generation service."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from typing import Protocol

from pydantic import Field, ValidationError

from backend.models.schemas import InvestmentMemo, StrictSchema
from backend.services.evidence_validator import (
    EvidenceValidationError,
    SourceDocument,
    validate_memo_evidence,
)


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


class InvalidMemoEvidenceError(ManualMemoGenerationError):
    """Raised when memo evidence cannot be located in supplied sources."""


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
        return parse_investment_memo_response(
            response,
            source_documents=source_documents_from_request(request),
        )


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
- Evidence: source-backed EvidenceItem entries using source_type, source_tier,
  source_id, and quotes copied from the supplied excerpts. Set source_id to the
  supplied excerpt source value.
- Observations: ObservationSection entries with statements supported by supplied
  EvidenceItem entries.
- Market Expectations: market_expectations must state what consensus notes and
  market-implied inputs appear to assume.
- Variant Hypothesis: variant_hypothesis must explain the thesis that differs
  from those expectations.
- Why Consensus May Be Wrong: why_consensus_may_be_wrong must connect the
  observations to the variant hypothesis.
- Adversarial Research Reasoning: adversarial_research must include bull_case,
  bear_case, key_disagreement, evidence_for_variant_view,
  evidence_against_variant_view, rebuttal, disconfirming_evidence, and
  final_synthesis.
- Research Verdict: research_verdict and confidence must follow from the full
  reasoning chain.
- Investment Stance: investment_stance, top_risks, monitoring_rules, and
  recommended_next_step must follow from the verdict without making a capital
  allocation decision.

Do not perform reverse DCF calculations. Set reverse_dcf_expectations to null
unless explicit reverse DCF outputs are supplied in the manual inputs. Populate
valuation_range with Bear, Base, and Bull scenarios using assumptions, implied
outcomes, and supporting evidence from the supplied excerpts. Do not add an
overall score, composite score, weighted aggregate, ranking signal, price target,
or buy/sell recommendation.

Category score weights must be exactly: business_quality=0.30, risk_profile=0.20,
expectations_gap=0.20, variant_perception=0.15, valuation=0.10, catalyst=0.05.
Do not use any other values.

Prioritize backward-looking evidence — historical results, completed periods, and
reported metrics — over management's forward-looking statements. Forward guidance
may be cited as supplementary evidence but must not be the primary basis for
observations or the variant hypothesis. If the variant relies mainly on management's
characterisation of future backlog or pipeline, explicitly note this as a limitation
in the unknowns section.

Every EvidenceItem quote must be copied character-for-character from the supplied
excerpts, including exact capitalisation. If a sentence begins with a lowercase
letter in the source, the quote must also begin with a lowercase letter. Do not
capitalise a word that is lowercase in the source. Whitespace normalisation is
acceptable, but fabricated, paraphrased, or unlocatable quotes are invalid.
Do not invent evidence when the supplied excerpts are insufficient; use
research_verdict "Insufficient Evidence", confidence "Low", and explain the
unknown facts in unknowns. Leave normalized_quote, located_start_offset,
located_end_offset, and match_score null or omitted; the validator populates them.

InvestmentMemo JSON schema:
{memo_schema}

Manual inputs:
{request_json}
"""


def source_documents_from_request(request: ManualMemoRequest) -> list[SourceDocument]:
    """Convert manual request excerpts into evidence validator source documents."""

    excerpts = [*request.ten_k_excerpts, *request.transcript_excerpts]
    return [
        SourceDocument(
            source=excerpt.source,
            text=excerpt.text,
            published_date=excerpt.published_date,
        )
        for excerpt in excerpts
    ]


def parse_investment_memo_response(
    response: str,
    source_documents: Sequence[SourceDocument] | None = None,
    quote_match_threshold: float | None = None,
) -> InvestmentMemo:
    """Parse an LLM response into InvestmentMemo with clear failure modes."""

    try:
        payload = json.loads(response)
    except json.JSONDecodeError as error:
        raise InvalidMemoJSONError(
            "LLM response was not valid JSON: "
            f"{error.msg} at line {error.lineno}, column {error.colno}"
        ) from error

    try:
        memo = InvestmentMemo.model_validate(payload)
    except ValidationError as error:
        raise InvalidMemoSchemaError(
            "LLM response did not match InvestmentMemo schema: "
            f"{error.errors(include_url=False)}"
        ) from error

    if source_documents is None:
        return memo

    try:
        return validate_memo_evidence(
            memo,
            source_documents=source_documents,
            threshold=quote_match_threshold,
        )
    except EvidenceValidationError as error:
        raise InvalidMemoEvidenceError(str(error)) from error


__all__ = [
    "CompanyMetadata",
    "InvalidMemoEvidenceError",
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
    "source_documents_from_request",
]
