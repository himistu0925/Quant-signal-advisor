import pandas as pd

from .base import IndicatorResult
from .registry import register


class VolumeIndicator:
    """Confirmation signal, not a directional vote: PRD section 9 uses this
    as a reliability multiplier on other indicators rather than its own
    buy/sell call. vote=1 here means "volume confirms conviction"; the
    scoring engine (not yet built) is responsible for reinterpreting it."""

    name = "Volume"

    def __init__(self, period: int = 20, multiplier_threshold: float = 1.5):
        self.period = period
        self.multiplier_threshold = multiplier_threshold

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        volume = df["Volume"]
        if len(volume) < self.period + 1:
            return IndicatorResult(vote=0, detail="Volume: insufficient data")

        avg_volume = volume.rolling(self.period).mean().iloc[-2]
        curr_volume = volume.iloc[-1]

        if pd.isna(avg_volume) or avg_volume == 0:
            return IndicatorResult(vote=0, detail="Volume: insufficient data")

        ratio = curr_volume / avg_volume
        vote = 1 if ratio >= self.multiplier_threshold else 0
        detail = f"Volume ratio={ratio:.2f}x avg({self.period})"
        return IndicatorResult(vote=vote, detail=detail)


register(VolumeIndicator())
