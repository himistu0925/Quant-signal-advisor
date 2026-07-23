import pandas as pd

from .base import IndicatorResult, crossover_vote
from .registry import register


class MACDIndicator:
    name = "MACD"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        close = df["Close"]
        if len(close) < self.slow + self.signal + 1:
            return IndicatorResult(vote=0, detail="MACD: insufficient data")

        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()

        prev_diff = macd_line.iloc[-2] - signal_line.iloc[-2]
        curr_diff = macd_line.iloc[-1] - signal_line.iloc[-1]

        vote = crossover_vote(prev_diff, curr_diff)
        detail = f"MACD={macd_line.iloc[-1]:.2f}, Signal={signal_line.iloc[-1]:.2f}"
        return IndicatorResult(vote=vote, detail=detail)


register(MACDIndicator())
