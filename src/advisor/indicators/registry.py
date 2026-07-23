from .base import Indicator

_REGISTRY: dict[str, Indicator] = {}
_STATUS: dict[str, str] = {}


def register(indicator: Indicator, status: str = "core") -> Indicator:
    """status="core" is scored live/in backtests by default. status=
    "candidate" registers the plugin (so it's reachable for contribution
    analysis) without it joining live scoring -- plan.md section 7: new
    indicators are only promoted after their individual contribution is
    validated by backtest."""
    _REGISTRY[indicator.name] = indicator
    _STATUS[indicator.name] = status
    return indicator


def get_registered() -> dict[str, Indicator]:
    return dict(_REGISTRY)


def get_core_registered() -> dict[str, Indicator]:
    return {name: ind for name, ind in _REGISTRY.items() if _STATUS.get(name) == "core"}
