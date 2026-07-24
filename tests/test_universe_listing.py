import requests

from advisor.universe.listing import _is_clean_symbol, _parse_nasdaq_listed, _parse_other_listed, fetch_us_listing

NASDAQ_FIXTURE = "\n".join(
    [
        "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares",
        "AAPL|Apple Inc. Common Stock|Q|N|N|100|N|N",
        "QQQ|Invesco QQQ Trust|Q|N|N|100|Y|N",
        "ZTEST|Test Issue|Q|Y|N|100|N|N",
        "ABC.W|Warrant|Q|N|N|100|N|N",
        "File Creation Time: 0101202600:00",
    ]
)

OTHER_FIXTURE = "\n".join(
    [
        "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol",
        "SPY|SPDR S&P 500 ETF Trust|P|SPY|Y|100|N|SPY",
        "BRK.A|Berkshire Hathaway|N|BRK.A|N|100|N|BRK.A",
        "TSTX|Test Security|N|TSTX|N|100|Y|TSTX",
        "File Creation Time: 0101202600:00",
    ]
)


def test_is_clean_symbol_rejects_special_characters_and_empty():
    assert _is_clean_symbol("AAPL") is True
    assert _is_clean_symbol("BRK.A") is False
    assert _is_clean_symbol("") is False


def test_parse_nasdaq_listed_drops_test_issues_and_dirty_symbols():
    listings = _parse_nasdaq_listed(NASDAQ_FIXTURE)
    symbols = {listing.symbol for listing in listings}

    assert symbols == {"AAPL", "QQQ"}  # ZTEST (test issue) and ABC.W (warrant) dropped
    qqq = next(listing for listing in listings if listing.symbol == "QQQ")
    assert qqq.is_etf is True
    assert qqq.exchange == "NASDAQ"


def test_parse_other_listed_maps_exchange_codes_and_drops_test_issues():
    listings = _parse_other_listed(OTHER_FIXTURE)
    symbols = {listing.symbol for listing in listings}

    assert symbols == {"SPY"}  # BRK.A dropped for the dot, TSTX dropped as a test issue
    spy = listings[0]
    assert spy.exchange == "NYSE Arca"
    assert spy.is_etf is True


def test_fetch_us_listing_combines_both_sources(monkeypatch):
    class FakeResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

    def fake_get(url, timeout=None):
        return FakeResponse(NASDAQ_FIXTURE) if "nasdaqlisted" in url else FakeResponse(OTHER_FIXTURE)

    monkeypatch.setattr(requests, "get", fake_get)

    symbols = [listing.symbol for listing in fetch_us_listing()]

    assert "AAPL" in symbols and "QQQ" in symbols
    assert "SPY" in symbols
    assert "BRK.A" not in symbols and "ZTEST" not in symbols and "TSTX" not in symbols
