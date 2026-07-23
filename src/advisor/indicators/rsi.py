import pandas as pd

from .base import IndicatorResult
from .registry import register


class RSIIndicator:
    name = "RSI"

    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        close = df["Close"]
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1 / self.period, min_periods=self.period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / self.period, min_periods=self.period, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        latest = rsi.iloc[-1]
        if pd.isna(latest):
            return IndicatorResult(vote=0, detail="RSI: insufficient data")

        if latest < self.oversold:
            vote = 1
        elif latest > self.overbought:
            vote = -1
        else:
            vote = 0

        return IndicatorResult(vote=vote, detail=f"RSI({self.period})={latest:.1f}")


register(RSIIndicator())
