import pandas as pd
import pytest

from advisor.risk.position_sizing import (
    MAX_POSITION_PCT,
    compute_risk_levels,
    position_size_pct,
    position_size_shares,
)


def _constant_range_df(n=30, high=11.0, low=9.0, close=10.0):
    return pd.DataFrame({"High": [high] * n, "Low": [low] * n, "Close": [close] * n})


def test_compute_risk_levels_returns_none_with_insufficient_history():
    df = _constant_range_df(n=3)
    assert compute_risk_levels(df, entry_price=10.0) is None


def test_compute_risk_levels_returns_none_for_non_positive_entry_price():
    df = _constant_range_df(n=30)
    assert compute_risk_levels(df, entry_price=0.0) is None


def test_compute_risk_levels_stop_and_target_from_atr():
    # Constant range -> ATR converges to 2.0 (see test_risk_atr.py); with
    # multiplier=2.0 the stop distance is 4.0 and target uses a 2:1 reward.
    df = _constant_range_df(high=11.0, low=9.0, close=10.0)
    levels = compute_risk_levels(df, entry_price=10.0, atr_period=14, atr_multiplier=2.0, reward_risk_ratio=2.0)

    assert levels is not None
    assert levels.stop_price == pytest.approx(6.0)
    assert levels.target_price == pytest.approx(18.0)
    assert levels.stop_distance_pct == pytest.approx(0.4)


def test_position_size_pct_scales_inversely_with_stop_distance():
    # 0.01 / 0.08 = 0.125, comfortably under MAX_POSITION_PCT so the cap
    # (covered separately below) doesn't mask the inverse-scaling behavior.
    assert position_size_pct(stop_distance_pct=0.08, risk_per_trade_pct=0.01) == pytest.approx(0.125)


def test_position_size_pct_caps_at_max_position_pct():
    # A very tight stop would otherwise imply far more than 100% of equity.
    assert position_size_pct(stop_distance_pct=0.001, risk_per_trade_pct=0.01) == pytest.approx(MAX_POSITION_PCT)


def test_position_size_pct_none_for_non_positive_stop_distance():
    assert position_size_pct(stop_distance_pct=0.0) is None


def test_position_size_shares_floors_to_whole_shares():
    # equity=10,000 * position_pct=0.1 -> $1,000 allocated; at $300/share
    # that is 3.33 shares, which must floor to 3 (never round up).
    assert position_size_shares(equity=10_000, position_pct=0.1, entry_price=300.0) == 3
