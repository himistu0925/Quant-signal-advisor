import pandas as pd

from .base import IndicatorResult
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

        if prev_diff <= 0 and curr_diff > 0:
            vote = 1  # golden cross
        elif prev_diff >= 0 and curr_diff < 0:
            vote = -1  # dead cross
        else:
            vote = 0

        detail = f"MA{self.short}={short_ma.iloc[-1]:.2f}, MA{self.long}={long_ma.iloc[-1]:.2f}"
        return IndicatorResult(vote=vote, detail=detail)


register(MovingAverageIndicator())
