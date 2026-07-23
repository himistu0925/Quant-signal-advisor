from .base import Indicator

_REGISTRY: dict[str, Indicator] = {}


def register(indicator: Indicator) -> Indicator:
    _REGISTRY[indicator.name] = indicator
    return indicator


def get_registered() -> dict[str, Indicator]:
    return dict(_REGISTRY)
