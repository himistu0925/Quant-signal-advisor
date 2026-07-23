import math

import pandas as pd
import pytest

from advisor.backtest.engine import BacktestResult, Trade
from advisor.backtest.metrics import compute_metrics


def test_compute_metrics_with_known_trades_and_equity():
    dates = pd.date_range("2020-01-01", periods=5)
    equity = pd.Series([1.0, 1.05, 0.95, 1.10, 1.20], index=dates)
    trades = [
        Trade(entry_date=dates[0], entry_price=100, exit_date=dates[1], exit_price=110),
        Trade(entry_date=dates[2], entry_price=100, exit_date=dates[3], exit_price=90),
    ]
    result = BacktestResult(trades=trades, equity_curve=equity)
    benchmark_close = pd.Series([50, 55], index=[dates[0], dates[4]])

    metrics = compute_metrics(result, benchmark_close)

    assert metrics.cumulative_return == pytest.approx(0.20)
    assert metrics.total_trades == 2
    assert metrics.win_rate == pytest.approx(0.5)
    assert metrics.avg_win_loss_ratio == pytest.approx(1.0)
    assert metrics.benchmark_return == pytest.approx(0.10)
    assert metrics.excess_return == pytest.approx(0.10)
    assert metrics.max_drawdown == pytest.approx(0.95 / 1.05 - 1, rel=1e-6)
    assert metrics.cagr > 0
    assert not math.isnan(metrics.sharpe_ratio)


def test_compute_metrics_empty_result_is_all_zero():
    result = BacktestResult()
    benchmark_close = pd.Series([100, 105], index=pd.date_range("2020-01-01", periods=2))

    metrics = compute_metrics(result, benchmark_close)

    assert metrics.total_trades == 0
    assert metrics.cumulative_return == 0.0
    assert metrics.win_rate == 0.0
