import pandas as pd

from .base import IndicatorResult
from .registry import register


class BollingerBandsIndicator:
    name = "BollingerBands"

    def __init__(self, period: int = 20, std_mult: float = 2.0):
        self.period = period
        self.std_mult = std_mult

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        close = df["Close"]
        if len(close) < self.period + 1:
            return IndicatorResult(vote=0, detail="BollingerBands: insufficient data")

        mid = close.rolling(self.period).mean()
        std = close.rolling(self.period).std()
        upper = mid + self.std_mult * std
        lower = mid - self.std_mult * std

        prev_close, curr_close = close.iloc[-2], close.iloc[-1]
        prev_upper, curr_upper = upper.iloc[-2], upper.iloc[-1]
        prev_lower, curr_lower = lower.iloc[-2], lower.iloc[-1]

        if any(pd.isna(v) for v in (prev_upper, curr_upper, prev_lower, curr_lower)):
            return IndicatorResult(vote=0, detail="BollingerBands: insufficient data")

        if prev_close < prev_lower and curr_close >= curr_lower:
            vote = 1  # re-entry from below the lower band
        elif prev_close > prev_upper and curr_close <= curr_upper:
            vote = -1  # re-entry from above the upper band
        else:
            vote = 0

        detail = f"BB(mid={mid.iloc[-1]:.2f}, upper={curr_upper:.2f}, lower={curr_lower:.2f})"
        return IndicatorResult(vote=vote, detail=detail)


register(BollingerBandsIndicator())
