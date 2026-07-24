from advisor.alerts.last_check import load_last_check, save_last_check


def test_load_last_check_missing_file_returns_none(tmp_path):
    assert load_last_check(tmp_path / "nope.json") is None


def test_save_and_load_roundtrip_market_open(tmp_path):
    path = tmp_path / "last_check.json"
    save_last_check(
        "2026-07-23T13:58:00-04:00",
        market_open=True,
        tickers={"AAPL": {"score": 1.5, "direction": None, "threshold": None}},
        path=path,
    )

    loaded = load_last_check(path)
    assert loaded["market_open"] is True
    assert loaded["timestamp"] == "2026-07-23T13:58:00-04:00"
    assert loaded["tickers"]["AAPL"]["score"] == 1.5


def test_save_market_closed_defaults_empty_tickers(tmp_path):
    path = tmp_path / "last_check.json"
    save_last_check("2026-07-23T20:00:00-04:00", market_open=False, path=path)

    loaded = load_last_check(path)
    assert loaded["market_open"] is False
    assert loaded["tickers"] == {}
