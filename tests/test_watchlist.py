import pytest

from advisor.watchlist import (
    MAX_TICKERS,
    Watchlist,
    WatchlistError,
    add_ticker,
    check_can_add,
    load_watchlist,
    remove_ticker,
)


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


def test_check_can_add_rejects_duplicate():
    wl = Watchlist(tickers=["AAPL"])
    with pytest.raises(WatchlistError):
        check_can_add(wl, "aapl")


def test_check_can_add_rejects_at_max():
    wl = Watchlist(tickers=[f"T{i}" for i in range(MAX_TICKERS)])
    with pytest.raises(WatchlistError):
        check_can_add(wl, "NEW")


def test_check_can_add_rejects_non_alpha():
    wl = Watchlist(tickers=["AAPL"])
    with pytest.raises(WatchlistError):
        check_can_add(wl, "BRK.B")


def test_check_can_add_returns_normalized_ticker():
    wl = Watchlist(tickers=["AAPL"])
    assert check_can_add(wl, " msft ") == "MSFT"


def test_add_ticker_appends_and_persists(tmp_path):
    p = write_yaml(tmp_path, "tickers:\n  - AAPL\n")
    updated = add_ticker(p, "msft")
    assert updated.tickers == ["AAPL", "MSFT"]
    assert load_watchlist(p).tickers == ["AAPL", "MSFT"]


def test_add_ticker_rejects_beyond_max(tmp_path):
    p = write_yaml(tmp_path, "tickers:\n" + "\n".join(f"  - T{i}" for i in range(MAX_TICKERS)))
    with pytest.raises(WatchlistError):
        add_ticker(p, "NEW")


def test_remove_ticker_removes_and_persists(tmp_path):
    p = write_yaml(tmp_path, "tickers:\n  - AAPL\n  - MSFT\n")
    updated = remove_ticker(p, "aapl")
    assert updated.tickers == ["MSFT"]
    assert load_watchlist(p).tickers == ["MSFT"]


def test_remove_ticker_rejects_unknown_ticker(tmp_path):
    p = write_yaml(tmp_path, "tickers:\n  - AAPL\n")
    with pytest.raises(WatchlistError):
        remove_ticker(p, "MSFT")


def test_remove_ticker_rejects_removing_last_ticker(tmp_path):
    p = write_yaml(tmp_path, "tickers:\n  - AAPL\n")
    with pytest.raises(WatchlistError):
        remove_ticker(p, "AAPL")
