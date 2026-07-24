import json
from dataclasses import asdict
from pathlib import Path

DEFAULT_CANDIDATES_PATH = Path("data/universe_candidates.json")


def load_candidates(path: Path = DEFAULT_CANDIDATES_PATH) -> list:
    path = Path(path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_candidates(candidates: list, as_of: str, path: Path = DEFAULT_CANDIDATES_PATH) -> None:
    """candidates is a list[universe.screen.Candidate], typed loosely as
    `list` here (not importing Candidate) to avoid a circular import --
    screen.py imports live.run_check.score_ticker, and run_check.py in turn
    reads this candidates file to check for sharp intraday moves (movers.py).

    Only ever called after a fully successful scan -- a partial/failed run
    should leave the previous scan's candidates in place rather than
    overwrite them with an incomplete result (mirrors calibration_store's
    insufficient-data handling elsewhere in this project)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [{**asdict(candidate), "as_of": as_of} for candidate in candidates]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
