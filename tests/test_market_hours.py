from datetime import datetime
from zoneinfo import ZoneInfo

from advisor.alerts.market_hours import is_market_open

NY_TZ = ZoneInfo("America/New_York")


def test_weekday_during_regular_hours_is_open():
    now = datetime(2026, 7, 23, 10, 0, tzinfo=NY_TZ)  # Thursday, 10:00 ET
    assert is_market_open(now) is True


def test_weekday_before_open_is_closed():
    now = datetime(2026, 7, 23, 9, 0, tzinfo=NY_TZ)
    assert is_market_open(now) is False


def test_weekday_after_close_is_closed():
    now = datetime(2026, 7, 23, 17, 0, tzinfo=NY_TZ)
    assert is_market_open(now) is False


def test_weekend_is_closed():
    now = datetime(2026, 7, 25, 10, 0, tzinfo=NY_TZ)  # Saturday
    assert is_market_open(now) is False


def test_naive_datetime_is_treated_as_ny_time():
    now = datetime(2026, 7, 23, 10, 0)  # naive, no tzinfo
    assert is_market_open(now) is True


def test_other_timezone_is_converted_to_ny():
    utc_open = datetime(2026, 7, 23, 14, 0, tzinfo=ZoneInfo("UTC"))  # 10:00 ET (EDT, UTC-4)
    assert is_market_open(utc_open) is True
