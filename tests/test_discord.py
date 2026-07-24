import pytest
import requests

from advisor.alerts import discord as discord_module
from advisor.alerts.discord import format_move_alert_message, format_signal_message, send_discord_alert


def test_format_signal_message_contains_key_fields():
    message = format_signal_message(
        ticker="AAPL",
        direction="BUY",
        price=224.15,
        timestamp_et="15:32 ET",
        reasons=["RSI 28.4(과매도)", "MACD 골든크로스"],
        vix_regime="중립",
        vix_percentile=52,
        score=5,
        threshold=4,
    )

    assert "BUY 신호 — AAPL" in message
    assert "$224.15" in message
    assert "15:32 ET" in message
    assert "RSI 28.4(과매도) · MACD 골든크로스" in message
    assert "VIX 필터: 중립 (52th pct)" in message
    assert "+5" in message and "+4" in message


def test_format_signal_message_handles_no_reasons():
    message = format_signal_message(
        ticker="AAPL", direction="SELL", price=100.0, timestamp_et="10:00 ET",
        reasons=[], vix_regime="neutral", vix_percentile=50, score=-3, threshold=-3,
    )
    assert "근거: N/A" in message


def test_format_signal_message_omits_risk_block_when_not_provided():
    message = format_signal_message(
        ticker="AAPL", direction="BUY", price=100.0, timestamp_et="10:00 ET",
        reasons=["RSI 28"], vix_regime="neutral", vix_percentile=50, score=5, threshold=3,
    )
    assert "손절" not in message


def test_format_signal_message_includes_risk_block_without_shares_by_default():
    message = format_signal_message(
        ticker="AAPL", direction="BUY", price=100.0, timestamp_et="10:00 ET",
        reasons=["RSI 28"], vix_regime="neutral", vix_percentile=50, score=5, threshold=3,
        stop_price=92.0, target_price=116.0, position_pct=0.05,
    )
    assert "손절: $92.00" in message
    assert "익절: $116.00" in message
    assert "제안 비중: 계좌의 5.0%" in message
    assert "주)" not in message  # no account size configured -> no share count


def test_format_signal_message_includes_shares_when_account_equity_known():
    message = format_signal_message(
        ticker="AAPL", direction="BUY", price=100.0, timestamp_et="10:00 ET",
        reasons=["RSI 28"], vix_regime="neutral", vix_percentile=50, score=5, threshold=3,
        stop_price=92.0, target_price=116.0, position_pct=0.05, shares=5,
    )
    assert "(~5주)" in message


def test_format_move_alert_message_labels_surge_and_plunge():
    surge = format_move_alert_message(
        ticker="AAPL", name="Apple Inc.", direction="SURGE", price=110.0,
        pct_change=0.062, timestamp_et="10:00 ET",
    )
    plunge = format_move_alert_message(
        ticker="AAPL", name="Apple Inc.", direction="PLUNGE", price=90.0,
        pct_change=-0.062, timestamp_et="10:00 ET",
    )

    assert "급등 알림 — AAPL (Apple Inc.)" in surge
    assert "+6.2%" in surge
    assert "급락 알림 — AAPL (Apple Inc.)" in plunge
    assert "-6.2%" in plunge


def test_format_move_alert_message_includes_scan_context_when_given():
    message = format_move_alert_message(
        ticker="AAPL", name="Apple Inc.", direction="SURGE", price=110.0,
        pct_change=0.062, timestamp_et="10:00 ET", scan_direction="BUY", scan_score=4.5,
    )
    assert "참고: 최근 발굴 스캔 스코어 BUY +4.5" in message


def test_format_move_alert_message_omits_risk_block_when_not_provided():
    message = format_move_alert_message(
        ticker="AAPL", name="Apple Inc.", direction="SURGE", price=110.0,
        pct_change=0.062, timestamp_et="10:00 ET",
    )
    assert "손절" not in message


def test_format_move_alert_message_includes_risk_block_when_provided():
    message = format_move_alert_message(
        ticker="AAPL", name="Apple Inc.", direction="SURGE", price=110.0,
        pct_change=0.062, timestamp_et="10:00 ET",
        stop_price=100.0, target_price=130.0, position_pct=0.1, shares=9,
    )
    assert "손절: $100.00" in message
    assert "익절: $130.00" in message
    assert "제안 비중: 계좌의 10.0%" in message
    assert "(~9주)" in message


def test_send_discord_alert_posts_content(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(discord_module.requests, "post", fake_post)

    send_discord_alert("https://discord.example/webhook", "hello")

    assert captured["url"] == "https://discord.example/webhook"
    assert captured["json"] == {"content": "hello"}


def test_send_discord_alert_raises_on_http_error(monkeypatch):
    class FailingResponse:
        def raise_for_status(self):
            raise requests.HTTPError("boom")

    def fake_post(url, json=None, timeout=None):
        return FailingResponse()

    monkeypatch.setattr(discord_module.requests, "post", fake_post)

    with pytest.raises(requests.HTTPError):
        send_discord_alert("https://discord.example/webhook", "hello")
