import pandas as pd


def true_range(df: pd.DataFrame) -> pd.Series:
    """Wilder's true range: the largest of today's high-low range, or the
    gap from yesterday's close to today's high/low. Canonical source for
    every indicator that needs it (see indicators/adx.py)."""
    high = df["High"] if "High" in df else df["Close"]
    low = df["Low"] if "Low" in df else df["Close"]
    close = df["Close"]
    prev_close = close.shift(1)
    return pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)


def average_true_range(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder-smoothed ATR (same recursive EWM form as RSI/ADX)."""
    tr = true_range(df)
    return tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
