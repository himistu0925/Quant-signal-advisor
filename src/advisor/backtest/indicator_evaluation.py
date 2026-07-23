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


def derive_ic_weights(
    df: pd.DataFrame,
    indicators: dict[str, Indicator],
    min_lookback: int = 100,
    forward_days: int = 5,
    min_ic_samples: int = 30,
) -> dict[str, float]:
    """Plan.md section 9 (2026-07-23 update): weight each indicator by its
    own measured information coefficient on THIS ticker's history, instead
    of every indicator getting the same weight everywhere -- a leveraged
    index ETF and an individual stock can genuinely have different
    indicators driving the real signal. Non-positive IC gets weight 0
    (excluded, not sign-flipped -- inverting a backward-looking correlation
    is a much bigger overfitting risk than just dropping it). Weights are
    rescaled to sum to len(indicators) so they stay on the same numeric
    scale as the old equal-weight-of-1.0 baseline (existing threshold grids
    like 2-5 remain meaningful)."""
    raw_weights = {}
    for name, indicator in indicators.items():
        report = evaluate_indicator_contribution(
            df, indicator, min_lookback=min_lookback, forward_days=forward_days, min_ic_samples=min_ic_samples,
        )
        ic = report.information_coefficient or 0.0
        raw_weights[name] = max(0.0, ic)

    total = sum(raw_weights.values())
    n = len(indicators)

    if total <= 0:
        # Nothing showed positive predictive value -- fall back to the
        # safe equal-weight baseline rather than an all-zero score.
        return {name: 1.0 for name in indicators}

    return {name: (w / total) * n for name, w in raw_weights.items()}
