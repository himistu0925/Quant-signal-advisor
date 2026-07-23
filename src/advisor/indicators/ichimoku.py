import pandas as pd

from .base import IndicatorResult
from .registry import register


class IchimokuIndicator:
    name = "Ichimoku"

    def __init__(self, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52):
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        close = df["Close"]
        high = df["High"] if "High" in df else close
        low = df["Low"] if "Low" in df else close

        if len(close) < 2:
            return IndicatorResult(vote=0, detail="Ichimoku: insufficient data")

        tenkan = (high.rolling(self.tenkan_period).max() + low.rolling(self.tenkan_period).min()) / 2
        kijun = (high.rolling(self.kijun_period).max() + low.rolling(self.kijun_period).min()) / 2
        span_a = ((tenkan + kijun) / 2).shift(self.kijun_period)
        span_b = (
            (high.rolling(self.senkou_b_period).max() + low.rolling(self.senkou_b_period).min()) / 2
        ).shift(self.kijun_period)

        cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)
        cloud_bottom = pd.concat([span_a, span_b], axis=1).min(axis=1)

        values = [
            close.iloc[-2], close.iloc[-1],
            cloud_top.iloc[-2], cloud_top.iloc[-1],
            cloud_bottom.iloc[-2], cloud_bottom.iloc[-1],
            tenkan.iloc[-2], tenkan.iloc[-1],
            kijun.iloc[-2], kijun.iloc[-1],
        ]
        if any(pd.isna(v) for v in values):
            return IndicatorResult(vote=0, detail="Ichimoku: insufficient data")

        prev_close, curr_close = values[0], values[1]
        prev_top, curr_top = values[2], values[3]
        prev_bottom, curr_bottom = values[4], values[5]
        prev_tenkan, curr_tenkan = values[6], values[7]
        prev_kijun, curr_kijun = values[8], values[9]

        breakout_up = prev_close <= prev_top and curr_close > curr_top
        breakout_down = prev_close >= prev_bottom and curr_close < curr_bottom
        golden_cross = prev_tenkan <= prev_kijun and curr_tenkan > curr_kijun
        dead_cross = prev_tenkan >= prev_kijun and curr_tenkan < curr_kijun

        # PRD requires the cloud breakout and the tenkan/kijun cross to land
        # on the same bar -- a strong composite signal, not two independent votes.
        if breakout_up and golden_cross:
            vote = 1
        elif breakout_down and dead_cross:
            vote = -1
        else:
            vote = 0

        detail = f"Ichimoku(cloud={curr_bottom:.2f}-{curr_top:.2f}, tenkan={curr_tenkan:.2f}, kijun={curr_kijun:.2f})"
        return IndicatorResult(vote=vote, detail=detail)


register(IchimokuIndicator())
