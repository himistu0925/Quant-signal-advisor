import pandas as pd

from .base import IndicatorResult
from .registry import register


class FibonacciRetracementIndicator:
    name = "Fibonacci"

    def __init__(self, lookback: int = 60):
        self.lookback = lookback

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        close = df["Close"]
        high = df["High"] if "High" in df else close
        low = df["Low"] if "Low" in df else close

        if len(close) < self.lookback + 1:
            return IndicatorResult(vote=0, detail="Fibonacci: insufficient data")

        window_high = high.iloc[-(self.lookback + 1):-1]
        window_low = low.iloc[-(self.lookback + 1):-1]
        swing_high = window_high.max()
        swing_low = window_low.min()
        diff = swing_high - swing_low

        if diff <= 0:
            return IndicatorResult(vote=0, detail="Fibonacci: insufficient data")

        level_382 = swing_low + 0.382 * diff
        level_618 = swing_low + 0.618 * diff
        curr_close = close.iloc[-1]
        prev_close = close.iloc[-2]

        if curr_close < swing_low:
            vote = -1  # broke below the established swing low
        elif level_382 <= curr_close <= level_618 and curr_close > prev_close:
            vote = 1  # bouncing inside the retracement zone
        else:
            vote = 0

        detail = f"Fib(38.2%={level_382:.2f}, 61.8%={level_618:.2f}, close={curr_close:.2f})"
        return IndicatorResult(vote=vote, detail=detail)


register(FibonacciRetracementIndicator())
