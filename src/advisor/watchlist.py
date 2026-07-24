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


def check_can_add(watchlist: Watchlist, ticker: str) -> str:
    """Pure validation, no I/O -- lets callers reject a bad add request
    before paying for a network fetch or a full calibration run."""
    ticker = ticker.strip().upper()
    if not ticker.isalpha():
        raise WatchlistError(f"'{ticker}' is not a valid ticker symbol")
    if ticker in watchlist.tickers:
        raise WatchlistError(f"{ticker} is already in the watchlist")
    if len(watchlist.tickers) >= MAX_TICKERS:
        raise WatchlistError(f"watchlist is already at the max of {MAX_TICKERS} tickers")
    return ticker


def save_watchlist(path: str | Path, watchlist: Watchlist) -> None:
    Path(path).write_text(
        yaml.safe_dump({"tickers": watchlist.tickers}, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def add_ticker(path: str | Path, ticker: str) -> Watchlist:
    """Re-reads the file fresh and re-validates immediately before writing --
    safe to call even if check_can_add() was already checked earlier (e.g.
    before an expensive calibration run), since the file may have changed
    in the meantime."""
    watchlist = load_watchlist(path)
    ticker = check_can_add(watchlist, ticker)
    updated = Watchlist(tickers=watchlist.tickers + [ticker])
    save_watchlist(path, updated)
    return updated


def remove_ticker(path: str | Path, ticker: str) -> Watchlist:
    watchlist = load_watchlist(path)
    ticker = ticker.strip().upper()
    if ticker not in watchlist.tickers:
        raise WatchlistError(f"{ticker} is not in the watchlist")
    remaining = [t for t in watchlist.tickers if t != ticker]
    if not remaining:
        raise WatchlistError("cannot remove the last remaining ticker")
    updated = Watchlist(tickers=remaining)
    save_watchlist(path, updated)
    return updated
