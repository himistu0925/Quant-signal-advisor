import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_STATE_PATH = Path("state/cooldown.json")


@dataclass
class _CooldownEntry:
    direction: str
    timestamp: datetime


class CooldownTracker:
    """Plan.md section 9: suppress duplicate same-direction alerts until
    either the indicator reverses or cooldown_minutes passes. State is
    JSON-persisted because each GitHub Actions run starts a fresh
    container -- without this file, cooldown would reset every run."""

    def __init__(self, path: Path = DEFAULT_STATE_PATH, cooldown_minutes: int = 60):
        self.path = Path(path)
        self.cooldown_minutes = cooldown_minutes
        self._state: dict[str, _CooldownEntry] = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            ticker: _CooldownEntry(direction=v["direction"], timestamp=datetime.fromisoformat(v["timestamp"]))
            for ticker, v in raw.items()
        }

    def should_alert(self, ticker: str, direction: str, now: datetime) -> bool:
        prior = self._state.get(ticker)
        if prior is None:
            return True
        if prior.direction != direction:
            return True
        return now - prior.timestamp >= timedelta(minutes=self.cooldown_minutes)

    def record(self, ticker: str, direction: str, now: datetime) -> None:
        self._state[ticker] = _CooldownEntry(direction=direction, timestamp=now)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            ticker: {"direction": entry.direction, "timestamp": entry.timestamp.isoformat()}
            for ticker, entry in self._state.items()
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
