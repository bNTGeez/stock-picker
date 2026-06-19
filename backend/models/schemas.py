"""Pydantic schemas for investment research memos."""

from datetime import date
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictSchema(BaseModel):
    """Base schema that rejects undeclared contract fields."""

    model_config = ConfigDict(extra="forbid")


class ResearchVerdict(str, Enum):
    """Final research conclusion for a memo."""

    INVESTABLE = "investable"
    WATCHLIST = "watchlist"
    PASS = "pass"


class InvestmentStance(str, Enum):
    """Portfolio action implied by the research."""

    LONG = "long"
    SHORT = "short"
    AVOID = "avoid"
    WATCH = "watch"


class Confidence(str, Enum):
    """Confidence level for the stated verdict."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceItem(StrictSchema):
    """Source-backed evidence referenced by an observation."""

    source: str = Field(..., min_length=1)
    quote: str = Field(..., min_length=1)
    url: HttpUrl | None = None
    published_date: date | None = None


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
    """Counter-thesis and disconfirming evidence for the memo."""

    bear_case: list[ObservationItem] = Field(..., min_length=1)
    disconfirming_evidence: list[EvidenceItem] = Field(default_factory=list)
    unresolved_challenges: list[str] = Field(default_factory=list)


class UnknownsSection(StrictSchema):
    """Known unknowns that remain after research."""

    open_questions: list[str] = Field(..., min_length=1)
    data_gaps: list[str] = Field(default_factory=list)


class CategoryScore(StrictSchema):
    """Non-aggregate score label for one research category."""

    score: str = Field(..., min_length=1)
    weight: float = Field(..., ge=0, le=1)


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
            if score.weight != expected_weight:
                raise ValueError(
                    f"{category} weight must be {expected_weight:.2f}"
                )
        return self


class ReverseDCFExpectations(StrictSchema):
    """Expectations implied by market price from a reverse DCF analysis."""

    implied_revenue_growth: float | None = None
    implied_operating_margin: float | None = None
    implied_free_cash_flow_margin: float | None = None
    implied_terminal_growth: float | None = None
    implied_discount_rate: float | None = None
    notes: str | None = None


class ValuationScenario(StrictSchema):
    """Single valuation case with explicit assumptions."""

    name: str = Field(..., min_length=1)
    intrinsic_value_per_share: float = Field(..., ge=0)
    assumptions: dict[str, Any] = Field(default_factory=dict)


class ValuationRange(StrictSchema):
    """Downside/base/upside valuation cases for the memo."""

    currency: str = Field(..., min_length=1, max_length=3)
    downside: ValuationScenario
    base: ValuationScenario
    upside: ValuationScenario


class MonitoringRule(StrictSchema):
    """Rule for tracking thesis drift after memo publication."""

    metric: str = Field(..., min_length=1)
    condition: str = Field(..., min_length=1)
    threshold: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)


class InvestmentMemo(StrictSchema):
    """Complete investment memo schema contract."""

    company_name: str = Field(..., min_length=1)
    ticker: str = Field(..., min_length=1)
    memo_date: date
    verdict: ResearchVerdict
    stance: InvestmentStance
    confidence: Confidence
    thesis: str = Field(..., min_length=1)
    observation_sections: list[ObservationSection] = Field(..., min_length=1)
    adversarial_research: AdversarialResearchSection
    unknowns: UnknownsSection
    category_scores: CategoryScores
    reverse_dcf_expectations: ReverseDCFExpectations | None = None
    valuation_range: ValuationRange
    monitoring_rules: list[MonitoringRule] = Field(default_factory=list)


__all__ = [
    "AdversarialResearchSection",
    "CategoryScore",
    "CategoryScores",
    "Confidence",
    "EvidenceItem",
    "InvestmentMemo",
    "InvestmentStance",
    "MonitoringRule",
    "ObservationItem",
    "ObservationSection",
    "ResearchVerdict",
    "ReverseDCFExpectations",
    "UnknownsSection",
    "ValuationRange",
    "ValuationScenario",
]
