"""Deterministic reverse DCF market expectations engine."""

from __future__ import annotations

from pydantic import Field, model_validator

from backend.models.schemas import ReverseDCFExpectations, StrictSchema


class ReverseDCFScenarioValues(StrictSchema):
    """Low, mid, and high scenario values expressed as decimals."""

    low: float = Field(..., gt=-1, lt=2)
    mid: float = Field(..., gt=-1, lt=2)
    high: float = Field(..., gt=-1, lt=2)

    @model_validator(mode="after")
    def enforce_ordering(self) -> "ReverseDCFScenarioValues":
        if not self.low <= self.mid <= self.high:
            raise ValueError("scenario values must be ordered low <= mid <= high")
        return self


class ReverseDCFTerminalAssumptions(StrictSchema):
    """Terminal value and growth assumptions used for reverse DCF solving."""

    projection_years: int = Field(default=5, ge=1, le=30)
    terminal_growth_rate: ReverseDCFScenarioValues
    revenue_cagr_assumptions: ReverseDCFScenarioValues


class ReverseDCFSBCAdjustment(StrictSchema):
    """SBC burden to subtract from cash flow margins."""

    annual_sbc_as_percent_revenue: float = Field(default=0.0, ge=0, lt=1)
    annual_sbc_amount: float = Field(default=0.0, ge=0)


class ReverseDCFDilutionAdjustment(StrictSchema):
    """Share-count adjustments reflected in market capitalization."""

    annual_dilution_rate: float = Field(default=0.0, ge=0, lt=1)
    additional_dilutive_shares: float = Field(default=0.0, ge=0)


class ReverseDCFCyclicalityAdjustment(StrictSchema):
    """Normalization adjustments for cyclical revenue or margin distortion."""

    revenue_normalization_factor: float = Field(default=1.0, gt=0)
    fcf_margin_adjustment: float = Field(default=0.0, gt=-1, lt=1)


class ReverseDCFInputs(StrictSchema):
    """Inputs required for deterministic reverse DCF expectations analysis."""

    share_price: float = Field(..., gt=0)
    shares_outstanding: float = Field(..., gt=0)
    net_debt: float = 0.0
    current_revenue: float = Field(..., gt=0)
    fcf_margin_assumptions: ReverseDCFScenarioValues
    wacc_range: ReverseDCFScenarioValues
    terminal_assumptions: ReverseDCFTerminalAssumptions
    sbc_adjustment: ReverseDCFSBCAdjustment = Field(
        default_factory=ReverseDCFSBCAdjustment
    )
    dilution_adjustment: ReverseDCFDilutionAdjustment = Field(
        default_factory=ReverseDCFDilutionAdjustment
    )
    cyclicality_adjustment: ReverseDCFCyclicalityAdjustment = Field(
        default_factory=ReverseDCFCyclicalityAdjustment
    )

    @model_validator(mode="after")
    def validate_discount_rates(self) -> "ReverseDCFInputs":
        terminal_growth = self.terminal_assumptions.terminal_growth_rate
        if self.wacc_range.low <= terminal_growth.high:
            raise ValueError(
                "wacc_range.low must exceed terminal_growth_rate.high"
            )
        return self


def calculate_reverse_dcf_expectations(
    inputs: ReverseDCFInputs,
) -> ReverseDCFExpectations:
    """Calculate market-implied growth and margin expectations.

    The low/mid/high outputs are sensitivity cases. The low case uses the most
    favorable discount-rate, terminal-growth, and counterpart assumptions; the
    high case uses the least favorable assumptions.
    """

    enterprise_value = _enterprise_value(inputs)
    normalized_revenue = _normalized_revenue(inputs)
    sbc_margin_burden = _sbc_margin_burden(inputs, normalized_revenue)
    terminal = inputs.terminal_assumptions

    implied_revenue_cagr_low = _solve_revenue_cagr(
        enterprise_value=enterprise_value,
        current_revenue=normalized_revenue,
        fcf_margin=_cash_margin(
            inputs.fcf_margin_assumptions.high,
            inputs.cyclicality_adjustment.fcf_margin_adjustment,
            sbc_margin_burden,
        ),
        wacc=inputs.wacc_range.low,
        terminal_growth=terminal.terminal_growth_rate.high,
        projection_years=terminal.projection_years,
    )
    implied_revenue_cagr_mid = _solve_revenue_cagr(
        enterprise_value=enterprise_value,
        current_revenue=normalized_revenue,
        fcf_margin=_cash_margin(
            inputs.fcf_margin_assumptions.mid,
            inputs.cyclicality_adjustment.fcf_margin_adjustment,
            sbc_margin_burden,
        ),
        wacc=inputs.wacc_range.mid,
        terminal_growth=terminal.terminal_growth_rate.mid,
        projection_years=terminal.projection_years,
    )
    implied_revenue_cagr_high = _solve_revenue_cagr(
        enterprise_value=enterprise_value,
        current_revenue=normalized_revenue,
        fcf_margin=_cash_margin(
            inputs.fcf_margin_assumptions.low,
            inputs.cyclicality_adjustment.fcf_margin_adjustment,
            sbc_margin_burden,
        ),
        wacc=inputs.wacc_range.high,
        terminal_growth=terminal.terminal_growth_rate.low,
        projection_years=terminal.projection_years,
    )

    implied_fcf_margin_low = _solve_reported_fcf_margin(
        enterprise_value=enterprise_value,
        current_revenue=normalized_revenue,
        revenue_cagr=terminal.revenue_cagr_assumptions.high,
        wacc=inputs.wacc_range.low,
        terminal_growth=terminal.terminal_growth_rate.high,
        projection_years=terminal.projection_years,
        cyclicality_margin_adjustment=(
            inputs.cyclicality_adjustment.fcf_margin_adjustment
        ),
        sbc_margin_burden=sbc_margin_burden,
    )
    implied_fcf_margin_mid = _solve_reported_fcf_margin(
        enterprise_value=enterprise_value,
        current_revenue=normalized_revenue,
        revenue_cagr=terminal.revenue_cagr_assumptions.mid,
        wacc=inputs.wacc_range.mid,
        terminal_growth=terminal.terminal_growth_rate.mid,
        projection_years=terminal.projection_years,
        cyclicality_margin_adjustment=(
            inputs.cyclicality_adjustment.fcf_margin_adjustment
        ),
        sbc_margin_burden=sbc_margin_burden,
    )
    implied_fcf_margin_high = _solve_reported_fcf_margin(
        enterprise_value=enterprise_value,
        current_revenue=normalized_revenue,
        revenue_cagr=terminal.revenue_cagr_assumptions.low,
        wacc=inputs.wacc_range.high,
        terminal_growth=terminal.terminal_growth_rate.low,
        projection_years=terminal.projection_years,
        cyclicality_margin_adjustment=(
            inputs.cyclicality_adjustment.fcf_margin_adjustment
        ),
        sbc_margin_burden=sbc_margin_burden,
    )

    return ReverseDCFExpectations(
        implied_revenue_cagr_low=round(implied_revenue_cagr_low, 4),
        implied_revenue_cagr_mid=round(implied_revenue_cagr_mid, 4),
        implied_revenue_cagr_high=round(implied_revenue_cagr_high, 4),
        implied_fcf_margin_low=round(implied_fcf_margin_low, 4),
        implied_fcf_margin_mid=round(implied_fcf_margin_mid, 4),
        implied_fcf_margin_high=round(implied_fcf_margin_high, 4),
    )


def _enterprise_value(inputs: ReverseDCFInputs) -> float:
    diluted_shares = (
        inputs.shares_outstanding
        * (1 + inputs.dilution_adjustment.annual_dilution_rate)
        + inputs.dilution_adjustment.additional_dilutive_shares
    )
    enterprise_value = inputs.share_price * diluted_shares + inputs.net_debt
    if enterprise_value <= 0:
        raise ValueError("enterprise value must be positive after adjustments")
    return enterprise_value


def _normalized_revenue(inputs: ReverseDCFInputs) -> float:
    return (
        inputs.current_revenue
        * inputs.cyclicality_adjustment.revenue_normalization_factor
    )


def _sbc_margin_burden(
    inputs: ReverseDCFInputs,
    normalized_revenue: float,
) -> float:
    return (
        inputs.sbc_adjustment.annual_sbc_as_percent_revenue
        + inputs.sbc_adjustment.annual_sbc_amount / normalized_revenue
    )


def _cash_margin(
    reported_fcf_margin: float,
    cyclicality_margin_adjustment: float,
    sbc_margin_burden: float,
) -> float:
    margin = (
        reported_fcf_margin
        + cyclicality_margin_adjustment
        - sbc_margin_burden
    )
    if margin <= 0:
        raise ValueError(
            "FCF margin assumptions must remain positive after SBC and "
            "cyclicality adjustments"
        )
    return margin


def _discounted_cash_flow_value(
    *,
    current_revenue: float,
    revenue_cagr: float,
    fcf_margin: float,
    wacc: float,
    terminal_growth: float,
    projection_years: int,
) -> float:
    value = 0.0
    final_revenue = current_revenue
    for year in range(1, projection_years + 1):
        final_revenue = current_revenue * (1 + revenue_cagr) ** year
        free_cash_flow = final_revenue * fcf_margin
        value += free_cash_flow / (1 + wacc) ** year

    terminal_free_cash_flow = final_revenue * fcf_margin * (1 + terminal_growth)
    terminal_value = terminal_free_cash_flow / (wacc - terminal_growth)
    return value + terminal_value / (1 + wacc) ** projection_years


def _solve_revenue_cagr(
    *,
    enterprise_value: float,
    current_revenue: float,
    fcf_margin: float,
    wacc: float,
    terminal_growth: float,
    projection_years: int,
) -> float:
    low = -0.95
    high = 2.0
    while (
        _discounted_cash_flow_value(
            current_revenue=current_revenue,
            revenue_cagr=high,
            fcf_margin=fcf_margin,
            wacc=wacc,
            terminal_growth=terminal_growth,
            projection_years=projection_years,
        )
        < enterprise_value
    ):
        high *= 2
        if high > 20:
            raise ValueError("could not solve implied revenue CAGR")

    for _ in range(100):
        mid = (low + high) / 2
        value = _discounted_cash_flow_value(
            current_revenue=current_revenue,
            revenue_cagr=mid,
            fcf_margin=fcf_margin,
            wacc=wacc,
            terminal_growth=terminal_growth,
            projection_years=projection_years,
        )
        if value < enterprise_value:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def _solve_reported_fcf_margin(
    *,
    enterprise_value: float,
    current_revenue: float,
    revenue_cagr: float,
    wacc: float,
    terminal_growth: float,
    projection_years: int,
    cyclicality_margin_adjustment: float,
    sbc_margin_burden: float,
) -> float:
    value_at_full_cash_margin = _discounted_cash_flow_value(
        current_revenue=current_revenue,
        revenue_cagr=revenue_cagr,
        fcf_margin=1.0,
        wacc=wacc,
        terminal_growth=terminal_growth,
        projection_years=projection_years,
    )
    required_cash_margin = enterprise_value / value_at_full_cash_margin
    return (
        required_cash_margin
        - cyclicality_margin_adjustment
        + sbc_margin_burden
    )


__all__ = [
    "ReverseDCFCyclicalityAdjustment",
    "ReverseDCFDilutionAdjustment",
    "ReverseDCFInputs",
    "ReverseDCFScenarioValues",
    "ReverseDCFSBCAdjustment",
    "ReverseDCFTerminalAssumptions",
    "calculate_reverse_dcf_expectations",
]
