import pandas as pd

from .base import IndicatorResult
from .registry import register


class StochasticIndicator:
    """Candidate indicator (plan.md section 7 expansion list) -- registered
    but excluded from live/backtest scoring until its contribution is
    validated (see backtest/indicator_evaluation.py)."""

    name = "Stochastic"

    def __init__(self, period: int = 14, smooth_k: int = 3, oversold: float = 20.0, overbought: float = 80.0):
        self.period = period
        self.smooth_k = smooth_k
        self.oversold = oversold
        self.overbought = overbought

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        close = df["Close"]
        high = df["High"] if "High" in df else close
        low = df["Low"] if "Low" in df else close

        if len(close) < self.period + self.smooth_k:
            return IndicatorResult(vote=0, detail="Stochastic: insufficient data")

        lowest_low = low.rolling(self.period).min()
        highest_high = high.rolling(self.period).max()
        raw_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        k = raw_k.rolling(self.smooth_k).mean()

        curr_k = k.iloc[-1]
        if pd.isna(curr_k):
            return IndicatorResult(vote=0, detail="Stochastic: insufficient data")

        if curr_k < self.oversold:
            vote = 1
        elif curr_k > self.overbought:
            vote = -1
        else:
            vote = 0

        return IndicatorResult(vote=vote, detail=f"Stochastic(%K={curr_k:.1f})")


register(StochasticIndicator(), status="candidate")
