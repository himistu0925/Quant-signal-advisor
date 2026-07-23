import pandas as pd

from advisor.indicators.bollinger_bands import BollingerBandsIndicator
from advisor.indicators.fibonacci import FibonacciRetracementIndicator
from advisor.indicators.ichimoku import IchimokuIndicator
from advisor.indicators.macd import MACDIndicator
from advisor.indicators.moving_average import MovingAverageIndicator
from advisor.indicators.rsi import RSIIndicator
from advisor.indicators.support_resistance import SupportResistanceIndicator
from advisor.indicators.volume import VolumeIndicator


def make_df(prices, **columns):
    data = {"Close": prices}
    data.update(columns)
    return pd.DataFrame(data)


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


def test_macd_golden_cross_signals_buy():
    # fast=1 makes the fast EMA equal to price; slow=3/signal=2 keeps the
    # hand-worked EWM recursion (alpha=0.5 / alpha=2/3) tractable by hand.
    prices = [10, 10, 10, 10, 10, 5, 15]
    result = MACDIndicator(fast=1, slow=3, signal=2).compute(make_df(prices))
    assert result.vote == 1


def test_macd_dead_cross_signals_sell():
    prices = [10, 10, 10, 10, 10, 15, 5]
    result = MACDIndicator(fast=1, slow=3, signal=2).compute(make_df(prices))
    assert result.vote == -1


def test_macd_insufficient_data_is_neutral():
    result = MACDIndicator().compute(make_df([100, 101, 102]))
    assert result.vote == 0


def test_bollinger_lower_band_reentry_signals_buy():
    prices = [100] * 10 + [70, 100]
    result = BollingerBandsIndicator(period=10).compute(make_df(prices))
    assert result.vote == 1


def test_bollinger_upper_band_reentry_signals_sell():
    prices = [100] * 10 + [130, 100]
    result = BollingerBandsIndicator(period=10).compute(make_df(prices))
    assert result.vote == -1


def test_bollinger_insufficient_data_is_neutral():
    result = BollingerBandsIndicator(period=20).compute(make_df([1, 2, 3]))
    assert result.vote == 0


def test_support_resistance_breakout_signals_buy():
    prices = [10, 10, 10, 10, 10, 20]
    result = SupportResistanceIndicator(lookback=5).compute(make_df(prices))
    assert result.vote == 1


def test_support_resistance_breakdown_signals_sell():
    prices = [10, 10, 10, 10, 10, 5]
    result = SupportResistanceIndicator(lookback=5).compute(make_df(prices))
    assert result.vote == -1


def test_support_resistance_insufficient_data_is_neutral():
    result = SupportResistanceIndicator(lookback=20).compute(make_df([1, 2, 3]))
    assert result.vote == 0


def test_volume_spike_confirms():
    volumes = [100] * 20 + [200]
    result = VolumeIndicator(period=20, multiplier_threshold=1.5).compute(
        make_df([1] * 21, Volume=volumes)
    )
    assert result.vote == 1


def test_volume_below_threshold_is_neutral():
    volumes = [100] * 20 + [120]
    result = VolumeIndicator(period=20, multiplier_threshold=1.5).compute(
        make_df([1] * 21, Volume=volumes)
    )
    assert result.vote == 0


def test_volume_insufficient_data_is_neutral():
    result = VolumeIndicator(period=20).compute(make_df([1, 1], Volume=[100, 100]))
    assert result.vote == 0


def test_fibonacci_bounce_in_zone_signals_buy():
    prices = [100, 100, 100, 100, 100, 100, 100, 50, 70, 70, 75]
    result = FibonacciRetracementIndicator(lookback=10).compute(make_df(prices))
    assert result.vote == 1


def test_fibonacci_break_below_swing_low_signals_sell():
    prices = [100, 100, 100, 100, 100, 100, 100, 50, 70, 70, 40]
    result = FibonacciRetracementIndicator(lookback=10).compute(make_df(prices))
    assert result.vote == -1


def test_fibonacci_insufficient_data_is_neutral():
    result = FibonacciRetracementIndicator(lookback=60).compute(make_df([1, 2, 3]))
    assert result.vote == 0


def test_ichimoku_cloud_breakout_with_golden_cross_signals_buy():
    prices = [10, 10, 10, 10, 10, 20]
    result = IchimokuIndicator(tenkan_period=1, kijun_period=2, senkou_b_period=3).compute(
        make_df(prices)
    )
    assert result.vote == 1


def test_ichimoku_cloud_breakdown_with_dead_cross_signals_sell():
    prices = [10, 10, 10, 10, 10, 0]
    result = IchimokuIndicator(tenkan_period=1, kijun_period=2, senkou_b_period=3).compute(
        make_df(prices)
    )
    assert result.vote == -1


def test_ichimoku_insufficient_data_is_neutral():
    result = IchimokuIndicator().compute(make_df([100, 101, 102]))
    assert result.vote == 0


def test_registry_collects_default_plugins():
    from advisor.indicators import get_registered

    registered = get_registered()
    for name in ["RSI", "MA", "MACD", "BollingerBands", "SupportResistance", "Volume", "Fibonacci", "Ichimoku"]:
        assert name in registered
