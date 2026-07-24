import pandas as pd

from advisor.universe import screen as screen_module
from advisor.universe.listing import Listing
from advisor.universe.screen import filter_by_liquidity, rank_candidates


def _listing(symbol, name="Name", exchange="NASDAQ", is_etf=False):
    return Listing(symbol=symbol, name=name, exchange=exchange, is_etf=is_etf)


def test_filter_by_liquidity_keeps_only_tickers_above_both_thresholds(monkeypatch):
    listings = [_listing("LIQUID"), _listing("THIN"), _listing("MISSING")]
    bars = {
        "LIQUID": pd.DataFrame({"Close": [100.0] * 10, "Volume": [1_000_000] * 10}),  # ~$100M/day
        "THIN": pd.DataFrame({"Close": [1.0] * 10, "Volume": [100] * 10}),  # ~$100/day
        # "MISSING" deliberately absent -- simulates a delisted/bad symbol yfinance couldn't fetch
    }
    monkeypatch.setattr(screen_module, "fetch_batch_daily", lambda tickers, period=None: bars)

    survivors = filter_by_liquidity(listings, min_price=5.0, min_avg_dollar_volume=1_000_000.0)

    assert [listing.symbol for listing in survivors] == ["LIQUID"]


def test_rank_candidates_excludes_watchlist_and_neutral_tickers(monkeypatch):
    listings = [_listing("BUYME"), _listing("WATCHED"), _listing("NEUTRAL")]
    bars = {
        "BUYME": pd.DataFrame({"Close": [1.0]}),
        "NEUTRAL": pd.DataFrame({"Close": [2.0]}),
        "WATCHED": pd.DataFrame({"Close": [1.0]}),
    }
    monkeypatch.setattr(screen_module, "fetch_batch_daily", lambda tickers, period=None: bars)

    def fake_score_ticker(df):
        price = df["Close"].iloc[-1]
        return ("BUY", 5.0, 3.0, ["reason"]) if price == 1.0 else (None, 0.0, None, [])

    monkeypatch.setattr(screen_module, "score_ticker", fake_score_ticker)

    candidates = rank_candidates(listings, exclude_tickers={"WATCHED"})

    assert [c.ticker for c in candidates] == ["BUYME"]  # WATCHED excluded, NEUTRAL has no signal


def test_rank_candidates_sorts_by_absolute_score_descending(monkeypatch):
    listings = [_listing("WEAK"), _listing("STRONG")]
    bars = {
        "WEAK": pd.DataFrame({"Close": [1.0]}),
        "STRONG": pd.DataFrame({"Close": [2.0]}),
    }
    monkeypatch.setattr(screen_module, "fetch_batch_daily", lambda tickers, period=None: bars)

    def fake_score_ticker(df):
        price = df["Close"].iloc[-1]
        return ("SELL", -8.0, -3.0, []) if price == 2.0 else ("BUY", 3.5, 3.0, [])

    monkeypatch.setattr(screen_module, "score_ticker", fake_score_ticker)

    candidates = rank_candidates(listings, top_n=10)

    assert [c.ticker for c in candidates] == ["STRONG", "WEAK"]  # |−8.0| > |3.5| regardless of direction


def test_rank_candidates_respects_top_n(monkeypatch):
    listings = [_listing("A"), _listing("B"), _listing("C")]
    bars = {name: pd.DataFrame({"Close": [1.0]}) for name in ["A", "B", "C"]}
    monkeypatch.setattr(screen_module, "fetch_batch_daily", lambda tickers, period=None: bars)
    monkeypatch.setattr(screen_module, "score_ticker", lambda df: ("BUY", 5.0, 3.0, []))

    candidates = rank_candidates(listings, top_n=2)

    assert len(candidates) == 2
