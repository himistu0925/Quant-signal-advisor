import sys

from advisor.backtest.calibration import InsufficientDataError, calibrate_ticker
from advisor.backtest.calibration_store import save_calibration, save_insufficient_data
from advisor.data.yfinance_client import fetch_benchmark, fetch_daily
from advisor.watchlist import WatchlistError, add_ticker, check_can_add, load_watchlist

WATCHLIST_PATH = "config/watchlist.yaml"
MIN_BARS_FOR_ADD = 30  # lower floor than calibrate_ticker's own ~100-bar/1y-span
                        # requirement -- just enough to say "yfinance actually
                        # has real data for this symbol" before spending tens
                        # of seconds on a full calibration run.


def main() -> None:
    if len(sys.argv) != 2:
        print("::error::usage: add_ticker.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1].strip().upper()

    try:
        check_can_add(load_watchlist(WATCHLIST_PATH), ticker)
    except WatchlistError as e:
        print(f"::error::{e}")
        sys.exit(1)

    df = fetch_daily(ticker, period="5y")
    if df is None or df.empty or len(df) < MIN_BARS_FOR_ADD:
        print(f"::error::{ticker}: no usable price data -- check the ticker symbol")
        sys.exit(1)

    benchmark = fetch_benchmark(period="5y")
    try:
        result = calibrate_ticker(df, benchmark)
        save_calibration(ticker, result)
        print(f"{ticker}: calibrated (buy={result.buy_threshold}, sell={result.sell_threshold})")
    except InsufficientDataError as e:
        # Not a reason to reject the add -- run_check.py already falls back
        # to equal weights + default +-3.0 thresholds for any ticker with no
        # real calibration on file, so the ticker is still fully usable.
        save_insufficient_data(ticker, str(e))
        print(f"{ticker}: added with default scoring (insufficient data to calibrate: {e})")

    updated = add_ticker(WATCHLIST_PATH, ticker)
    print(f"watchlist is now: {updated.tickers}")


if __name__ == "__main__":
    main()
