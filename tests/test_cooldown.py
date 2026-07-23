from datetime import datetime, timedelta

from advisor.alerts.cooldown import CooldownTracker


def test_first_signal_is_always_allowed(tmp_path):
    tracker = CooldownTracker(path=tmp_path / "cooldown.json", cooldown_minutes=60)
    now = datetime(2026, 7, 23, 10, 0)
    assert tracker.should_alert("AAPL", "BUY", now) is True


def test_same_direction_within_window_is_suppressed(tmp_path):
    tracker = CooldownTracker(path=tmp_path / "cooldown.json", cooldown_minutes=60)
    now = datetime(2026, 7, 23, 10, 0)
    tracker.record("AAPL", "BUY", now)

    later = now + timedelta(minutes=30)
    assert tracker.should_alert("AAPL", "BUY", later) is False


def test_same_direction_after_window_is_allowed(tmp_path):
    tracker = CooldownTracker(path=tmp_path / "cooldown.json", cooldown_minutes=60)
    now = datetime(2026, 7, 23, 10, 0)
    tracker.record("AAPL", "BUY", now)

    later = now + timedelta(minutes=61)
    assert tracker.should_alert("AAPL", "BUY", later) is True


def test_direction_reversal_is_always_allowed(tmp_path):
    tracker = CooldownTracker(path=tmp_path / "cooldown.json", cooldown_minutes=60)
    now = datetime(2026, 7, 23, 10, 0)
    tracker.record("AAPL", "BUY", now)

    later = now + timedelta(minutes=1)
    assert tracker.should_alert("AAPL", "SELL", later) is True


def test_state_persists_across_instances(tmp_path):
    path = tmp_path / "cooldown.json"
    now = datetime(2026, 7, 23, 10, 0)

    tracker = CooldownTracker(path=path, cooldown_minutes=60)
    tracker.record("AAPL", "BUY", now)
    tracker.save()

    reloaded = CooldownTracker(path=path, cooldown_minutes=60)
    later = now + timedelta(minutes=5)
    assert reloaded.should_alert("AAPL", "BUY", later) is False
