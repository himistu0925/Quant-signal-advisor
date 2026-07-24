import json
from dataclasses import asdict
from pathlib import Path

DEFAULT_CANDIDATES_PATH = Path("data/universe_candidates.json")
DEFAULT_SEARCH_INDEX_PATH = Path("docs/tickers.json")


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


def build_search_index(listings: list) -> list:
    """Array-of-arrays, not array-of-objects -- for ~12,480 rows this avoids
    repeating four JSON keys per row, meaningfully shrinking the file the
    dashboard's ticker search has to fetch."""
    return [[l.symbol, l.name, l.exchange, int(l.is_etf)] for l in listings]


def save_search_index(listings: list, path: Path = DEFAULT_SEARCH_INDEX_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_search_index(listings), separators=(",", ":")), encoding="utf-8")
