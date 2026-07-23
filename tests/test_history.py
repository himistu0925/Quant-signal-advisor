from advisor.alerts.history import append_signal_event, load_signal_history


def test_load_signal_history_missing_file_returns_empty(tmp_path):
    assert load_signal_history(tmp_path / "nope.json") == []


def test_append_and_load_roundtrip(tmp_path):
    path = tmp_path / "history.json"
    append_signal_event({"ticker": "AAPL", "direction": "BUY"}, path=path)
    append_signal_event({"ticker": "MSFT", "direction": "SELL"}, path=path)

    history = load_signal_history(path)
    assert len(history) == 2
    assert history[0]["ticker"] == "AAPL"
    assert history[1]["ticker"] == "MSFT"


def test_append_truncates_to_max_entries(tmp_path):
    path = tmp_path / "history.json"
    for i in range(5):
        append_signal_event({"i": i}, path=path, max_entries=3)

    history = load_signal_history(path)
    assert len(history) == 3
    assert [h["i"] for h in history] == [2, 3, 4]
