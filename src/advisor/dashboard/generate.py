import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from advisor.alerts.history import DEFAULT_HISTORY_PATH, load_signal_history
from advisor.backtest.calibration_store import (
    DEFAULT_CALIBRATION_DIR,
    InsufficientDataMarker,
    load_calibration_entry,
)
from advisor.watchlist import load_watchlist

DEFAULT_OUTPUT_DIR = Path("docs")


def build_dashboard_data(
    watchlist_path: str = "config/watchlist.yaml",
    calibration_dir=DEFAULT_CALIBRATION_DIR,
    history_path=DEFAULT_HISTORY_PATH,
    generated_at: datetime | None = None,
) -> dict:
    watchlist = load_watchlist(watchlist_path)

    tickers = []
    for ticker in watchlist.tickers:
        try:
            entry = load_calibration_entry(ticker, directory=calibration_dir)
        except FileNotFoundError:
            entry = None

        if entry is None:
            calibration_summary = None
        elif isinstance(entry, InsufficientDataMarker):
            calibration_summary = {"status": "insufficient_data", "reason": entry.reason}
        else:
            calibration_summary = {
                "status": "calibrated",
                "weights": entry.weights,
                "buy_threshold": entry.buy_threshold,
                "sell_threshold": entry.sell_threshold,
                "test_metrics": asdict(entry.test_metrics),
            }
        tickers.append({"ticker": ticker, "calibration": calibration_summary})

    history = load_signal_history(history_path)
    recent_signals = list(reversed(history[-50:]))

    return {
        "generated_at": (generated_at or datetime.now()).isoformat(),
        "tickers": tickers,
        "recent_signals": recent_signals,
    }


def _format_pct(value) -> str:
    return f"{value:.1%}" if isinstance(value, (int, float)) else "-"


def _top_indicators(weights: dict, n: int = 3) -> str:
    ranked = sorted(weights.items(), key=lambda kv: -kv[1])
    shown = [f"{name}({w:.1f})" for name, w in ranked[:n] if w > 0]
    return ", ".join(shown) if shown else "-"


def _watchlist_rows(tickers: list) -> str:
    rows = []
    for entry in tickers:
        ticker = entry["ticker"]
        calibration = entry["calibration"]
        if calibration is None:
            rows.append(f"<tr><td>{ticker}</td><td colspan='6'>캘리브레이션 없음 (기본값 사용)</td></tr>")
            continue
        if calibration["status"] == "insufficient_data":
            rows.append(f"<tr><td>{ticker}</td><td colspan='6'>데이터 부족 (상장 초기 등 — 기본값 사용)</td></tr>")
            continue

        m = calibration["test_metrics"]
        rows.append(
            "<tr>"
            f"<td>{ticker}</td>"
            f"<td>{calibration['buy_threshold']:+.1f} / {calibration['sell_threshold']:+.1f}</td>"
            f"<td>{_top_indicators(calibration['weights'])}</td>"
            f"<td>{_format_pct(m['cumulative_return'])}</td>"
            f"<td>{m['sharpe_ratio']:.2f}</td>"
            f"<td>{m['total_trades']}</td>"
            f"<td>{_format_pct(m['excess_return'])}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _signal_rows(signals: list) -> str:
    if not signals:
        return "<tr><td colspan='5'>아직 발생한 신호가 없습니다.</td></tr>"

    rows = []
    for s in signals:
        reasons = " · ".join(s.get("reasons", [])) or "-"
        rows.append(
            "<tr>"
            f"<td>{s.get('timestamp', '-')}</td>"
            f"<td>{s.get('ticker', '-')}</td>"
            f"<td>{s.get('direction', '-')}</td>"
            f"<td>${s.get('price', 0):.2f}</td>"
            f"<td>{reasons}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_html(data: dict) -> str:
    watchlist_rows = _watchlist_rows(data["tickers"])
    signal_rows = _signal_rows(data["recent_signals"])

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>퀀트 신호 어드바이저 대시보드</title>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 2rem auto; max-width: 900px; padding: 0 1rem; color: #1a1a1a; }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
  th {{ background: #f5f5f5; }}
  .meta {{ color: #666; font-size: 0.85rem; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #111; color: #eee; }}
    th {{ background: #222; }}
    th, td {{ border-color: #333; }}
  }}
</style>
</head>
<body>
<h1>퀀트 신호 어드바이저 대시보드</h1>
<p class="meta">생성 시각: {data['generated_at']}</p>

<h2>워치리스트 현황</h2>
<table>
<tr><th>종목</th><th>매수/매도 임계값</th><th>주요 지표</th><th>검증구간 누적수익</th><th>샤프비율</th><th>거래수</th><th>벤치마크 초과수익</th></tr>
{watchlist_rows}
</table>

<h2>최근 신호 히스토리</h2>
<table>
<tr><th>시각</th><th>종목</th><th>방향</th><th>가격</th><th>근거</th></tr>
{signal_rows}
</table>
</body>
</html>
"""


def generate(
    watchlist_path: str = "config/watchlist.yaml",
    calibration_dir=DEFAULT_CALIBRATION_DIR,
    history_path=DEFAULT_HISTORY_PATH,
    output_dir=DEFAULT_OUTPUT_DIR,
    generated_at: datetime | None = None,
) -> Path:
    data = build_dashboard_data(watchlist_path, calibration_dir, history_path, generated_at)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (output_dir / "index.html").write_text(render_html(data), encoding="utf-8")
    return output_dir


if __name__ == "__main__":
    generate()
