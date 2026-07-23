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
