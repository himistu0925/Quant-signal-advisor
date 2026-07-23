import pandas as pd

from .base import IndicatorResult
from .registry import register


class SupportResistanceIndicator:
    name = "SupportResistance"

    def __init__(self, lookback: int = 20):
        self.lookback = lookback

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        close = df["Close"]
        high = df["High"] if "High" in df else close
        low = df["Low"] if "Low" in df else close

        if len(close) < self.lookback + 1:
            return IndicatorResult(vote=0, detail="SupportResistance: insufficient data")

        window_high = high.iloc[-(self.lookback + 1):-1]
        window_low = low.iloc[-(self.lookback + 1):-1]
        resistance = window_high.max()
        support = window_low.min()
        curr_close = close.iloc[-1]

        if curr_close > resistance:
            vote = 1
        elif curr_close < support:
            vote = -1
        else:
            vote = 0

        detail = f"S/R(resistance={resistance:.2f}, support={support:.2f}, close={curr_close:.2f})"
        return IndicatorResult(vote=vote, detail=detail)


register(SupportResistanceIndicator())
