import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .calibration import CalibrationResult
from .metrics import PerformanceMetrics

DEFAULT_CALIBRATION_DIR = Path("calibration")


@dataclass
class InsufficientDataMarker:
    """Persisted in place of a real CalibrationResult when there wasn't
    enough history to calibrate (see calibration.InsufficientDataError) --
    lets the dashboard say "데이터 부족" instead of looking identical to
    "just never calibrated yet"."""

    ticker: str
    reason: str


def save_calibration(ticker: str, result: CalibrationResult, directory: Path = DEFAULT_CALIBRATION_DIR) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{ticker}.json"

    payload = {
        "ticker": ticker,
        "weights": result.weights,
        "buy_threshold": result.buy_threshold,
        "sell_threshold": result.sell_threshold,
        "train_metrics": asdict(result.train_metrics),
        "test_metrics": asdict(result.test_metrics),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def save_insufficient_data(ticker: str, reason: str, directory: Path = DEFAULT_CALIBRATION_DIR) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{ticker}.json"

    payload = {"ticker": ticker, "status": "insufficient_data", "reason": reason}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_calibration(ticker: str, directory: Path = DEFAULT_CALIBRATION_DIR) -> CalibrationResult:
    """Assumes a full result -- raises KeyError if the file is actually an
    InsufficientDataMarker. Use load_calibration_entry when the ticker might
    not have a real calibration."""
    directory = Path(directory)
    payload = json.loads((directory / f"{ticker}.json").read_text(encoding="utf-8"))

    return CalibrationResult(
        weights=payload["weights"],
        buy_threshold=payload["buy_threshold"],
        sell_threshold=payload["sell_threshold"],
        train_metrics=PerformanceMetrics(**payload["train_metrics"]),
        test_metrics=PerformanceMetrics(**payload["test_metrics"]),
    )


def load_calibration_entry(ticker: str, directory: Path = DEFAULT_CALIBRATION_DIR):
    """Returns whichever was actually saved for this ticker: a full
    CalibrationResult or an InsufficientDataMarker. Raises FileNotFoundError
    if this ticker has never been calibrated at all."""
    directory = Path(directory)
    payload = json.loads((directory / f"{ticker}.json").read_text(encoding="utf-8"))

    if payload.get("status") == "insufficient_data":
        return InsufficientDataMarker(ticker=payload["ticker"], reason=payload.get("reason", ""))

    return CalibrationResult(
        weights=payload["weights"],
        buy_threshold=payload["buy_threshold"],
        sell_threshold=payload["sell_threshold"],
        train_metrics=PerformanceMetrics(**payload["train_metrics"]),
        test_metrics=PerformanceMetrics(**payload["test_metrics"]),
    )
