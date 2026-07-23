import json
from pathlib import Path

DEFAULT_HISTORY_PATH = Path("data/signal_history.json")


def load_signal_history(path: Path = DEFAULT_HISTORY_PATH) -> list:
    path = Path(path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def append_signal_event(event: dict, path: Path = DEFAULT_HISTORY_PATH, max_entries: int = 500) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    history = load_signal_history(path)
    history.append(event)
    history = history[-max_entries:]

    path.write_text(json.dumps(history, indent=2), encoding="utf-8")
