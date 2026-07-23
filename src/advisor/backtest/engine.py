from dataclasses import dataclass, field

import pandas as pd

from advisor.indicators.base import Indicator


@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float

    @property
    def return_pct(self) -> float:
        return (self.exit_price - self.entry_price) / self.entry_price


@dataclass
class BacktestResult:
    trades: list = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))


def simulate_trades(
    close: pd.Series, score_series: pd.Series, buy_threshold: float, sell_threshold: float
) -> BacktestResult:
    """Shared trading state machine, driven purely by a precomputed score per
    day. Split out from BacktestEngine.run so grid search (calibration.py)
    can reuse it against a precomputed vote matrix instead of recomputing
    every indicator for every weight/threshold combination it tries."""
    if score_series.empty:
        return BacktestResult()

    prev_close = close.shift(1)

    equity_values = []
    equity_dates = []
    trades: list[Trade] = []

    in_position = False
    entry_price = None
    entry_date = None
    equity = 1.0

    for date, score in score_series.items():
        price = close.loc[date]

        if in_position:
            equity *= price / prev_close.loc[date]

        if not in_position and score >= buy_threshold:
            in_position = True
            entry_price = price
            entry_date = date
        elif in_position and score <= sell_threshold:
            trades.append(Trade(entry_date, entry_price, date, price))
            in_position = False
            entry_price = None
            entry_date = None

        equity_values.append(equity)
        equity_dates.append(date)

    if in_position:
        # Mark the still-open position to market at the last available
        # price so metrics don't show trades=0 alongside a nonzero return.
        trades.append(Trade(entry_date, entry_price, equity_dates[-1], close.loc[equity_dates[-1]]))

    return BacktestResult(trades=trades, equity_curve=pd.Series(equity_values, index=equity_dates))


class BacktestEngine:
    """Long-only, single-position-at-a-time simulator (plan.md sections 2 & 9:
    position sizing/shorting are out of scope). Indicators are evaluated on an
    expanding window ending at each bar so no future data ever leaks into a
    day's decision -- this also makes the engine identical in shape to how
    the live signal check will call indicators."""

    def __init__(
        self,
        indicators: dict[str, Indicator],
        weights: dict | None = None,
        volume_indicator: Indicator | None = None,
        volume_multiplier: float = 1.5,
        buy_threshold: float = 3.0,
        sell_threshold: float = -3.0,
        min_lookback: int = 100,
    ):
        self.indicators = indicators
        self.weights = weights or {name: 1.0 for name in indicators}
        self.volume_indicator = volume_indicator
        self.volume_multiplier = volume_multiplier
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.min_lookback = min_lookback

    def score_at(self, window: pd.DataFrame) -> float:
        total = 0.0
        for name, indicator in self.indicators.items():
            result = indicator.compute(window)
            total += result.vote * self.weights.get(name, 1.0)

        if self.volume_indicator is not None:
            volume_result = self.volume_indicator.compute(window)
            if volume_result.vote == 1:
                total *= self.volume_multiplier

        return total

    def run(self, df: pd.DataFrame) -> BacktestResult:
        close = df["Close"]
        n = len(df)
        if n <= self.min_lookback:
            return BacktestResult()

        dates = df.index[self.min_lookback:]
        scores = [self.score_at(df.iloc[: self.min_lookback + j + 1]) for j in range(len(dates))]
        score_series = pd.Series(scores, index=dates)

        return simulate_trades(close, score_series, self.buy_threshold, self.sell_threshold)


def default_engine(**overrides) -> BacktestEngine:
    from advisor.indicators import split_registered

    directional, volume_indicator = split_registered()
    overrides.setdefault("volume_indicator", volume_indicator)
    return BacktestEngine(indicators=directional, **overrides)
