from dataclasses import dataclass

import pandas as pd


@dataclass
class VixState:
    value: float
    percentile: float
    regime: str  # "extreme_fear" | "extreme_greed" | "neutral"


class VixFilter:
    """Market-wide macro filter (plan.md section 8): not a per-ticker vote,
    but a regime read on how extreme current VIX is versus its own history,
    meant to shift buy/sell thresholds in the (not-yet-built) scoring engine."""

    def __init__(self, high_percentile: float = 80.0, low_percentile: float = 20.0):
        self.high_percentile = high_percentile
        self.low_percentile = low_percentile

    def evaluate(self, vix_history: pd.DataFrame) -> VixState:
        close = vix_history["Close"]
        if close.empty:
            raise ValueError("vix_history must contain at least one row")

        current = close.iloc[-1]
        percentile = (close < current).mean() * 100

        if percentile >= self.high_percentile:
            regime = "extreme_fear"
        elif percentile <= self.low_percentile:
            regime = "extreme_greed"
        else:
            regime = "neutral"

        return VixState(value=current, percentile=percentile, regime=regime)
