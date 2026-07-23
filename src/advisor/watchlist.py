from dataclasses import dataclass
from pathlib import Path

import yaml

MAX_TICKERS = 5


class WatchlistError(Exception):
    pass


@dataclass
class Watchlist:
    tickers: list[str]


def load_watchlist(path: str | Path) -> Watchlist:
    path = Path(path)
    if not path.exists():
        raise WatchlistError(f"watchlist file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_tickers = data.get("tickers") or []
    if not isinstance(raw_tickers, list):
        raise WatchlistError("'tickers' must be a list")

    tickers = [str(t).strip().upper() for t in raw_tickers if str(t).strip()]

    if len(tickers) == 0:
        raise WatchlistError("watchlist must contain at least one ticker")

    dupes = {t for t in tickers if tickers.count(t) > 1}
    if dupes:
        raise WatchlistError(f"duplicate tickers in watchlist: {sorted(dupes)}")

    if len(tickers) > MAX_TICKERS:
        raise WatchlistError(
            f"watchlist exceeds max of {MAX_TICKERS} tickers (got {len(tickers)})"
        )

    return Watchlist(tickers=tickers)
