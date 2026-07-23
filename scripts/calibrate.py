from advisor.backtest.calibration import calibrate_ticker
from advisor.backtest.calibration_store import save_calibration
from advisor.data.yfinance_client import fetch_benchmark, fetch_daily
from advisor.watchlist import load_watchlist


def main() -> None:
    watchlist = load_watchlist("config/watchlist.yaml")
    benchmark = fetch_benchmark(period="5y")

    for ticker in watchlist.tickers:
        df = fetch_daily(ticker, period="5y")
        result = calibrate_ticker(df, benchmark)
        path = save_calibration(ticker, result)
        print(f"{ticker}: buy={result.buy_threshold} sell={result.sell_threshold} -> {path}")


if __name__ == "__main__":
    main()
