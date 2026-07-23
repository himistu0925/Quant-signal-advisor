from dataclasses import dataclass

import numpy as np
import pandas as pd

from .engine import BacktestResult


@dataclass
class PerformanceMetrics:
    cumulative_return: float
    cagr: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    avg_win_loss_ratio: float | None  # None when there are no losing trades to compare against
    total_trades: int
    benchmark_return: float
    excess_return: float


def _cagr(equity: pd.Series) -> float:
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1


def _sharpe_ratio(equity: pd.Series) -> float:
    daily_returns = equity.pct_change().dropna()
    if daily_returns.std() == 0 or daily_returns.empty:
        return 0.0
    return (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    return ((equity / equity.cummax()) - 1).min()


def compute_metrics(result: BacktestResult, benchmark_close: pd.Series) -> PerformanceMetrics:
    equity = result.equity_curve
    if equity.empty:
        return PerformanceMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0)

    cumulative_return = equity.iloc[-1] / equity.iloc[0] - 1

    wins = [t.return_pct for t in result.trades if t.return_pct > 0]
    losses = [t.return_pct for t in result.trades if t.return_pct <= 0]
    total_trades = len(result.trades)
    win_rate = len(wins) / total_trades if total_trades else 0.0

    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    if avg_loss != 0:
        avg_win_loss_ratio = abs(avg_win / avg_loss)
    elif avg_win > 0:
        # No losing trades at all -- float("inf") would serialize to the
        # non-standard JSON token "Infinity" and break strict JSON parsers
        # (calibration/*.json and docs/data.json are both real JSON files).
        avg_win_loss_ratio = None
    else:
        avg_win_loss_ratio = 0.0

    if len(benchmark_close) > 1:
        benchmark_return = benchmark_close.iloc[-1] / benchmark_close.iloc[0] - 1
    else:
        benchmark_return = 0.0

    return PerformanceMetrics(
        cumulative_return=cumulative_return,
        cagr=_cagr(equity),
        max_drawdown=_max_drawdown(equity),
        sharpe_ratio=_sharpe_ratio(equity),
        win_rate=win_rate,
        avg_win_loss_ratio=avg_win_loss_ratio,
        total_trades=total_trades,
        benchmark_return=benchmark_return,
        excess_return=cumulative_return - benchmark_return,
    )
