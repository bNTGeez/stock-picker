"""Pydantic schemas for investment research memos."""

from datetime import date
from enum import Enum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictSchema(BaseModel):
    """Base schema that rejects undeclared contract fields."""

    model_config = ConfigDict(extra="forbid")


class ResearchVerdict(str, Enum):
    """Final research conclusion for a memo."""

    INSUFFICIENT_EVIDENCE = "Insufficient Evidence"
    REJECT = "Reject"
    WATCHLIST = "Watchlist"
    RESEARCH_FURTHER = "Research Further"
    CANDIDATE = "Candidate"
    HIGH_CONVICTION_CANDIDATE = "High Conviction Candidate"


class InvestmentStance(str, Enum):
    """Investment stance implied by the research."""

    BEARISH = "Bearish"
    LEAN_BEARISH = "Lean Bearish"
    NEUTRAL = "Neutral"
    LEAN_BULLISH = "Lean Bullish"
    BULLISH = "Bullish"


class Confidence(str, Enum):
    """Confidence level for the stated verdict."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class EvidenceItem(StrictSchema):
    """Source-backed evidence referenced by an observation."""

    source: str = Field(..., min_length=1)
    quote: str = Field(..., min_length=1)
    url: HttpUrl | None = None
    published_date: date | None = None
    normalized_quote: str | None = Field(default=None, min_length=1)
    located_start_offset: int | None = Field(default=None, ge=0)
    located_end_offset: int | None = Field(default=None, ge=0)
    match_score: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_location_metadata(self) -> "EvidenceItem":
        location_values = (
            self.normalized_quote,
            self.located_start_offset,
            self.located_end_offset,
            self.match_score,
        )
        if any(value is not None for value in location_values):
            if any(value is None for value in location_values):
                raise ValueError(
                    "Evidence location metadata must be populated together"
                )
            if self.located_end_offset <= self.located_start_offset:
                raise ValueError(
                    "Evidence located_end_offset must be greater than "
                    "located_start_offset"
                )
        return self


class ObservationItem(StrictSchema):
    """Analytical observation supported by one or more evidence items."""

    observation: str = Field(..., min_length=1)
    analysis: str = Field(..., min_length=1)
    evidence: list[EvidenceItem] = Field(..., min_length=1)


class ObservationSection(StrictSchema):
    """Named group of memo observations."""

    title: str = Field(..., min_length=1)
    observations: list[ObservationItem] = Field(..., min_length=1)


class AdversarialResearchSection(StrictSchema):
    """Bull, bear, and disconfirming tests of the variant hypothesis."""

    bull_case: str = Field(..., min_length=1)
    bear_case: str = Field(..., min_length=1)
    key_disagreement: str = Field(..., min_length=1)
    evidence_for_variant_view: list[EvidenceItem] = Field(..., min_length=1)
    evidence_against_variant_view: list[EvidenceItem] = Field(..., min_length=1)
    rebuttal: str = Field(..., min_length=1)
    disconfirming_evidence: list[str] = Field(..., min_length=1)
    final_synthesis: str = Field(..., min_length=1)


class UnknownsSection(StrictSchema):
    """Known unknowns that remain after research."""

    open_questions: list[str] = Field(..., min_length=1)
    data_gaps: list[str] = Field(default_factory=list)


class CategoryScore(StrictSchema):
    """Non-aggregate score label for one research category."""

    score: int = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)
    rationale: str = Field(..., min_length=1)


class CategoryScores(StrictSchema):
    """Fixed-weight category score labels for an investment memo."""

    FIXED_WEIGHTS: ClassVar[dict[str, float]] = {
        "business_quality": 0.30,
        "risk_profile": 0.20,
        "expectations_gap": 0.20,
        "variant_perception": 0.15,
        "valuation": 0.10,
        "catalyst": 0.05,
    }

    business_quality: CategoryScore
    risk_profile: CategoryScore
    expectations_gap: CategoryScore
    variant_perception: CategoryScore
    valuation: CategoryScore
    catalyst: CategoryScore

    @model_validator(mode="after")
    def enforce_fixed_weights(self) -> "CategoryScores":
        for category, expected_weight in self.FIXED_WEIGHTS.items():
            score = getattr(self, category)
            if abs(score.weight - expected_weight) > 1e-9:
                raise ValueError(
                    f"{category} weight must be {expected_weight:.2f}"
                )
        return self


class ReverseDCFExpectations(StrictSchema):
    """Expectations implied by market price from a reverse DCF analysis."""

    implied_revenue_cagr_low: float
    implied_revenue_cagr_mid: float
    implied_revenue_cagr_high: float
    implied_fcf_margin_low: float
    implied_fcf_margin_mid: float
    implied_fcf_margin_high: float
    notes: str | None = None


class ValuationScenario(StrictSchema):
    """Single Bear/Base/Bull valuation case with explicit assumptions."""

    label: Literal["Bear", "Base", "Bull"]
    assumptions: list[str] = Field(..., min_length=1)
    implied_outcome: str = Field(..., min_length=1)
    supporting_evidence: list[EvidenceItem] = Field(..., min_length=1)


class ValuationRange(StrictSchema):
    """Bear/Base/Bull valuation range for the memo."""

    bear: ValuationScenario
    base: ValuationScenario
    bull: ValuationScenario

    @model_validator(mode="after")
    def enforce_scenario_labels(self) -> "ValuationRange":
        expected_labels = {
            "bear": "Bear",
            "base": "Base",
            "bull": "Bull",
        }
        for field_name, expected_label in expected_labels.items():
            scenario = getattr(self, field_name)
            if scenario.label != expected_label:
                raise ValueError(
                    f"{field_name} scenario label must be {expected_label}"
                )
        return self


class MonitoringRule(StrictSchema):
    """Rule for tracking thesis drift after memo publication."""

    trigger: str = Field(..., min_length=1)
    rationale: str = Field(..., min_length=1)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class MonitoringRules(StrictSchema):
    """Green, yellow, and red thesis monitoring triggers."""

    green_flags: list[MonitoringRule] = Field(..., min_length=1)
    yellow_flags: list[MonitoringRule] = Field(..., min_length=1)
    red_flags: list[MonitoringRule] = Field(..., min_length=1)


class InvestmentMemo(StrictSchema):
    """Complete investment memo schema contract."""

    company_name: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    memo_date: date
    research_verdict: ResearchVerdict
    investment_stance: InvestmentStance
    confidence: Confidence
    category_scores: CategoryScores
    market_expectations: str = Field(..., min_length=1)
    observations: list[ObservationItem] = Field(..., min_length=1)
    variant_hypothesis: str = Field(..., min_length=1)
    why_consensus_may_be_wrong: str = Field(..., min_length=1)
    adversarial_research: AdversarialResearchSection
    unknowns: UnknownsSection
    top_risks: list[str] = Field(..., min_length=1)
    valuation_range: ValuationRange
    reverse_dcf_expectations: ReverseDCFExpectations | None
    monitoring_rules: MonitoringRules
    recommended_next_step: str = Field(..., min_length=1)


__all__ = [
    "AdversarialResearchSection",
    "CategoryScore",
    "CategoryScores",
    "Confidence",
    "EvidenceItem",
    "InvestmentMemo",
    "InvestmentStance",
    "MonitoringRule",
    "MonitoringRules",
    "ObservationItem",
    "ObservationSection",
    "ResearchVerdict",
    "ReverseDCFExpectations",
    "UnknownsSection",
    "ValuationRange",
    "ValuationScenario",
]
