from datetime import datetime, time
from zoneinfo import ZoneInfo

NY_TZ = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


def is_market_open(now: datetime | None = None) -> bool:
    """Plan.md section 3: GitHub Actions cron is UTC-fixed and can't track
    DST, so the cron window is intentionally generous (see schedule.yml) and
    this function does the real regular-hours check in America/New_York.
    Market holidays are not modeled -- a known gap, not an oversight; a
    holiday will just trigger a run that finds no signals worth alerting."""
    if now is None:
        now = datetime.now(tz=NY_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=NY_TZ)
    else:
        now = now.astimezone(NY_TZ)

    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    return MARKET_OPEN <= now.time() <= MARKET_CLOSE
