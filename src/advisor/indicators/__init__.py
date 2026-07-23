from . import (  # noqa: F401  (import registers plugins)
    bollinger_bands,
    fibonacci,
    ichimoku,
    macd,
    moving_average,
    rsi,
    support_resistance,
    volume,
)
from .registry import get_registered

__all__ = ["get_registered", "split_registered"]


def split_registered():
    """Volume (plan.md section 9) is a confidence multiplier, not a
    directional vote -- every caller that builds a scoring engine needs to
    pull it out of the registry separately, so that split lives here once."""
    registered = dict(get_registered())
    volume_indicator = registered.pop("Volume", None)
    return registered, volume_indicator
