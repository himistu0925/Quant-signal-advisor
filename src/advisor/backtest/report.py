from dataclasses import dataclass

import pandas as pd

from .engine import BacktestEngine, BacktestResult
from .metrics import PerformanceMetrics, compute_metrics


@dataclass
class BacktestReport:
    train: PerformanceMetrics
    test: PerformanceMetrics
    full: PerformanceMetrics
    split_date: pd.Timestamp


def _split_result(result: BacktestResult, split_date: pd.Timestamp) -> tuple[BacktestResult, BacktestResult]:
    equity = result.equity_curve
    train_equity = equity[equity.index < split_date]
    test_equity = equity[equity.index >= split_date]
    train_trades = [t for t in result.trades if t.exit_date < split_date]
    test_trades = [t for t in result.trades if t.exit_date >= split_date]
    return (
        BacktestResult(trades=train_trades, equity_curve=train_equity),
        BacktestResult(trades=test_trades, equity_curve=test_equity),
    )


def generate_report(
    df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    engine: BacktestEngine,
    test_years: float = 1.0,
) -> BacktestReport:
    """Runs one continuous simulation over the full history (no lookahead,
    per BacktestEngine) then splits the resulting trades/equity by date --
    section 9's train/test split is for *calibrating* thresholds later
    (Phase 4); here it just separates this report's numbers by period."""
    result = engine.run(df)
    split_date = df.index[-1] - pd.Timedelta(days=int(test_years * 365.25))

    train_result, test_result = _split_result(result, split_date)
    benchmark_close = benchmark_df["Close"]

    return BacktestReport(
        train=compute_metrics(train_result, benchmark_close[benchmark_close.index < split_date]),
        test=compute_metrics(test_result, benchmark_close[benchmark_close.index >= split_date]),
        full=compute_metrics(result, benchmark_close),
        split_date=split_date,
    )
