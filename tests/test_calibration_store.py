from advisor.backtest.calibration import CalibrationResult
from advisor.backtest.calibration_store import load_calibration, save_calibration
from advisor.backtest.metrics import PerformanceMetrics


def make_metrics(value):
    return PerformanceMetrics(
        cumulative_return=value,
        cagr=value,
        max_drawdown=-value,
        sharpe_ratio=value,
        win_rate=0.5,
        avg_win_loss_ratio=1.0,
        total_trades=2,
        benchmark_return=0.1,
        excess_return=value - 0.1,
    )


def test_save_and_load_calibration_roundtrip(tmp_path):
    result = CalibrationResult(
        weights={"RSI": 1.0, "MACD": 0.5},
        buy_threshold=3.0,
        sell_threshold=-3.0,
        train_metrics=make_metrics(0.2),
        test_metrics=make_metrics(0.1),
    )

    path = save_calibration("AAPL", result, directory=tmp_path)
    assert path.exists()

    loaded = load_calibration("AAPL", directory=tmp_path)

    assert loaded.weights == {"RSI": 1.0, "MACD": 0.5}
    assert loaded.buy_threshold == 3.0
    assert loaded.train_metrics.sharpe_ratio == 0.2
    assert loaded.test_metrics.total_trades == 2
