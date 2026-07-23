from dataclasses import dataclass
from itertools import product

import pandas as pd

from advisor.indicators.base import Indicator

from .engine import simulate_trades
from .metrics import PerformanceMetrics, compute_metrics


def compute_vote_matrix(df: pd.DataFrame, indicators: dict[str, Indicator], min_lookback: int) -> pd.DataFrame:
    """The expensive O(n^2) pass -- run once per ticker, not once per grid
    combination. Everything after this is cheap vectorized arithmetic over
    these precomputed votes, which is what makes a weight/threshold grid
    search over hundreds or thousands of combinations tractable."""
    n = len(df)
    dates = df.index[min_lookback:]
    votes = {name: [] for name in indicators}

    for i in range(min_lookback, n):
        window = df.iloc[: i + 1]
        for name, indicator in indicators.items():
            votes[name].append(indicator.compute(window).vote)

    return pd.DataFrame(votes, index=dates)


def _score_series_from_votes(
    vote_matrix: pd.DataFrame,
    weights: dict,
    volume_votes: pd.Series | None,
    volume_multiplier: float,
) -> pd.Series:
    score = sum(vote_matrix[name] * weight for name, weight in weights.items())
    if volume_votes is not None:
        score = score * volume_votes.map(lambda v: volume_multiplier if v == 1 else 1.0)
    return score


@dataclass
class CalibrationResult:
    weights: dict
    buy_threshold: float
    sell_threshold: float
    train_metrics: PerformanceMetrics
    test_metrics: PerformanceMetrics


class InsufficientDataError(Exception):
    """Not enough price history to run a meaningful train/test calibration
    (plan.md section 9 assumes a multi-year split) -- e.g. a ticker that
    IPO'd a few weeks ago. Callers should skip calibrating this ticker
    rather than persist a threshold that was never really searched."""


def grid_search(
    df: pd.DataFrame,
    indicators: dict[str, Indicator],
    weight_grid: list,
    threshold_grid: list,
    volume_indicator: Indicator | None = None,
    volume_multiplier: float = 1.5,
    min_lookback: int = 100,
    test_years: float = 1.0,
    benchmark_df: pd.DataFrame | None = None,
) -> CalibrationResult:
    """Section 9's methodology: search weight/threshold combinations on the
    train period only (objective = Sharpe ratio), then re-run the winner on
    the untouched holdout test period to surface overfitting rather than
    hide it. Symmetric thresholds (sell = -buy) keep the grid a single
    dimension instead of two, which matters a lot once weight combinations
    are already multiplying the search space."""
    close = df["Close"]
    names = list(indicators.keys())

    vote_matrix = compute_vote_matrix(df, indicators, min_lookback)
    if vote_matrix.empty:
        raise InsufficientDataError(
            f"only {len(df)} price bars available -- need more than min_lookback={min_lookback} "
            "to compute even one indicator vote"
        )

    volume_votes = None
    if volume_indicator is not None:
        volume_votes = compute_vote_matrix(df, {"Volume": volume_indicator}, min_lookback)["Volume"]

    split_date = df.index[-1] - pd.Timedelta(days=int(test_years * 365.25))
    train_mask = vote_matrix.index < split_date

    if train_mask.sum() == 0 or (~train_mask).sum() == 0:
        raise InsufficientDataError(
            f"computable history only spans {vote_matrix.index[0].date()}..{vote_matrix.index[-1].date()} "
            f"({len(vote_matrix)} days) -- not enough to form both a train period and a "
            f"{test_years}-year test period"
        )

    if benchmark_df is not None:
        benchmark_close = benchmark_df["Close"]
        train_benchmark = benchmark_close[benchmark_close.index < split_date]
        test_benchmark = benchmark_close[benchmark_close.index >= split_date]
    else:
        train_benchmark = pd.Series(dtype=float)
        test_benchmark = pd.Series(dtype=float)

    best_objective = None
    best_weights = None
    best_buy_threshold = None

    for weight_combo in product(weight_grid, repeat=len(names)):
        weights = dict(zip(names, weight_combo))
        score_series = _score_series_from_votes(vote_matrix, weights, volume_votes, volume_multiplier)
        train_score = score_series[train_mask]

        for buy_threshold in threshold_grid:
            sell_threshold = -buy_threshold
            train_result = simulate_trades(close, train_score, buy_threshold, sell_threshold)
            objective = compute_metrics(train_result, train_benchmark).sharpe_ratio

            if best_objective is None or objective > best_objective:
                best_objective = objective
                best_weights = weights
                best_buy_threshold = buy_threshold

    best_sell_threshold = -best_buy_threshold
    full_score_series = _score_series_from_votes(vote_matrix, best_weights, volume_votes, volume_multiplier)

    train_result = simulate_trades(close, full_score_series[train_mask], best_buy_threshold, best_sell_threshold)
    test_result = simulate_trades(close, full_score_series[~train_mask], best_buy_threshold, best_sell_threshold)

    return CalibrationResult(
        weights=best_weights,
        buy_threshold=best_buy_threshold,
        sell_threshold=best_sell_threshold,
        train_metrics=compute_metrics(train_result, train_benchmark),
        test_metrics=compute_metrics(test_result, test_benchmark),
    )


def calibrate_ticker(
    df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    weight_grid=(1.0,),
    threshold_grid=(2.0, 3.0, 4.0, 5.0),
    min_lookback: int = 100,
    test_years: float = 1.0,
) -> CalibrationResult:
    """Default weight_grid=(1.0,) intentionally searches thresholds only:
    with 7 directional indicators, even a 3-value weight grid is 3**7=2187
    combinations, and calibrating 14 free parameters (7 weights + threshold)
    against ~4 years of daily bars risks curve-fitting badly (plan.md
    section 14). Pass a wider weight_grid explicitly if you want that
    broader (and slower, and shakier) search."""
    from advisor.indicators import split_registered

    directional, volume_indicator = split_registered()

    return grid_search(
        df=df,
        indicators=directional,
        weight_grid=list(weight_grid),
        threshold_grid=list(threshold_grid),
        volume_indicator=volume_indicator,
        min_lookback=min_lookback,
        test_years=test_years,
        benchmark_df=benchmark_df,
    )
