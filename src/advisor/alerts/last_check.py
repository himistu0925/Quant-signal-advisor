import json
from pathlib import Path

DEFAULT_LAST_CHECK_PATH = Path("state/last_check.json")


def save_last_check(
    timestamp: str,
    market_open: bool,
    tickers: dict | None = None,
    path: Path = DEFAULT_LAST_CHECK_PATH,
) -> None:
    """Persisted on every run() call, market hours or not -- lets the
    dashboard show exactly when the workflow last actually executed
    (distinguishing "checked and found nothing" from "hasn't run"), which
    matters because GitHub's cron scheduler silently drops most fires of a
    frequent schedule (see schedule.yml)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp": timestamp, "market_open": market_open, "tickers": tickers or {}}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_last_check(path: Path = DEFAULT_LAST_CHECK_PATH) -> dict | None:
    path = Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
