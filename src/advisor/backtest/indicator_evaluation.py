from dataclasses import dataclass

import pandas as pd

from advisor.indicators.base import Indicator

from .calibration import compute_vote_matrix
from .engine import simulate_trades
from .metrics import PerformanceMetrics, compute_metrics


@dataclass
class ContributionReport:
    name: str
    signal_count: int
    information_coefficient: float | None
    solo_metrics: PerformanceMetrics


def evaluate_indicator_contribution(
    df: pd.DataFrame,
    indicator: Indicator,
    benchmark_close: pd.Series | None = None,
    min_lookback: int = 100,
    forward_days: int = 5,
    min_ic_samples: int = 30,
) -> ContributionReport:
    """Plan.md section 7: before a candidate indicator can be promoted to
    core (registry.register(..., status="core")), check whether it actually
    predicts anything on its own -- a solo backtest (trade on every vote,
    no other indicators involved) plus an information coefficient (does the
    vote correlate with the *forward*, not concurrent, return -- so this
    can't be fooled by lookahead)."""
    votes = compute_vote_matrix(df, {indicator.name: indicator}, min_lookback)[indicator.name]
    close = df["Close"]

    result = simulate_trades(close, votes, buy_threshold=1, sell_threshold=-1)
    benchmark = benchmark_close if benchmark_close is not None else pd.Series(dtype=float)
    solo_metrics = compute_metrics(result, benchmark)

    forward_return = close.pct_change(forward_days).shift(-forward_days)
    aligned_forward = forward_return.reindex(votes.index)
    valid = aligned_forward.notna()

    if valid.sum() >= min_ic_samples:
        ic = votes[valid].corr(aligned_forward[valid])
        # A constant vote series (e.g. all zero) makes correlation undefined
        # (NaN) rather than raising -- and float("nan") is just as
        # non-standard in JSON as float("inf") was (see metrics.py).
        information_coefficient = None if pd.isna(ic) else float(ic)
    else:
        information_coefficient = None

    return ContributionReport(
        name=indicator.name,
        signal_count=int((votes != 0).sum()),
        information_coefficient=information_coefficient,
        solo_metrics=solo_metrics,
    )
