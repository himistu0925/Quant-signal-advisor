import pytest

from advisor.watchlist import WatchlistError, load_watchlist


def write_yaml(tmp_path, content):
    p = tmp_path / "watchlist.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def test_load_valid_watchlist_normalizes_case(tmp_path):
    p = write_yaml(tmp_path, "tickers:\n  - aapl\n  - MSFT\n")
    wl = load_watchlist(p)
    assert wl.tickers == ["AAPL", "MSFT"]


def test_max_tickers_enforced(tmp_path):
    p = write_yaml(tmp_path, "tickers:\n" + "\n".join(f"  - T{i}" for i in range(6)))
    with pytest.raises(WatchlistError):
        load_watchlist(p)


def test_exactly_five_tickers_allowed(tmp_path):
    p = write_yaml(tmp_path, "tickers:\n" + "\n".join(f"  - T{i}" for i in range(5)))
    wl = load_watchlist(p)
    assert len(wl.tickers) == 5


def test_empty_watchlist_rejected(tmp_path):
    p = write_yaml(tmp_path, "tickers: []")
    with pytest.raises(WatchlistError):
        load_watchlist(p)


def test_duplicate_tickers_rejected(tmp_path):
    p = write_yaml(tmp_path, "tickers:\n  - AAPL\n  - aapl\n")
    with pytest.raises(WatchlistError):
        load_watchlist(p)


def test_missing_file_raises(tmp_path):
    with pytest.raises(WatchlistError):
        load_watchlist(tmp_path / "nope.yaml")
