import pandas as pd

from advisor.risk.atr import true_range

from .base import IndicatorResult
from .registry import register


class ADXIndicator:
    """Candidate indicator (plan.md section 7 expansion list) -- registered
    but excluded from live/backtest scoring until its contribution is
    validated (see backtest/indicator_evaluation.py).

    ADX measures trend *strength*, not direction; +DI/-DI supply direction.
    Wilder's original smoothing (same recursive form as RSI's)."""

    name = "ADX"

    def __init__(self, di_period: int = 14, adx_period: int = 14, trend_threshold: float = 25.0):
        self.di_period = di_period
        self.adx_period = adx_period
        self.trend_threshold = trend_threshold

    def compute(self, df: pd.DataFrame) -> IndicatorResult:
        high = df["High"] if "High" in df else df["Close"]
        low = df["Low"] if "Low" in df else df["Close"]
        close = df["Close"]

        if len(close) < max(self.di_period, self.adx_period) + 2:
            return IndicatorResult(vote=0, detail="ADX: insufficient data")

        up_move = high.diff()
        down_move = -low.diff()

        plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
        minus_dm = ((down_move > up_move) & (down_move > 0)) * down_move

        tr = true_range(df)

        alpha_di = 1 / self.di_period
        smoothed_plus_dm = plus_dm.ewm(alpha=alpha_di, adjust=False, min_periods=self.di_period).mean()
        smoothed_minus_dm = minus_dm.ewm(alpha=alpha_di, adjust=False, min_periods=self.di_period).mean()
        smoothed_tr = tr.ewm(alpha=alpha_di, adjust=False, min_periods=self.di_period).mean()

        plus_di = 100 * smoothed_plus_dm / smoothed_tr
        minus_di = 100 * smoothed_minus_dm / smoothed_tr

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        adx = dx.ewm(alpha=1 / self.adx_period, adjust=False, min_periods=self.adx_period).mean()

        curr_adx = adx.iloc[-1]
        curr_plus_di = plus_di.iloc[-1]
        curr_minus_di = minus_di.iloc[-1]

        if pd.isna(curr_adx) or pd.isna(curr_plus_di) or pd.isna(curr_minus_di):
            return IndicatorResult(vote=0, detail="ADX: insufficient data")

        if curr_adx > self.trend_threshold and curr_plus_di > curr_minus_di:
            vote = 1
        elif curr_adx > self.trend_threshold and curr_minus_di > curr_plus_di:
            vote = -1
        else:
            vote = 0

        detail = f"ADX={curr_adx:.1f}(+DI={curr_plus_di:.1f},-DI={curr_minus_di:.1f})"
        return IndicatorResult(vote=vote, detail=detail)


register(ADXIndicator(), status="candidate")
