import pandas as pd

from advisor.indicators.moving_average import MovingAverageIndicator
from advisor.indicators.rsi import RSIIndicator


def make_df(prices):
    return pd.DataFrame({"Close": prices})


def test_rsi_oversold_signals_buy():
    prices = [100 - i for i in range(20)]
    result = RSIIndicator(period=14).compute(make_df(prices))
    assert result.vote == 1


def test_rsi_overbought_signals_sell():
    prices = [50 + i for i in range(20)]
    result = RSIIndicator(period=14).compute(make_df(prices))
    assert result.vote == -1


def test_rsi_insufficient_data_is_neutral():
    result = RSIIndicator(period=14).compute(make_df([100, 101, 102]))
    assert result.vote == 0


def test_ma_golden_cross_signals_buy():
    # short(2)/long(3) crafted so short MA sits below long MA one bar back,
    # then crosses above it on the latest bar.
    prices = [10, 10, 10, 5, 20]
    result = MovingAverageIndicator(short=2, long=3).compute(make_df(prices))
    assert result.vote == 1


def test_ma_dead_cross_signals_sell():
    prices = [10, 10, 10, 15, 0]
    result = MovingAverageIndicator(short=2, long=3).compute(make_df(prices))
    assert result.vote == -1


def test_ma_insufficient_data_is_neutral():
    result = MovingAverageIndicator(short=20, long=50).compute(make_df([1, 2, 3]))
    assert result.vote == 0


def test_registry_collects_default_plugins():
    from advisor.indicators import get_registered

    registered = get_registered()
    assert "RSI" in registered
    assert "MA" in registered
