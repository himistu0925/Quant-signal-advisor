import pandas as pd

from .base import IndicatorResult, crossover_vote
from .registry import register


class OBVIndicator:
    """Candidate indicator (plan.md section 7 expansion list) -- registered
    but excluded from live/backtest scoring until its contribution is
    validated (see backtest/indicator_evaluation.py)."""

    name = "OBV"

    def __init__(self, short: int = 5, long: int = 20):
        self.short = short
        self.long = long

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        close = df["Close"]
        volume = df["Volume"]

        if len(close) < self.long + 1:
            return IndicatorResult(vote=0, detail="OBV: insufficient data")

        direction = close.diff().apply(lambda d: 1 if d > 0 else (-1 if d < 0 else 0))
        obv = (direction * volume).cumsum()

        short_ma = obv.rolling(self.short).mean()
        long_ma = obv.rolling(self.long).mean()

        prev_diff = short_ma.iloc[-2] - long_ma.iloc[-2]
        curr_diff = short_ma.iloc[-1] - long_ma.iloc[-1]
        if pd.isna(prev_diff) or pd.isna(curr_diff):
            return IndicatorResult(vote=0, detail="OBV: insufficient data")

        vote = crossover_vote(prev_diff, curr_diff)
        detail = f"OBV(short={short_ma.iloc[-1]:.0f}, long={long_ma.iloc[-1]:.0f})"
        return IndicatorResult(vote=vote, detail=detail)


register(OBVIndicator(), status="candidate")
