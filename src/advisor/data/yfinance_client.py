import time

import pandas as pd
import yfinance as yf

VIX_SYMBOL = "^VIX"
SPX_SYMBOL = "^GSPC"  # backtest benchmark: S&P 500 buy-and-hold
DEFAULT_BATCH_CHUNK_SIZE = 150
DEFAULT_BATCH_CHUNK_DELAY_SECONDS = 1.0


def fetch_daily(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Long-history daily OHLCV bars, used for backtesting/calibration."""
    return yf.Ticker(ticker).history(period=period, interval="1d")


def fetch_intraday(ticker: str, period: str = "60d", interval: str = "15m") -> pd.DataFrame:
    """Rolling intraday bars, used for live signal checks. yfinance caps
    15m/30m bars at ~60 days of history."""
    return yf.Ticker(ticker).history(period=period, interval=interval)


def fetch_vix(period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    return yf.Ticker(VIX_SYMBOL).history(period=period, interval=interval)


def fetch_benchmark(period: str = "5y", interval: str = "1d") -> pd.DataFrame:
    return yf.Ticker(SPX_SYMBOL).history(period=period, interval=interval)


def fetch_batch_daily(
    tickers: list[str],
    period: str = "3mo",
    chunk_size: int = DEFAULT_BATCH_CHUNK_SIZE,
    chunk_delay_seconds: float = DEFAULT_BATCH_CHUNK_DELAY_SECONDS,
) -> dict[str, pd.DataFrame]:
    """Batch daily-bar fetch for universe screening -- a one-ticker-at-a-time
    loop (fetch_daily) is far too slow and rate-limit-prone across thousands
    of tickers. Chunks the ticker list and pauses between chunks to stay
    polite to Yahoo's undocumented limits. Returns only the tickers that
    came back with usable (non-empty) data -- silently drops the rest,
    since a screen is expected to skip delisted/bad symbols."""
    results: dict[str, pd.DataFrame] = {}
    chunks = [tickers[i : i + chunk_size] for i in range(0, len(tickers), chunk_size)]

    for i, chunk in enumerate(chunks):
        data = yf.download(
            chunk, period=period, interval="1d", group_by="ticker",
            threads=True, progress=False, auto_adjust=False,
        )

        if isinstance(data.columns, pd.MultiIndex):
            available = set(data.columns.get_level_values(0))
            for ticker in chunk:
                if ticker not in available:
                    continue
                df = data[ticker].dropna(how="all")
                if not df.empty:
                    results[ticker] = df
        elif len(chunk) == 1:
            df = data.dropna(how="all")
            if not df.empty:
                results[chunk[0]] = df

        if i < len(chunks) - 1:
            time.sleep(chunk_delay_seconds)

    return results
