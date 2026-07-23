import pandas as pd
import pytest

from advisor.backtest.engine import BacktestEngine
from advisor.indicators.base import IndicatorResult
from tests.helpers import FakeIndicator


def make_price_df(prices):
    dates = pd.date_range("2020-01-01", periods=len(prices))
    return pd.DataFrame({"Close": prices}, index=dates)


def test_single_trade_lifecycle_and_equity_compounding():
    prices = [100, 101, 102, 103, 104, 105, 104, 103, 102, 101]
    df = make_price_df(prices)
    votes = [0, 0, 0, 1, 1, 1, -1, -1, 0, 0]
    engine = BacktestEngine(
        indicators={"Fake": FakeIndicator(votes)},
        buy_threshold=1,
        sell_threshold=-1,
        min_lookback=3,
    )

    result = engine.run(df)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_date == df.index[3]
    assert trade.entry_price == 103
    assert trade.exit_date == df.index[6]
    assert trade.exit_price == 104

    assert result.equity_curve.index[0] == df.index[3]
    assert result.equity_curve.index[-1] == df.index[9]
    assert result.equity_curve.iloc[-1] == pytest.approx(104 / 103)


def test_still_open_position_is_marked_to_market_at_series_end():
    prices = [100, 101, 102, 103, 104, 105, 106, 107]
    df = make_price_df(prices)
    votes = [0, 0, 0, 1, 1, 1, 1, 1]  # buys at index 3, never gets a sell signal
    engine = BacktestEngine(
        indicators={"Fake": FakeIndicator(votes)},
        buy_threshold=1,
        sell_threshold=-1,
        min_lookback=3,
    )

    result = engine.run(df)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_date == df.index[3]
    assert trade.exit_date == df.index[-1]
    assert trade.exit_price == prices[-1]


def test_insufficient_data_returns_empty_result():
    df = make_price_df([100, 101, 102])
    engine = BacktestEngine(indicators={"Fake": FakeIndicator([0, 0, 0])}, min_lookback=10)

    result = engine.run(df)

    assert result.trades == []
    assert result.equity_curve.empty


class ConstantIndicator:
    def __init__(self, vote, name="Const"):
        self.vote = vote
        self.name = name

    def compute(self, window):
        return IndicatorResult(vote=self.vote, detail="const")


def test_volume_indicator_multiplies_score_when_confirming():
    engine = BacktestEngine(
        indicators={"Const": ConstantIndicator(1)},
        volume_indicator=ConstantIndicator(1, name="Volume"),
        volume_multiplier=1.5,
    )
    score = engine.score_at(pd.DataFrame({"Close": [1, 2, 3]}))
    assert score == pytest.approx(1.5)


def test_volume_indicator_does_not_multiply_when_not_confirming():
    engine = BacktestEngine(
        indicators={"Const": ConstantIndicator(1)},
        volume_indicator=ConstantIndicator(0, name="Volume"),
        volume_multiplier=1.5,
    )
    score = engine.score_at(pd.DataFrame({"Close": [1, 2, 3]}))
    assert score == pytest.approx(1.0)
