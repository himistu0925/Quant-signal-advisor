from advisor.backtest.calibration import InsufficientDataError, calibrate_ticker
from advisor.backtest.calibration_store import save_calibration, save_insufficient_data
from advisor.data.yfinance_client import fetch_benchmark, fetch_daily
from advisor.watchlist import load_watchlist


def main() -> None:
    watchlist = load_watchlist("config/watchlist.yaml")
    benchmark = fetch_benchmark(period="5y")

    for ticker in watchlist.tickers:
        df = fetch_daily(ticker, period="5y")

        try:
            result = calibrate_ticker(df, benchmark)
        except InsufficientDataError as e:
            path = save_insufficient_data(ticker, str(e))
            print(f"{ticker}: skipped calibration ({e}) -> {path}")
            continue

        path = save_calibration(ticker, result)
        print(f"{ticker}: buy={result.buy_threshold} sell={result.sell_threshold} -> {path}")

        ranked = sorted(result.weights.items(), key=lambda kv: -kv[1])
        weight_summary = ", ".join(f"{name}={w:.2f}" for name, w in ranked)
        print(f"  weights: {weight_summary}")


if __name__ == "__main__":
    main()
