from dataclasses import dataclass

import pandas as pd

from advisor.risk.atr import average_true_range

ATR_PERIOD = 14
MOVE_ATR_MULTIPLE = 2.0  # today's move must be at least this many multiples of the ticker's own ATR


@dataclass
class MoveAlert:
    direction: str  # "SURGE" or "PLUNGE"
    pct_change: float
    price: float


def detect_sharp_move(
    df: pd.DataFrame,
    atr_period: int = ATR_PERIOD,
    atr_multiple: float = MOVE_ATR_MULTIPLE,
) -> MoveAlert | None:
    """Flags when today's move (latest bar's close vs. the prior close) is
    unusually large *relative to this ticker's own normal daily range*
    (ATR) -- a typically-tight 1%/day stock moving 3% is more notable than
    the same 3% move on a stock that swings 5% on an average day. Used to
    catch a universe-scan candidate moving *right now*, during market
    hours, rather than only surfacing it in the next nightly scan.

    Returns None when there's too little history, or the move doesn't
    clear the bar."""
    if len(df) < 2:
        return None

    prev_close = df["Close"].iloc[-2]
    price = df["Close"].iloc[-1]
    if pd.isna(prev_close) or pd.isna(price) or prev_close <= 0:
        return None

    pct_change = price / prev_close - 1

    atr = average_true_range(df, period=atr_period)
    latest_atr = atr.iloc[-1]
    if pd.isna(latest_atr):
        return None

    atr_pct = latest_atr / prev_close
    if atr_pct <= 0 or abs(pct_change) < atr_multiple * atr_pct:
        return None

    return MoveAlert(direction="SURGE" if pct_change > 0 else "PLUNGE", pct_change=pct_change, price=price)
