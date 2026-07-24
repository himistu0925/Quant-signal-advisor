import pandas as pd
import pytest

from advisor.risk.atr import average_true_range, true_range


def _make_df(highs, lows, closes):
    return pd.DataFrame({"High": highs, "Low": lows, "Close": closes})


def test_true_range_uses_high_low_range_on_first_bar():
    df = _make_df([10], [9], [9.5])
    assert true_range(df).iloc[0] == pytest.approx(1.0)


def test_true_range_uses_gap_from_prior_close_when_larger():
    # day2: H-L=0.4, but the gap from day1's close (9.5) is larger (0.7)
    # day3: a 5-point gap up dwarfs the 1-point high-low range that day
    df = _make_df([10, 10.2, 15], [9, 9.8, 14], [9.5, 10, 14.5])
    tr = true_range(df)
    assert tr.iloc[1] == pytest.approx(0.7)
    assert tr.iloc[2] == pytest.approx(5.0)


def test_true_range_falls_back_to_close_when_no_high_low_columns():
    df = pd.DataFrame({"Close": [10, 11, 9]})
    tr = true_range(df)
    assert tr.iloc[1] == pytest.approx(1.0)
    assert tr.iloc[2] == pytest.approx(2.0)


def test_average_true_range_is_nan_until_period_bars_available():
    df = _make_df([10] * 5, [9] * 5, [9.5] * 5)
    atr = average_true_range(df, period=14)
    assert pd.isna(atr.iloc[-1])


def test_average_true_range_converges_to_constant_daily_range():
    # Constant High=11/Low=9/Close=10 every day -> true range is a flat 2.0
    # every bar (no gaps), so Wilder-smoothed ATR should converge to 2.0.
    df = _make_df([11] * 20, [9] * 20, [10] * 20)
    atr = average_true_range(df, period=14)
    assert atr.iloc[-1] == pytest.approx(2.0)
