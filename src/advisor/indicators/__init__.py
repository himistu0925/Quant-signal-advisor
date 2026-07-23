from . import (  # noqa: F401  (import registers plugins)
    adx,
    bollinger_bands,
    fibonacci,
    ichimoku,
    macd,
    moving_average,
    obv,
    rsi,
    stochastic,
    support_resistance,
    volume,
)
from .registry import get_core_registered, get_registered

__all__ = ["get_registered", "get_core_registered", "split_registered"]


def split_registered():
    """Volume (plan.md section 9) is a confidence multiplier, not a
    directional vote -- every caller that builds a scoring engine needs to
    pull it out of the registry separately, so that split lives here once.
    Only "core" indicators are included (see registry.register) -- unvalidated
    candidate indicators never silently join live/backtest scoring."""
    registered = dict(get_core_registered())
    volume_indicator = registered.pop("Volume", None)
    return registered, volume_indicator
