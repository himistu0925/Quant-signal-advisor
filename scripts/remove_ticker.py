import sys

from advisor.backtest.calibration_store import delete_calibration
from advisor.watchlist import WatchlistError, remove_ticker

WATCHLIST_PATH = "config/watchlist.yaml"


def main() -> None:
    if len(sys.argv) != 2:
        print("::error::usage: remove_ticker.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1].strip().upper()

    try:
        updated = remove_ticker(WATCHLIST_PATH, ticker)
    except WatchlistError as e:
        print(f"::error::{e}")
        sys.exit(1)

    delete_calibration(ticker)
    print(f"{ticker}: removed. watchlist is now: {updated.tickers}")


if __name__ == "__main__":
    main()
