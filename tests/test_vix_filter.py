import pandas as pd
import pytest

from advisor.market_signals.vix_filter import VixFilter


def test_extreme_high_vix_is_extreme_fear():
    history = pd.DataFrame({"Close": [15] * 90 + [40]})
    state = VixFilter().evaluate(history)
    assert state.regime == "extreme_fear"
    assert state.percentile > 90


def test_extreme_low_vix_is_extreme_greed():
    history = pd.DataFrame({"Close": [30] * 90 + [10]})
    state = VixFilter().evaluate(history)
    assert state.regime == "extreme_greed"
    assert state.percentile < 10


def test_mid_range_vix_is_neutral():
    history = pd.DataFrame({"Close": list(range(1, 100)) + [50]})
    state = VixFilter().evaluate(history)
    assert state.regime == "neutral"
    assert 20 < state.percentile < 80


def test_empty_history_raises():
    with pytest.raises(ValueError):
        VixFilter().evaluate(pd.DataFrame({"Close": []}))
