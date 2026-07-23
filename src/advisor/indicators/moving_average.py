import pandas as pd

from .base import IndicatorResult, crossover_vote
from .registry import register


class MovingAverageIndicator:
    name = "MA"

    def __init__(self, short: int = 20, long: int = 50):
        self.short = short
        self.long = long

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        close = df["Close"]
        short_ma = close.rolling(self.short).mean()
        long_ma = close.rolling(self.long).mean()

        if len(close) < self.long + 1:
            return IndicatorResult(vote=0, detail="MA: insufficient data")

        prev_diff = short_ma.iloc[-2] - long_ma.iloc[-2]
        curr_diff = short_ma.iloc[-1] - long_ma.iloc[-1]
        if pd.isna(prev_diff) or pd.isna(curr_diff):
            return IndicatorResult(vote=0, detail="MA: insufficient data")

        vote = crossover_vote(prev_diff, curr_diff)
        detail = f"MA{self.short}={short_ma.iloc[-1]:.2f}, MA{self.long}={long_ma.iloc[-1]:.2f}"
        return IndicatorResult(vote=vote, detail=detail)


register(MovingAverageIndicator())
