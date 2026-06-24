import pytest
from pydantic import ValidationError

from backend.services.reverse_dcf import (
    ReverseDCFCyclicalityAdjustment,
    ReverseDCFDilutionAdjustment,
    ReverseDCFInputs,
    ReverseDCFScenarioValues,
    ReverseDCFSBCAdjustment,
    ReverseDCFTerminalAssumptions,
    calculate_reverse_dcf_expectations,
)


def fixture_inputs(**overrides: object) -> ReverseDCFInputs:
    data = {
        "share_price": 20,
        "shares_outstanding": 100,
        "net_debt": 200,
        "current_revenue": 500,
        "fcf_margin_assumptions": {
            "low": 0.18,
            "mid": 0.20,
            "high": 0.22,
        },
        "wacc_range": {
            "low": 0.08,
            "mid": 0.10,
            "high": 0.12,
        },
        "terminal_assumptions": {
            "projection_years": 5,
            "terminal_growth_rate": {
                "low": 0.02,
                "mid": 0.025,
                "high": 0.03,
            },
            "revenue_cagr_assumptions": {
                "low": 0.04,
                "mid": 0.07,
                "high": 0.10,
            },
        },
    }
    data.update(overrides)
    return ReverseDCFInputs.model_validate(data)


def output_fields(inputs: ReverseDCFInputs) -> dict[str, float]:
    return calculate_reverse_dcf_expectations(inputs).model_dump(
        exclude={"notes"}
    )


def test_reverse_dcf_known_fixture_outputs_are_deterministic() -> None:
    assert output_fields(fixture_inputs()) == {
        "implied_revenue_cagr_low": 0.0233,
        "implied_revenue_cagr_mid": 0.141,
        "implied_revenue_cagr_high": 0.2471,
        "implied_fcf_margin_low": 0.1579,
        "implied_fcf_margin_mid": 0.2665,
        "implied_fcf_margin_high": 0.3976,
    }


def test_net_debt_adjustment_changes_enterprise_value_expectations() -> None:
    net_cash = calculate_reverse_dcf_expectations(
        fixture_inputs(net_debt=-200)
    )
    net_debt = calculate_reverse_dcf_expectations(
        fixture_inputs(net_debt=400)
    )

    assert net_debt.implied_revenue_cagr_mid > net_cash.implied_revenue_cagr_mid
    assert net_debt.implied_fcf_margin_mid > net_cash.implied_fcf_margin_mid


def test_sbc_and_dilution_adjustments_raise_implied_expectations() -> None:
    base = calculate_reverse_dcf_expectations(fixture_inputs())
    adjusted = calculate_reverse_dcf_expectations(
        fixture_inputs(
            sbc_adjustment=ReverseDCFSBCAdjustment(
                annual_sbc_as_percent_revenue=0.03,
                annual_sbc_amount=10,
            ),
            dilution_adjustment=ReverseDCFDilutionAdjustment(
                annual_dilution_rate=0.05,
                additional_dilutive_shares=5,
            ),
        )
    )

    assert adjusted.implied_revenue_cagr_mid > base.implied_revenue_cagr_mid
    assert adjusted.implied_fcf_margin_mid > base.implied_fcf_margin_mid


def test_cyclicality_adjustments_normalize_peak_revenue_and_margin() -> None:
    base = calculate_reverse_dcf_expectations(fixture_inputs())
    cyclical_peak = calculate_reverse_dcf_expectations(
        fixture_inputs(
            cyclicality_adjustment=ReverseDCFCyclicalityAdjustment(
                revenue_normalization_factor=0.9,
                fcf_margin_adjustment=-0.02,
            )
        )
    )

    assert cyclical_peak.implied_revenue_cagr_mid > base.implied_revenue_cagr_mid
    assert cyclical_peak.implied_fcf_margin_mid > base.implied_fcf_margin_mid


def test_wacc_sensitivity_outputs_are_ordered() -> None:
    result = calculate_reverse_dcf_expectations(fixture_inputs())

    assert (
        result.implied_revenue_cagr_low
        < result.implied_revenue_cagr_mid
        < result.implied_revenue_cagr_high
    )
    assert (
        result.implied_fcf_margin_low
        < result.implied_fcf_margin_mid
        < result.implied_fcf_margin_high
    )


def test_reverse_dcf_validates_terminal_growth_below_wacc() -> None:
    with pytest.raises(ValidationError, match="wacc_range.low"):
        ReverseDCFInputs(
            share_price=20,
            shares_outstanding=100,
            net_debt=200,
            current_revenue=500,
            fcf_margin_assumptions=ReverseDCFScenarioValues(
                low=0.18,
                mid=0.20,
                high=0.22,
            ),
            wacc_range=ReverseDCFScenarioValues(low=0.04, mid=0.08, high=0.12),
            terminal_assumptions=ReverseDCFTerminalAssumptions(
                projection_years=5,
                terminal_growth_rate=ReverseDCFScenarioValues(
                    low=0.02,
                    mid=0.03,
                    high=0.05,
                ),
                revenue_cagr_assumptions=ReverseDCFScenarioValues(
                    low=0.04,
                    mid=0.07,
                    high=0.10,
                ),
            ),
        )
