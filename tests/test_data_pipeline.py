import pandas as pd

from advisor.data import yfinance_client as yfc


class FakeTicker:
    def __init__(self, symbol):
        self.symbol = symbol

    def history(self, period=None, interval=None):
        return pd.DataFrame(
            {"Close": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3)
        )


def test_fetch_daily_uses_given_ticker(monkeypatch):
    captured = {}

    def fake_ticker(symbol):
        captured["symbol"] = symbol
        return FakeTicker(symbol)

    monkeypatch.setattr(yfc.yf, "Ticker", fake_ticker)
    df = yfc.fetch_daily("AAPL", period="5y")

    assert captured["symbol"] == "AAPL"
    assert list(df["Close"]) == [1, 2, 3]


def test_fetch_intraday_uses_given_ticker(monkeypatch):
    captured = {}

    def fake_ticker(symbol):
        captured["symbol"] = symbol
        return FakeTicker(symbol)

    monkeypatch.setattr(yfc.yf, "Ticker", fake_ticker)
    yfc.fetch_intraday("MSFT", period="60d", interval="15m")

    assert captured["symbol"] == "MSFT"


def test_fetch_vix_uses_caret_vix_symbol(monkeypatch):
    captured = {}

    def fake_ticker(symbol):
        captured["symbol"] = symbol
        return FakeTicker(symbol)

    monkeypatch.setattr(yfc.yf, "Ticker", fake_ticker)
    yfc.fetch_vix()

    assert captured["symbol"] == "^VIX"


def test_fetch_benchmark_uses_sp500_symbol(monkeypatch):
    captured = {}

    def fake_ticker(symbol):
        captured["symbol"] = symbol
        return FakeTicker(symbol)

    monkeypatch.setattr(yfc.yf, "Ticker", fake_ticker)
    yfc.fetch_benchmark()

    assert captured["symbol"] == "^GSPC"


# --- fetch_batch_daily -------------------------------------------------------


def test_fetch_batch_daily_parses_multi_ticker_response(monkeypatch):
    captured = {}

    def fake_download(tickers, **kwargs):
        captured["tickers"] = tickers
        captured["kwargs"] = kwargs
        return pd.concat(
            {
                "AAPL": pd.DataFrame({"Close": [1.0, 2.0], "Volume": [100, 200]}),
                "MSFT": pd.DataFrame({"Close": [3.0, 4.0], "Volume": [300, 400]}),
            },
            axis=1,
        )

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    result = yfc.fetch_batch_daily(["AAPL", "MSFT"], period="3mo")

    assert set(result.keys()) == {"AAPL", "MSFT"}
    assert list(result["AAPL"]["Close"]) == [1.0, 2.0]
    assert captured["kwargs"]["timeout"] == yfc.DEFAULT_BATCH_REQUEST_TIMEOUT_SECONDS


def test_fetch_batch_daily_drops_tickers_missing_from_response(monkeypatch):
    def fake_download(tickers, **kwargs):
        return pd.concat({"AAPL": pd.DataFrame({"Close": [1.0], "Volume": [100]})}, axis=1)

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    result = yfc.fetch_batch_daily(["AAPL", "DELISTED"], period="3mo")

    assert set(result.keys()) == {"AAPL"}


def test_fetch_batch_daily_drops_all_nan_ticker(monkeypatch):
    def fake_download(tickers, **kwargs):
        return pd.concat(
            {
                "AAPL": pd.DataFrame({"Close": [1.0], "Volume": [100]}),
                "STALE": pd.DataFrame({"Close": [float("nan")], "Volume": [float("nan")]}),
            },
            axis=1,
        )

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    result = yfc.fetch_batch_daily(["AAPL", "STALE"])

    assert set(result.keys()) == {"AAPL"}


def test_fetch_batch_daily_handles_single_ticker_flat_columns(monkeypatch):
    def fake_download(tickers, **kwargs):
        return pd.DataFrame({"Close": [1.0, 2.0], "Volume": [100, 200]})

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    result = yfc.fetch_batch_daily(["AAPL"], period="3mo")

    assert list(result["AAPL"]["Close"]) == [1.0, 2.0]


def test_fetch_batch_daily_skips_failed_chunk_but_keeps_processing_others(monkeypatch):
    calls = []

    def fake_download(tickers, **kwargs):
        calls.append(list(tickers))
        if tickers == ["BAD"]:
            raise TimeoutError("simulated network timeout")
        return pd.DataFrame({"Close": [1.0], "Volume": [100]})

    monkeypatch.setattr(yfc.yf, "download", fake_download)

    result = yfc.fetch_batch_daily(["BAD", "GOOD"], chunk_size=1, chunk_delay_seconds=0)

    assert "BAD" not in result
    assert "GOOD" in result
    assert len(calls) == 2  # the failed chunk didn't stop the second chunk from being attempted
