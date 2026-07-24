from advisor.backtest.calibration import CalibrationResult
from advisor.backtest.calibration_store import save_calibration, save_insufficient_data
from advisor.backtest.metrics import PerformanceMetrics
from advisor.dashboard.generate import build_dashboard_data, generate, render_html


def _write_watchlist(tmp_path, tickers):
    path = tmp_path / "watchlist.yaml"
    content = "tickers:\n" + "\n".join(f"  - {t}" for t in tickers) + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def _metrics(**overrides):
    base = dict(
        cumulative_return=0.15, cagr=0.10, max_drawdown=-0.05, sharpe_ratio=1.2,
        win_rate=0.6, avg_win_loss_ratio=1.5, total_trades=5, benchmark_return=0.08, excess_return=0.07,
    )
    base.update(overrides)
    return PerformanceMetrics(**base)


def test_build_dashboard_data_includes_calibrated_and_uncalibrated_tickers(tmp_path):
    watchlist_path = _write_watchlist(tmp_path, ["AAPL", "MSFT"])
    calibration_dir = tmp_path / "calibration"
    save_calibration(
        "AAPL",
        CalibrationResult(weights={"RSI": 1.0}, buy_threshold=2.0, sell_threshold=-2.0,
                           train_metrics=_metrics(), test_metrics=_metrics()),
        directory=calibration_dir,
    )
    history_path = tmp_path / "history.json"
    history_path.write_text(
        '[{"ticker": "AAPL", "direction": "BUY", "price": 100.0, "timestamp": "2026-07-23T10:00:00", "reasons": ["RSI=30"]}]',
        encoding="utf-8",
    )

    data = build_dashboard_data(watchlist_path, calibration_dir, history_path, tmp_path / "last_check.json")

    tickers_by_name = {t["ticker"]: t for t in data["tickers"]}
    assert tickers_by_name["AAPL"]["calibration"]["buy_threshold"] == 2.0
    assert tickers_by_name["MSFT"]["calibration"] is None
    assert len(data["recent_signals"]) == 1
    assert data["recent_signals"][0]["ticker"] == "AAPL"


def test_build_dashboard_data_marks_insufficient_data_ticker(tmp_path):
    watchlist_path = _write_watchlist(tmp_path, ["SPCX"])
    calibration_dir = tmp_path / "calibration"
    save_insufficient_data("SPCX", "only 27 bars available", directory=calibration_dir)

    data = build_dashboard_data(watchlist_path, calibration_dir, tmp_path / "history.json", tmp_path / "last_check.json")

    entry = data["tickers"][0]
    assert entry["calibration"]["status"] == "insufficient_data"
    assert "27 bars" in entry["calibration"]["reason"]


def test_render_html_shows_insufficient_data_message():
    data = {
        "generated_at": "2026-07-23T10:00:00",
        "tickers": [{"ticker": "SPCX", "calibration": {"status": "insufficient_data", "reason": "only 27 bars"}}],
        "recent_signals": [],
    }
    html = render_html(data)

    assert "SPCX" in html
    assert "데이터 부족" in html


def test_render_html_shows_top_weighted_indicators():
    data = {
        "generated_at": "2026-07-23T10:00:00",
        "tickers": [{
            "ticker": "TQQQ",
            "calibration": {
                "status": "calibrated",
                "weights": {"RSI": 3.0, "MACD": 2.0, "ADX": 0.0, "OBV": 0.0},
                "buy_threshold": 2.0, "sell_threshold": -2.0,
                "test_metrics": {
                    "cumulative_return": 0.1, "cagr": 0.1, "max_drawdown": -0.05, "sharpe_ratio": 1.0,
                    "win_rate": 0.5, "avg_win_loss_ratio": 1.0, "total_trades": 3,
                    "benchmark_return": 0.05, "excess_return": 0.05,
                },
            },
        }],
        "recent_signals": [],
    }
    html = render_html(data)

    assert "RSI(3.0)" in html
    assert "MACD(2.0)" in html
    assert "ADX" not in html  # zero-weight indicators are omitted


def test_render_html_shows_no_last_check_message_when_none():
    data = {"generated_at": "2026-07-23T10:00:00", "tickers": [], "recent_signals": [], "last_check": None}
    html = render_html(data)

    assert "아직 체크 기록이 없습니다" in html


def test_render_html_shows_market_closed_last_check():
    data = {
        "generated_at": "2026-07-23T10:00:00", "tickers": [], "recent_signals": [],
        "last_check": {"timestamp": "2026-07-23T17:41:00-04:00", "market_open": False, "tickers": {}},
    }
    html = render_html(data)

    assert "장 마감 시간이라 스킵됨" in html
    assert "2026-07-23T17:41:00-04:00" in html


def test_render_html_shows_ticker_scores_from_last_check():
    data = {
        "generated_at": "2026-07-23T10:00:00", "tickers": [], "recent_signals": [],
        "last_check": {
            "timestamp": "2026-07-23T13:58:00-04:00",
            "market_open": True,
            "tickers": {"TQQQ": {"score": 1.23, "direction": None, "threshold": None}},
        },
    }
    html = render_html(data)

    assert "TQQQ" in html
    assert "1.23" in html
    assert "중립" in html


def test_render_html_shows_no_signals_message_when_empty():
    data = {"generated_at": "2026-07-23T10:00:00", "tickers": [{"ticker": "AAPL", "calibration": None}], "recent_signals": []}
    html = render_html(data)

    assert "AAPL" in html
    assert "아직 발생한 신호가 없습니다" in html


def test_render_html_includes_calibration_metrics():
    data = {
        "generated_at": "2026-07-23T10:00:00",
        "tickers": [{
            "ticker": "AAPL",
            "calibration": {
                "status": "calibrated",
                "weights": {"RSI": 1.0}, "buy_threshold": 2.0, "sell_threshold": -2.0,
                "test_metrics": {
                    "cumulative_return": 0.15, "cagr": 0.1, "max_drawdown": -0.05, "sharpe_ratio": 1.2,
                    "win_rate": 0.6, "avg_win_loss_ratio": 1.5, "total_trades": 5,
                    "benchmark_return": 0.08, "excess_return": 0.07,
                },
            },
        }],
        "recent_signals": [],
    }
    html = render_html(data)

    assert "+2.0 / -2.0" in html
    assert "15.0%" in html


def test_build_dashboard_data_includes_universe_candidates(tmp_path):
    watchlist_path = _write_watchlist(tmp_path, ["AAPL"])
    candidates_path = tmp_path / "candidates.json"
    candidates_path.write_text(
        '[{"ticker": "NVDA", "name": "NVIDIA", "exchange": "NASDAQ", "direction": "BUY", '
        '"score": 4.5, "as_of": "2026-07-24T06:00:00+00:00"}]',
        encoding="utf-8",
    )

    data = build_dashboard_data(
        watchlist_path, tmp_path / "calibration", tmp_path / "history.json",
        tmp_path / "last_check.json", candidates_path,
    )

    assert data["universe_candidates"][0]["ticker"] == "NVDA"


def test_render_html_shows_universe_candidates_section():
    data = {
        "generated_at": "2026-07-23T10:00:00",
        "tickers": [], "recent_signals": [],
        "universe_candidates": [
            {"ticker": "NVDA", "name": "NVIDIA Corp", "exchange": "NASDAQ",
             "direction": "BUY", "score": 4.5, "as_of": "2026-07-24T06:00:00+00:00"},
        ],
    }
    html = render_html(data)

    assert "NVDA" in html
    assert "NVIDIA Corp" in html
    assert "2026-07-24T06:00:00+00:00" in html


def test_render_html_shows_no_candidates_message_when_empty():
    data = {"generated_at": "2026-07-23T10:00:00", "tickers": [], "recent_signals": [], "universe_candidates": []}
    html = render_html(data)

    assert "아직 발굴된 후보가 없습니다" in html


def test_generate_writes_index_html_and_data_json(tmp_path):
    watchlist_path = _write_watchlist(tmp_path, ["AAPL"])
    output_dir = tmp_path / "docs"

    generate(
        watchlist_path=watchlist_path,
        calibration_dir=tmp_path / "calibration",
        history_path=tmp_path / "history.json",
        last_check_path=tmp_path / "last_check.json",
        output_dir=output_dir,
    )

    assert (output_dir / "index.html").exists()
    assert (output_dir / "data.json").exists()
    assert "AAPL" in (output_dir / "index.html").read_text(encoding="utf-8")
