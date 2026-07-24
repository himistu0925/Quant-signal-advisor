import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from advisor.alerts.history import DEFAULT_HISTORY_PATH, load_signal_history
from advisor.alerts.last_check import DEFAULT_LAST_CHECK_PATH, load_last_check
from advisor.backtest.calibration_store import (
    DEFAULT_CALIBRATION_DIR,
    InsufficientDataMarker,
    load_calibration_entry,
)
from advisor.universe.store import DEFAULT_CANDIDATES_PATH, load_candidates
from advisor.watchlist import load_watchlist

DEFAULT_OUTPUT_DIR = Path("docs")


def build_dashboard_data(
    watchlist_path: str = "config/watchlist.yaml",
    calibration_dir=DEFAULT_CALIBRATION_DIR,
    history_path=DEFAULT_HISTORY_PATH,
    last_check_path=DEFAULT_LAST_CHECK_PATH,
    candidates_path=DEFAULT_CANDIDATES_PATH,
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
        "last_check": load_last_check(last_check_path),
        "universe_candidates": load_candidates(candidates_path),
    }


def _format_pct(value) -> str:
    return f"{value:.1%}" if isinstance(value, (int, float)) else "-"


def _top_indicators(weights: dict, n: int = 3) -> str:
    ranked = sorted(weights.items(), key=lambda kv: -kv[1])
    shown = [f"{name}({w:.1f})" for name, w in ranked[:n] if w > 0]
    return ", ".join(shown) if shown else "-"


def _direction_badge(direction: str) -> str:
    cls = {"BUY": "badge-buy", "SELL": "badge-sell"}.get(direction, "badge-neutral")
    return f'<span class="badge {cls}">{direction}</span>'


def _remove_button(ticker: str) -> str:
    return f'<button class="btn-remove" data-ticker="{ticker}">삭제</button>'


def _watchlist_rows(tickers: list) -> str:
    rows = []
    for entry in tickers:
        ticker = entry["ticker"]
        calibration = entry["calibration"]
        if calibration is None:
            rows.append(
                f"<tr><td>{ticker}</td><td colspan='6'>캘리브레이션 없음 (기본값 사용)</td>"
                f"<td>{_remove_button(ticker)}</td></tr>"
            )
            continue
        if calibration["status"] == "insufficient_data":
            rows.append(
                f"<tr><td>{ticker}</td><td colspan='6'>데이터 부족 (상장 초기 등 — 기본값 사용)</td>"
                f"<td>{_remove_button(ticker)}</td></tr>"
            )
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
            f"<td>{_remove_button(ticker)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _last_check_section(last_check: dict | None) -> str:
    if last_check is None:
        return "<p>아직 체크 기록이 없습니다.</p>"

    timestamp = last_check.get("timestamp", "-")
    if not last_check.get("market_open"):
        return f"<p>마지막 워크플로 실행: {timestamp} (장 마감 시간이라 스킵됨)</p>"

    tickers = last_check.get("tickers", {})
    if not tickers:
        return f"<p>마지막 체크: {timestamp} (워치리스트 비어 있음)</p>"

    rows = []
    for ticker, info in tickers.items():
        direction = info.get("direction") or "중립"
        score = info.get("score")
        score_str = f"{score:.2f}" if isinstance(score, (int, float)) else "-"
        rows.append(f"<tr><td>{ticker}</td><td>{score_str}</td><td>{_direction_badge(direction)}</td></tr>")

    return (
        f"<p>마지막 체크: {timestamp}</p>"
        "<table>"
        "<tr><th>종목</th><th>현재 스코어</th><th>방향</th></tr>"
        f"{''.join(rows)}"
        "</table>"
    )


def _risk_cell(s: dict) -> str:
    # %-based only, by design -- signal_history.json is committed to the
    # public repo, so no dollar amount or share count ever lands here.
    stop, target, position_pct = s.get("stop_price"), s.get("target_price"), s.get("position_pct")
    if stop is None or target is None or position_pct is None:
        return "-"
    return f"손절 ${stop:.2f} / 익절 ${target:.2f} ({position_pct:.1%})"


def _signal_rows(signals: list) -> str:
    if not signals:
        return "<tr><td colspan='6'>아직 발생한 신호가 없습니다.</td></tr>"

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
            f"<td>{_risk_cell(s)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _candidates_rows(candidates: list) -> str:
    if not candidates:
        return "<tr><td colspan='6'>아직 발굴된 후보가 없습니다.</td></tr>"

    rows = []
    for c in candidates:
        rows.append(
            "<tr>"
            f"<td>{c.get('ticker', '-')}</td>"
            f"<td>{c.get('name', '-')}</td>"
            f"<td>{c.get('exchange', '-')}</td>"
            f"<td>{c.get('direction', '-')}</td>"
            f"<td>{c.get('score', 0):+.2f}</td>"
            f"<td>{_risk_cell(c)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


# Built as a plain (non-f) string, not an f-string: the JS below is full of
# literal `{`/`}` (object literals, template-literal `${...}` interpolation)
# that would otherwise all need doubling to survive Python's f-string
# parsing. __CURRENT_WATCHLIST__ is substituted via a plain .replace() call
# instead, so none of that escaping is needed.
_INTERACTIVE_PANEL_TEMPLATE = """
<h2>워치리스트 관리</h2>
<details>
  <summary>⚙ 설정 (GitHub 토큰)</summary>
  <p class="meta">
    종목 추가/삭제를 실제로 저장소에 반영하려면 이 저장소 전용 GitHub Fine-grained
    Personal Access Token이 필요합니다 (Contents: Read/Write, Actions: Read/Write).
    토큰은 이 브라우저에만 저장되고 서버로 전송되지 않습니다.
  </p>
  <input type="password" id="pat-input" placeholder="github_pat_...">
  <button id="pat-save">저장</button>
  <button id="pat-clear">삭제</button>
  <p class="meta" id="pat-status"></p>
</details>

<div class="search-panel">
  <input type="text" id="ticker-search" placeholder="티커 또는 종목명 검색 (예: AAPL, Apple)">
  <div id="search-results"></div>
</div>

<div id="op-status"></div>

<script>
const OWNER = "himistu0925";
const REPO = "Quant-signal-advisor";
const MAX_TICKERS = 5;
const CURRENT_WATCHLIST = __CURRENT_WATCHLIST__;
const API = `https://api.github.com/repos/${OWNER}/${REPO}`;

function getPat() { return localStorage.getItem("qsa_gh_pat") || ""; }

document.getElementById("pat-save").addEventListener("click", () => {
  const v = document.getElementById("pat-input").value.trim();
  if (!v) return;
  localStorage.setItem("qsa_gh_pat", v);
  document.getElementById("pat-input").value = "";
  document.getElementById("pat-status").textContent = "토큰이 저장되었습니다.";
});
document.getElementById("pat-clear").addEventListener("click", () => {
  localStorage.removeItem("qsa_gh_pat");
  document.getElementById("pat-status").textContent = "토큰이 삭제되었습니다.";
});

async function ghFetch(path, options) {
  options = options || {};
  const pat = getPat();
  if (!pat) throw new Error("먼저 위 설정에서 GitHub 토큰을 등록해주세요.");
  const headers = Object.assign(
    {
      "Authorization": `Bearer ${pat}`,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    options.body ? { "Content-Type": "application/json" } : {},
    options.headers || {}
  );
  return fetch(`${API}${path}`, Object.assign({}, options, { headers }));
}

function showStatus(html) {
  const el = document.getElementById("op-status");
  el.classList.add("visible");
  el.innerHTML = html;
}

async function dispatchAndPoll(workflow, ticker, button) {
  button.disabled = true;
  showStatus(`⏳ ${ticker} 처리 중... (보통 1~3분 정도 걸려요)`);
  try {
    const dispatchRes = await ghFetch(`/actions/workflows/${workflow}/dispatches`, {
      method: "POST",
      body: JSON.stringify({ ref: "master", inputs: { ticker: ticker }, return_run_details: true }),
    });
    if (!dispatchRes.ok && dispatchRes.status !== 204) {
      const err = await dispatchRes.text();
      throw new Error(`실행 요청 실패 (${dispatchRes.status}): ${err}`);
    }

    let runId = null;
    if (dispatchRes.status === 200) {
      const body = await dispatchRes.json();
      runId = body.workflow_run_id;
    }

    if (!runId) {
      // Defensive fallback for older API behavior (bare 204, no run id):
      // find the newest run created at/after dispatch time.
      const dispatchedAt = Date.now();
      for (let i = 0; i < 10 && !runId; i++) {
        await new Promise(r => setTimeout(r, 3000));
        const runsRes = await ghFetch(`/actions/workflows/${workflow}/runs?event=workflow_dispatch&per_page=5`);
        const runsBody = await runsRes.json();
        const fresh = (runsBody.workflow_runs || []).find(r => new Date(r.created_at).getTime() >= dispatchedAt - 5000);
        if (fresh) runId = fresh.id;
      }
      if (!runId) throw new Error("실행을 찾지 못했습니다. GitHub Actions 탭에서 직접 확인해주세요.");
    }

    const deadline = Date.now() + 5 * 60 * 1000;
    let run = null;
    while (Date.now() < deadline) {
      const runRes = await ghFetch(`/actions/runs/${runId}`);
      run = await runRes.json();
      if (run.status === "completed") break;
      await new Promise(r => setTimeout(r, 4000));
    }

    if (!run || run.status !== "completed") {
      showStatus(`⏱ 시간이 오래 걸리고 있어요. <a href="https://github.com/${OWNER}/${REPO}/actions" target="_blank">Actions 탭</a>에서 직접 확인해주세요.`);
      return;
    }

    if (run.conclusion === "success") {
      showStatus(`✅ ${ticker} 처리 완료! <button onclick="location.reload()">새로고침</button>`);
    } else {
      showStatus(`❌ 실패했습니다. <a href="${run.html_url}" target="_blank">실행 로그 보기</a>`);
    }
  } catch (e) {
    showStatus(`❌ 오류: ${e.message}`);
  } finally {
    button.disabled = false;
  }
}

document.querySelectorAll(".btn-remove").forEach(btn => {
  btn.addEventListener("click", () => dispatchAndPoll("remove_ticker.yml", btn.dataset.ticker, btn));
});

let tickerIndex = null;
async function loadTickerIndex() {
  if (tickerIndex) return tickerIndex;
  const res = await fetch("tickers.json");
  tickerIndex = await res.json();
  return tickerIndex;
}

const searchInput = document.getElementById("ticker-search");
const resultsEl = document.getElementById("search-results");
searchInput.addEventListener("input", async () => {
  const q = searchInput.value.trim().toUpperCase();
  resultsEl.innerHTML = "";
  if (!q) return;
  const index = await loadTickerIndex();
  const matches = index.filter(row => row[0].startsWith(q) || row[1].toUpperCase().includes(q)).slice(0, 20);
  for (const [sym, name, exchange] of matches) {
    const row = document.createElement("div");
    row.className = "result-row";
    const already = CURRENT_WATCHLIST.includes(sym);
    const full = CURRENT_WATCHLIST.length >= MAX_TICKERS;
    const label = already ? "이미 있음" : (full ? "5개 꽉 참" : "추가");
    const disabledAttr = (already || full) ? "disabled" : "";
    row.innerHTML = `<span>${sym} — ${name} (${exchange})</span><button class="btn-add" data-ticker="${sym}" ${disabledAttr}>${label}</button>`;
    resultsEl.appendChild(row);
  }
  resultsEl.querySelectorAll(".btn-add").forEach(btn => {
    btn.addEventListener("click", () => dispatchAndPoll("add_ticker.yml", btn.dataset.ticker, btn));
  });
});
</script>
"""


def _interactive_panel(current_tickers: list) -> str:
    return _INTERACTIVE_PANEL_TEMPLATE.replace("__CURRENT_WATCHLIST__", json.dumps(current_tickers))


def render_html(data: dict) -> str:
    watchlist_rows = _watchlist_rows(data["tickers"])
    signal_rows = _signal_rows(data["recent_signals"])
    last_check_section = _last_check_section(data.get("last_check"))
    candidates = data.get("universe_candidates") or []
    candidates_rows = _candidates_rows(candidates)
    candidates_as_of = candidates[0].get("as_of", "-") if candidates else "-"
    interactive_panel = _interactive_panel([t["ticker"] for t in data["tickers"]])

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
  .badge {{ display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }}
  .badge-buy {{ background: #d1fae5; color: #065f46; }}
  .badge-sell {{ background: #fee2e2; color: #991b1b; }}
  .badge-neutral {{ background: #e5e7eb; color: #374151; }}
  button {{ cursor: pointer; border: 1px solid #ccc; background: #fff; border-radius: 6px; padding: 0.3rem 0.8rem; font-size: 0.85rem; }}
  button:disabled {{ cursor: not-allowed; opacity: 0.5; }}
  input[type=text], input[type=password] {{ width: 100%; max-width: 380px; padding: 0.4rem; border: 1px solid #ccc; border-radius: 6px; font-size: 0.9rem; }}
  details {{ border: 1px solid #ddd; border-radius: 8px; padding: 0.6rem 1rem; margin: 0.5rem 0; }}
  .search-panel {{ margin: 1rem 0; }}
  .result-row {{ display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid #ddd; gap: 1rem; }}
  #op-status {{ display: none; margin: 1rem 0; padding: 0.75rem 1rem; border-radius: 8px; background: #f5f5f5; }}
  #op-status.visible {{ display: block; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #111; color: #eee; }}
    th {{ background: #222; }}
    th, td {{ border-color: #333; }}
    button {{ background: #222; border-color: #444; color: #eee; }}
    input[type=text], input[type=password] {{ background: #1a1a1a; border-color: #444; color: #eee; }}
    details {{ border-color: #333; }}
    .result-row {{ border-color: #333; }}
    #op-status {{ background: #222; }}
    .badge-buy {{ background: #064e3b; color: #6ee7b7; }}
    .badge-sell {{ background: #7f1d1d; color: #fca5a5; }}
    .badge-neutral {{ background: #374151; color: #d1d5db; }}
  }}
</style>
</head>
<body>
<h1>퀀트 신호 어드바이저 대시보드</h1>
<p class="meta">생성 시각: {data['generated_at']}</p>

<h2>마지막 체크</h2>
{last_check_section}

<h2>워치리스트 현황</h2>
<table>
<tr><th>종목</th><th>매수/매도 임계값</th><th>주요 지표</th><th>검증구간 누적수익</th><th>샤프비율</th><th>거래수</th><th>벤치마크 초과수익</th><th>관리</th></tr>
{watchlist_rows}
</table>
{interactive_panel}

<h2>최근 신호 히스토리</h2>
<table>
<tr><th>시각</th><th>종목</th><th>방향</th><th>가격</th><th>근거</th><th>리스크 (ATR 기준)</th></tr>
{signal_rows}
</table>

<h2>자동 발굴 후보 (전체 미국 상장 종목/ETF 스캔)</h2>
<p class="meta">기준 시각: {candidates_as_of} · 워치리스트 미포함 종목 중 유동성 필터 통과 + 현재 매수/매도 신호가 있는 상위 종목 (참고용, 알림 발송 대상 아님)</p>
<table>
<tr><th>종목</th><th>이름</th><th>거래소</th><th>방향</th><th>스코어</th><th>리스크 (ATR 기준)</th></tr>
{candidates_rows}
</table>
</body>
</html>
"""


def generate(
    watchlist_path: str = "config/watchlist.yaml",
    calibration_dir=DEFAULT_CALIBRATION_DIR,
    history_path=DEFAULT_HISTORY_PATH,
    last_check_path=DEFAULT_LAST_CHECK_PATH,
    candidates_path=DEFAULT_CANDIDATES_PATH,
    output_dir=DEFAULT_OUTPUT_DIR,
    generated_at: datetime | None = None,
) -> Path:
    data = build_dashboard_data(
        watchlist_path, calibration_dir, history_path, last_check_path, candidates_path, generated_at
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (output_dir / "index.html").write_text(render_html(data), encoding="utf-8")
    return output_dir


if __name__ == "__main__":
    generate()
