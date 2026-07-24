from dataclasses import dataclass

import pandas as pd

from advisor.risk.atr import average_true_range

ATR_PERIOD = 14
ATR_MULTIPLIER = 2.0  # stop distance = ATR * this
REWARD_RISK_RATIO = 2.0  # target distance = stop distance * this
RISK_PER_TRADE_PCT = 0.01  # fraction of equity lost if the stop is hit
MAX_POSITION_PCT = 0.25  # cap so a low-volatility ticker can't imply >25% of equity in one name


@dataclass
class RiskLevels:
    stop_price: float
    target_price: float
    stop_distance_pct: float


def compute_risk_levels(
    df: pd.DataFrame,
    entry_price: float,
    atr_period: int = ATR_PERIOD,
    atr_multiplier: float = ATR_MULTIPLIER,
    reward_risk_ratio: float = REWARD_RISK_RATIO,
) -> RiskLevels | None:
    """ATR-based stop/target for a long entry (BUY signals only -- a SELL
    signal means "exit an existing holding", not a new position to size).
    Returns None when there isn't enough history yet for a meaningful ATR."""
    if entry_price <= 0:
        return None

    atr = average_true_range(df, period=atr_period)
    latest_atr = atr.iloc[-1]
    if pd.isna(latest_atr):
        return None

    stop_distance = latest_atr * atr_multiplier
    stop_distance_pct = stop_distance / entry_price
    if stop_distance_pct <= 0:
        return None

    return RiskLevels(
        stop_price=entry_price - stop_distance,
        target_price=entry_price + stop_distance * reward_risk_ratio,
        stop_distance_pct=stop_distance_pct,
    )


def position_size_pct(stop_distance_pct: float, risk_per_trade_pct: float = RISK_PER_TRADE_PCT) -> float | None:
    """Fixed-fractional sizing: how much of total equity to allocate so a
    full stop-out only loses risk_per_trade_pct of equity. Needs no account
    size at all -- safe to surface anywhere, including the public dashboard."""
    if stop_distance_pct <= 0:
        return None
    return min(risk_per_trade_pct / stop_distance_pct, MAX_POSITION_PCT)


def position_size_shares(equity: float, position_pct: float, entry_price: float) -> int:
    """Only meaningful once an actual account size is known (ACCOUNT_EQUITY
    env var). For the private Discord message only -- never pass this
    through to anything committed to the (public) repo."""
    if entry_price <= 0:
        return 0
    return int((equity * position_pct) // entry_price)


def parse_account_equity(raw: str | None) -> float | None:
    """ACCOUNT_EQUITY is an optional secret (same os.environ.get pattern as
    FINNHUB_API_KEY) -- absent by default, in which case position sizing
    stays in %-of-equity terms with no real dollar figure anywhere. Shared
    by every entry point that can compute a position size (live/run_check.py,
    scripts/scan_universe.py)."""
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if value > 0 else None
