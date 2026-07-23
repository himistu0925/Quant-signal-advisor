import pandas as pd
import pytest

from advisor.backtest.indicator_evaluation import evaluate_indicator_contribution
from tests.helpers import FakeIndicator


def _alternating_df(n):
    prices = [100 if i % 2 == 0 else 110 for i in range(n)]
    return pd.DataFrame({"Close": prices}, index=pd.date_range("2020-01-01", periods=n))


def test_perfectly_predictive_votes_give_ic_near_one():
    n = 40
    votes = [1 if i % 2 == 0 else -1 for i in range(n)]

    report = evaluate_indicator_contribution(
        _alternating_df(n), FakeIndicator(votes), min_lookback=0, forward_days=1, min_ic_samples=10,
    )

    assert report.information_coefficient == pytest.approx(1.0, abs=1e-6)
    assert report.signal_count == n
    assert report.solo_metrics.win_rate == 1.0
    assert report.solo_metrics.total_trades > 0


def test_below_min_samples_returns_none_ic():
    n = 20
    votes = [1 if i % 2 == 0 else -1 for i in range(n)]

    report = evaluate_indicator_contribution(
        _alternating_df(n), FakeIndicator(votes), min_lookback=0, forward_days=1, min_ic_samples=1000,
    )

    assert report.information_coefficient is None


def test_constant_zero_votes_give_none_ic_not_nan():
    n = 40
    votes = [0] * n

    report = evaluate_indicator_contribution(
        _alternating_df(n), FakeIndicator(votes), min_lookback=0, forward_days=1, min_ic_samples=10,
    )

    assert report.information_coefficient is None
    assert report.signal_count == 0
    assert report.solo_metrics.total_trades == 0
