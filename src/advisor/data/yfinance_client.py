import pandas as pd
import yfinance as yf

VIX_SYMBOL = "^VIX"
SPX_SYMBOL = "^GSPC"  # backtest benchmark: S&P 500 buy-and-hold


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
