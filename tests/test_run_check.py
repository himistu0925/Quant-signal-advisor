from datetime import datetime

import pandas as pd
import pytest

from advisor.alerts.cooldown import CooldownTracker
from advisor.alerts.history import load_signal_history
from advisor.backtest.calibration import CalibrationResult
from advisor.backtest.metrics import PerformanceMetrics
from advisor.indicators.base import IndicatorResult
from advisor.live import run_check


class ConstantIndicator:
    def __init__(self, vote, name="Const"):
        self.vote = vote
        self.name = name

    def compute(self, df):
        return IndicatorResult(vote=self.vote, detail=f"{self.name}={self.vote}")


def _zero_metrics():
    return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0)


def _write_watchlist(tmp_path, tickers):
    path = tmp_path / "watchlist.yaml"
    content = "tickers:\n" + "\n".join(f"  - {t}" for t in tickers) + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def _raise_not_found(ticker):
    raise FileNotFoundError()


# --- score_ticker -----------------------------------------------------------


def test_score_ticker_buy_signal_with_default_weights(monkeypatch):
    directional = {"A": ConstantIndicator(1, "A"), "B": ConstantIndicator(1, "B"), "C": ConstantIndicator(1, "C")}
    monkeypatch.setattr(run_check, "split_registered", lambda: (directional, None))

    direction, score, threshold, reasons = run_check.score_ticker(pd.DataFrame({"Close": [1, 2, 3]}))

    assert direction == "BUY"
    assert score == 3
    assert threshold == run_check.DEFAULT_BUY_THRESHOLD
    assert len(reasons) == 3


def test_score_ticker_neutral_when_below_threshold(monkeypatch):
    directional = {"A": ConstantIndicator(1, "A")}
    monkeypatch.setattr(run_check, "split_registered", lambda: (directional, None))

    direction, score, threshold, reasons = run_check.score_ticker(pd.DataFrame({"Close": [1]}))

    assert direction is None
    assert score == 1


def test_score_ticker_applies_volume_multiplier(monkeypatch):
    directional = {"A": ConstantIndicator(1, "A"), "B": ConstantIndicator(1, "B")}
    volume = ConstantIndicator(1, "Volume")
    monkeypatch.setattr(run_check, "split_registered", lambda: (directional, volume))

    _, score, _, _ = run_check.score_ticker(pd.DataFrame({"Close": [1]}))

    assert score == pytest.approx(2 * run_check.VOLUME_MULTIPLIER)


def test_score_ticker_uses_calibration_weights_and_threshold(monkeypatch):
    directional = {"A": ConstantIndicator(1, "A")}
    monkeypatch.setattr(run_check, "split_registered", lambda: (directional, None))

    calibration = CalibrationResult(
        weights={"A": 5.0}, buy_threshold=4.0, sell_threshold=-4.0,
        train_metrics=_zero_metrics(), test_metrics=_zero_metrics(),
    )

    direction, score, threshold, _ = run_check.score_ticker(pd.DataFrame({"Close": [1]}), calibration=calibration)

    assert score == 5.0
    assert direction == "BUY"
    assert threshold == 4.0


def test_score_ticker_raises_buy_threshold_during_extreme_fear(monkeypatch):
    from advisor.market_signals.vix_filter import VixState

    directional = {"A": ConstantIndicator(3, "A")}
    monkeypatch.setattr(run_check, "split_registered", lambda: (directional, None))

    df = pd.DataFrame({"Close": [1]})
    calm = VixState(value=15, percentile=50, regime="neutral")
    fearful = VixState(value=40, percentile=95, regime="extreme_fear")

    direction_calm, _, threshold_calm, _ = run_check.score_ticker(df, vix_state=calm)
    direction_fearful, _, threshold_fearful, _ = run_check.score_ticker(df, vix_state=fearful)

    assert direction_calm == "BUY"
    assert threshold_calm == run_check.DEFAULT_BUY_THRESHOLD
    assert direction_fearful is None  # score(3) no longer clears the raised bar
    assert threshold_fearful is None  # no signal fired, so no threshold to report


def test_score_ticker_adds_news_sentiment_to_score(monkeypatch):
    directional = {"A": ConstantIndicator(1, "A")}
    monkeypatch.setattr(run_check, "split_registered", lambda: (directional, None))

    positive_news = IndicatorResult(vote=1, detail="News: positive")
    direction, score, _, reasons = run_check.score_ticker(
        pd.DataFrame({"Close": [1]}), news_result=positive_news
    )

    assert score == pytest.approx(1 + run_check.NEWS_SENTIMENT_WEIGHT)
    assert "News: positive" in reasons


# --- run() orchestration -----------------------------------------------------


def test_run_does_nothing_outside_market_hours(tmp_path, monkeypatch):
    called = {"score_ticker": False}
    monkeypatch.setattr(run_check, "is_market_open", lambda now: False)
    monkeypatch.setattr(run_check, "score_ticker", lambda *a, **k: called.__setitem__("score_ticker", True))

    run_check.run(
        watchlist_path=_write_watchlist(tmp_path, ["AAPL"]),
        now=datetime(2026, 7, 23, 20, 0),
        cooldown_path=tmp_path / "cooldown.json",
        history_path=tmp_path / "history.json",
        last_check_path=tmp_path / "last_check.json",
    )

    assert called["score_ticker"] is False
    assert not (tmp_path / "history.json").exists()

    from advisor.alerts.last_check import load_last_check

    last_check = load_last_check(tmp_path / "last_check.json")
    assert last_check["market_open"] is False


def test_run_sends_alert_and_records_history_on_buy_signal(tmp_path, monkeypatch):
    watchlist_path = _write_watchlist(tmp_path, ["AAPL"])
    monkeypatch.setattr(run_check, "is_market_open", lambda now: True)
    monkeypatch.setattr(run_check, "fetch_daily", lambda ticker, period="1y": pd.DataFrame({"Close": [100.0]}))
    monkeypatch.setattr(run_check, "fetch_vix", lambda period="1y": pd.DataFrame({"Close": [15.0] * 30}))
    monkeypatch.setattr(run_check, "load_calibration_entry", _raise_not_found)
    monkeypatch.setattr(run_check, "score_ticker", lambda *a, **k: ("BUY", 5.0, 3.0, ["reason1"]))
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")

    sent = []
    monkeypatch.setattr(run_check, "send_discord_alert", lambda url, message: sent.append((url, message)))

    now = datetime(2026, 7, 23, 10, 0)
    cooldown_path = tmp_path / "cooldown.json"
    history_path = tmp_path / "history.json"
    last_check_path = tmp_path / "last_check.json"

    run_check.run(
        watchlist_path=watchlist_path, now=now, cooldown_path=cooldown_path,
        history_path=history_path, last_check_path=last_check_path,
    )

    assert len(sent) == 1
    assert sent[0][0] == "https://discord.example/webhook"
    assert "AAPL" in sent[0][1]

    history = load_signal_history(history_path)
    assert len(history) == 1
    assert history[0]["ticker"] == "AAPL"
    assert history[0]["direction"] == "BUY"

    tracker = CooldownTracker(path=cooldown_path)
    assert tracker.should_alert("AAPL", "BUY", now) is False

    from advisor.alerts.last_check import load_last_check

    last_check = load_last_check(last_check_path)
    assert last_check["market_open"] is True
    assert last_check["tickers"]["AAPL"]["direction"] == "BUY"


def test_run_skips_discord_send_without_webhook_url_but_still_logs(tmp_path, monkeypatch):
    watchlist_path = _write_watchlist(tmp_path, ["AAPL"])
    monkeypatch.setattr(run_check, "is_market_open", lambda now: True)
    monkeypatch.setattr(run_check, "fetch_daily", lambda ticker, period="1y": pd.DataFrame({"Close": [100.0]}))
    monkeypatch.setattr(run_check, "fetch_vix", lambda period="1y": pd.DataFrame({"Close": [15.0] * 30}))
    monkeypatch.setattr(run_check, "load_calibration_entry", _raise_not_found)
    monkeypatch.setattr(run_check, "score_ticker", lambda *a, **k: ("BUY", 5.0, 3.0, ["reason1"]))
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)

    sent = []
    monkeypatch.setattr(run_check, "send_discord_alert", lambda url, message: sent.append((url, message)))

    history_path = tmp_path / "history.json"
    run_check.run(
        watchlist_path=watchlist_path,
        now=datetime(2026, 7, 23, 10, 0),
        cooldown_path=tmp_path / "cooldown.json",
        history_path=history_path,
        last_check_path=tmp_path / "last_check.json",
    )

    assert sent == []
    assert len(load_signal_history(history_path)) == 1


def test_run_suppresses_repeat_alert_within_cooldown(tmp_path, monkeypatch):
    watchlist_path = _write_watchlist(tmp_path, ["AAPL"])
    monkeypatch.setattr(run_check, "is_market_open", lambda now: True)
    monkeypatch.setattr(run_check, "fetch_daily", lambda ticker, period="1y": pd.DataFrame({"Close": [100.0]}))
    monkeypatch.setattr(run_check, "fetch_vix", lambda period="1y": pd.DataFrame({"Close": [15.0] * 30}))
    monkeypatch.setattr(run_check, "load_calibration_entry", _raise_not_found)
    monkeypatch.setattr(run_check, "score_ticker", lambda *a, **k: ("BUY", 5.0, 3.0, ["reason1"]))
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")

    sent = []
    monkeypatch.setattr(run_check, "send_discord_alert", lambda url, message: sent.append((url, message)))

    cooldown_path = tmp_path / "cooldown.json"
    history_path = tmp_path / "history.json"
    last_check_path = tmp_path / "last_check.json"

    run_check.run(watchlist_path=watchlist_path, now=datetime(2026, 7, 23, 10, 0), cooldown_path=cooldown_path, history_path=history_path, last_check_path=last_check_path)
    run_check.run(watchlist_path=watchlist_path, now=datetime(2026, 7, 23, 10, 15), cooldown_path=cooldown_path, history_path=history_path, last_check_path=last_check_path)

    assert len(sent) == 1
    assert len(load_signal_history(history_path)) == 1


def test_run_adds_atr_risk_levels_to_buy_signal_without_leaking_shares(tmp_path, monkeypatch):
    watchlist_path = _write_watchlist(tmp_path, ["AAPL"])
    monkeypatch.setattr(run_check, "is_market_open", lambda now: True)

    # Constant High=11/Low=9/Close=10 -> ATR(14) converges to 2.0 (see test_risk_atr.py),
    # so with the module's default 2.0x multiplier the stop distance is 4.0.
    df = pd.DataFrame({"High": [11.0] * 20, "Low": [9.0] * 20, "Close": [10.0] * 20})
    monkeypatch.setattr(run_check, "fetch_daily", lambda ticker, period="1y": df)
    monkeypatch.setattr(run_check, "fetch_vix", lambda period="1y": pd.DataFrame({"Close": [15.0] * 30}))
    monkeypatch.setattr(run_check, "load_calibration_entry", _raise_not_found)
    monkeypatch.setattr(run_check, "score_ticker", lambda *a, **k: ("BUY", 5.0, 3.0, ["reason1"]))
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    monkeypatch.setenv("ACCOUNT_EQUITY", "10000")

    sent = []
    monkeypatch.setattr(run_check, "send_discord_alert", lambda url, message: sent.append((url, message)))

    history_path = tmp_path / "history.json"
    run_check.run(
        watchlist_path=watchlist_path, now=datetime(2026, 7, 23, 10, 0),
        cooldown_path=tmp_path / "cooldown.json", history_path=history_path,
        last_check_path=tmp_path / "last_check.json",
    )

    message = sent[0][1]
    assert "손절: $6.00" in message and "익절: $18.00" in message
    assert "주)" in message  # ACCOUNT_EQUITY was set, so a share count is included here

    event = load_signal_history(history_path)[0]
    assert event["stop_price"] == pytest.approx(6.0)
    assert event["target_price"] == pytest.approx(18.0)
    assert event["position_pct"] is not None
    assert "shares" not in event  # data/signal_history.json is committed publicly -- never leak this


def test_run_omits_risk_fields_when_atr_not_yet_computable(tmp_path, monkeypatch):
    watchlist_path = _write_watchlist(tmp_path, ["AAPL"])
    monkeypatch.setattr(run_check, "is_market_open", lambda now: True)
    monkeypatch.setattr(run_check, "fetch_daily", lambda ticker, period="1y": pd.DataFrame({"Close": [100.0]}))
    monkeypatch.setattr(run_check, "fetch_vix", lambda period="1y": pd.DataFrame({"Close": [15.0] * 30}))
    monkeypatch.setattr(run_check, "load_calibration_entry", _raise_not_found)
    monkeypatch.setattr(run_check, "score_ticker", lambda *a, **k: ("BUY", 5.0, 3.0, ["reason1"]))
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    monkeypatch.delenv("ACCOUNT_EQUITY", raising=False)

    sent = []
    monkeypatch.setattr(run_check, "send_discord_alert", lambda url, message: sent.append((url, message)))

    history_path = tmp_path / "history.json"
    run_check.run(
        watchlist_path=watchlist_path, now=datetime(2026, 7, 23, 10, 0),
        cooldown_path=tmp_path / "cooldown.json", history_path=history_path,
        last_check_path=tmp_path / "last_check.json",
    )

    assert "손절" not in sent[0][1]
    event = load_signal_history(history_path)[0]
    assert event["stop_price"] is None
    assert event["position_pct"] is None


def test_run_treats_insufficient_data_marker_as_no_calibration(tmp_path, monkeypatch):
    from advisor.backtest.calibration_store import InsufficientDataMarker

    watchlist_path = _write_watchlist(tmp_path, ["SPCX"])
    monkeypatch.setattr(run_check, "is_market_open", lambda now: True)
    monkeypatch.setattr(run_check, "fetch_daily", lambda ticker, period="1y": pd.DataFrame({"Close": [100.0]}))
    monkeypatch.setattr(run_check, "fetch_vix", lambda period="1y": pd.DataFrame({"Close": [15.0] * 30}))
    monkeypatch.setattr(
        run_check, "load_calibration_entry",
        lambda ticker: InsufficientDataMarker(ticker=ticker, reason="only 27 bars available"),
    )

    captured_calibration = {}

    def fake_score_ticker(df, calibration=None, vix_state=None, news_result=None):
        captured_calibration["value"] = calibration
        return (None, 0.0, None, [])

    monkeypatch.setattr(run_check, "score_ticker", fake_score_ticker)

    run_check.run(
        watchlist_path=watchlist_path,
        now=datetime(2026, 7, 23, 10, 0),
        cooldown_path=tmp_path / "cooldown.json",
        history_path=tmp_path / "history.json",
        last_check_path=tmp_path / "last_check.json",
    )

    assert captured_calibration["value"] is None
