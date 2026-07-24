import json

from advisor.universe.listing import Listing
from advisor.universe.store import build_search_index, save_search_index

LISTINGS = [
    Listing(symbol="AAPL", name="Apple Inc. Common Stock", exchange="NASDAQ", is_etf=False),
    Listing(symbol="SPY", name="SPDR S&P 500 ETF Trust", exchange="NYSE Arca", is_etf=True),
]


def test_build_search_index_is_array_of_arrays():
    index = build_search_index(LISTINGS)
    assert index == [
        ["AAPL", "Apple Inc. Common Stock", "NASDAQ", 0],
        ["SPY", "SPDR S&P 500 ETF Trust", "NYSE Arca", 1],
    ]


def test_save_search_index_writes_json_file(tmp_path):
    path = tmp_path / "docs" / "tickers.json"
    save_search_index(LISTINGS, path=path)

    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == build_search_index(LISTINGS)
