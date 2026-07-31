# 나만의 퀀트 트레이딩 신호 어드바이저 — 프로젝트 히스토리

> 이 문서는 지금까지 Claude와 함께 이 프로젝트를 만들어온 전체 과정(설계 결정, 만든 도구, 겪은 문제와 해결책, 배운 점)을 한 곳에 정리한 기록입니다.
> 코드 자체는 이미 이 git 저장소(로컬 + GitHub `himistu0925/Quant-signal-advisor`)에 안전하게 저장되어 있으며, 이 문서는 "왜 이렇게 만들었는지"에 대한 맥락을 남기기 위한 것입니다.
> 최종 갱신: 2026-07-31

---

## 1. 프로젝트 개요

**목표**: 주관적 판단 대신 보조지표 수치만으로 매수/매도 후보 신호를 생성해 **디스코드로 알려주는** 개인용 도구. 실제 주문 체결은 사용자가 직접 하며, 시스템은 백테스트 + 실시간(15~30분 주기) 신호 알림까지만 담당한다. (근거: [plan.md](plan.md), PRD v0.2, 2026-07-22 작성)

| 항목 | 내용 |
|---|---|
| 대상 시장 | 미국 주식 (NYSE/NASDAQ) |
| 워치리스트 | 사용자가 직접 추가/삭제, 최대 5종목 |
| 데이터 소스 | yfinance (무료), VIX, 뉴스 감성 |
| 알림 채널 | Discord Webhook + 웹 대시보드 (GitHub Pages) |
| 체크 주기 | 장중 15~30분 간격 |
| 실행 환경 | GitHub Actions (PC 꺼져 있어도 동작) |
| 임계값 | 5년 백테스트 기반 캘리브레이션 |
| 자동 주문 실행 | 범위 밖 — 사용자가 수동 실행 |

**배포 상태**: 2026-07-23부터 실서비스 중.
- 저장소: https://github.com/himistu0925/Quant-signal-advisor (public)
- 대시보드: https://himistu0925.github.io/Quant-signal-advisor
- 소개/회고 페이지: https://himistu0925.github.io/Quant-signal-advisor/showcase.html

**현재 워치리스트 (2026-07-31 기준, 5/5 캡 도달)**: TQQQ, SOXL, UPRO, AAPL, GOOGL
- 처음엔 AAPL/MSFT 자리표시자였다가 → 사용자가 실제로 거래하는 **3배 레버리지 인덱스 ETF** (TQQQ=나스닥100, SOXL=반도체, UPRO=S&P500) 중심으로 확정.
- 2026-07-25에 대시보드에서 직접 AAPL, GOOGL을 추가해 5/5 캡을 채움 (아래 "브라우저 워치리스트 편집기" 참고).

---

## 2. 시스템 아키텍처 & 만든 도구들

```
워치리스트 설정(최대 5종목)
  → yfinance 시세·거래량·VIX
  → 지표 프레임워크(플러그인형)
  → 신호 스코어링 엔진(IC 기반 가중치 합산)
  → 백테스트 기반 캘리브레이션(과거 5년 데이터)
  → 쿨다운/중복 억제
  → Discord Webhook 알림 + 대시보드
```

### 핵심 모듈 (`src/advisor/`)

- **`indicators/`** — 플러그인형 보조지표 프레임워크. `compute(df) -> IndicatorResult(vote, detail)` 인터페이스로 통일. 레지스트리에서 "core"(항상 스코어링에 포함)와 "candidate"(등록만 되고 검증 전까지 스코어링에서 제외) 상태 구분.
  - Core: RSI, MACD, 이동평균, 볼린저밴드, 지지/저항, 일목균형표, 피보나치, 거래량
  - Candidate (아직 core로 승격 안 됨): Stochastic, ADX, OBV — AAPL/MSFT 기준 기여도 분석에서 예측력이 약/음(-)으로 나와 보류. 레버리지 ETF 워치리스트 기준으로는 재분석 필요.
- **`backtest/`** — 룩어헤드 안전한 확장윈도우(expanding-window) 시뮬레이션 엔진, 성과 지표, 그리드서치 캘리브레이션, 지표별 기여도 평가(정보계수/IC).
  - `indicator_evaluation.py::derive_ic_weights` — **핵심 설계 결정** (2026-07-23): 종목별로 각 core 지표의 가중치를 그 지표의 개별 정보계수(IC, vote와 향후 수익률의 상관관계)로 산출. 맹목적 동일가중이나 그리드서치 가중치가 아니라 "종목마다 다른 지표가 주도하게" 만드는 사용자의 명시적 요청이었음. IC가 0 이하면 가중치 0(제외, 부호 반전 아님). 예: TQQQ는 거의 RSI 단독 주도, SOXL은 볼린저밴드/일목균형표/이동평균/RSI/MACD에 분산.
- **`alerts/`** — Discord 알림, 쿨다운 트래커, 장중 시간 게이팅.
- **`live/run_check.py`** — 실시간 라이브 체크의 메인 진입점 (워치리스트 신호 + 유니버스 후보 급등락 감지 통합).
- **`live/movers.py::detect_sharp_move`** — 유니버스 후보 종목이 자기 자신의 평균 변동폭(ATR) 대비 `MOVE_ATR_MULTIPLE`(기본 2.0x) 이상 움직이면 즉시 알림 (2026-07-24).
- **`dashboard/`** — 정적 사이트 생성기 (`docs/index.html`, 서버 없음).
- **`risk/{atr.py, position_sizing.py}`** — 2026-07-24 추가. BUY 신호에 ATR 기반 손절/목표가와 고정비율 포지션 사이징(`1% 리스크 / 손절폭%`, 종목당 25% 캡) 부여. 공개 저장소이므로 `data/signal_history.json`에는 %만 저장, 실제 주식 수는 선택적 `ACCOUNT_EQUITY` 시크릿이 있을 때만 비공개 디스코드 메시지에만 표시(사용자가 아직 설정 안 함).
- **`universe/{listing.py, screen.py, store.py}`** — 미국 상장 전체 종목(~12,480개, 2026-07-24 기준)을 유동성으로 스크리닝해 상위 10개 후보를 매일 새벽 스캔. 실제 워치리스트에는 자동 추가되지 않음(캘리브레이션된 5종목만 유지) — 후보는 별도로 급등락 알림만 받음.
- **`watchlist.py`** — `check_can_add`/`add_ticker`/`remove_ticker`/`save_watchlist`.

### 스크립트 & 워크플로

- `scripts/run_signal_check.py`, `scripts/calibrate.py`, `scripts/scan_universe.py`, `scripts/generate_dashboard.py`, `scripts/add_ticker.py`, `scripts/remove_ticker.py`, `scripts/send_test_alert.py`
- `scripts/commit_and_push.sh` — 5개 워크플로가 공용으로 쓰는 커밋/푸시 스크립트 (아래 "git push 경합" 참고)
- GitHub Actions: `schedule.yml`(실시간 체크), `universe_scan.yml`(유니버스 스캔), `calibrate.yml`(월간 재캘리브레이션), `add_ticker.yml`/`remove_ticker.yml`(대시보드 편집기용)

### 브라우저 워치리스트 편집기 (2026-07-25)

대시보드에서 실제 브로커 앱처럼 티커를 검색해 워치리스트에 추가/삭제할 수 있게 만듦. 별도 백엔드 없이 브라우저가 사용자 본인의 GitHub PAT를 `localStorage`에 보관하고 `api.github.com`을 직접 호출 → `workflow_dispatch`로 `add_ticker.yml`/`remove_ticker.yml` 실행. `docs/tickers.json`이 클라이언트 검색용 티커 목록 제공.

### 검증/회고 자료

- `docs/assumption_validation.md` (2026-07-27) — 5가지 투자 스타일 페르소나로 plan.md 핵심 가정 검증. 매수보다 **매도 타이밍이 더 고통스럽다**는 점, "지표 기반 신호"는 기술적 트레이더에게만 통하고 장기 투자자에게는 안 맞는다는 점, 혼자 판단할 때 흔들리는 진짜 이유는 정보 부족이 아니라 "판단을 검증할 앵커"의 부재라는 점(커뮤니티 여론이 그 자리를 대신하지만 자주 틀림 — 이 도구의 실질적 차별점) 확인.
- `docs/showcase.html` (2026-07-31) — 2주차 과제용 소개/회고 페이지.

---

## 3. 시행착오 타임라인 — 운영 이슈와 해결책

프로젝트를 만들면서 실제로 부딪히고 고친 문제들. 코드에는 결과만 남고 "왜"는 남지 않으므로 여기에 기록.

1. **유니버스 스캔 행(hang) 문제** — `yfinance_client.fetch_batch_daily`에 타임아웃이 없어서 12,480개 종목 스캔이 18분+ 멈춘 채 진행 상태를 알 수 없었음. → 청크당 20초 타임아웃 + 실패 시 스킵 + 진행 로그 출력으로 해결 (commit e928e2a).
2. **GitHub Actions 크론이 조용히 fire를 누락함** — `schedule.yml`이 하루 8번 예상 중 실제로는 0번 자동 실행됨. 원인: 정각(`:00`/`:30`)은 GitHub 공식 문서가 고부하 시간대로 지목. → 크론을 정각에서 몇 분씩 offset (`7,37` 등)으로 1차 완화, 그래도 대부분(하루 20번 중 2번) 누락 지속 확인(Actions API로 검증). → **cron-job.org**(외부 무료 크론)가 `workflow_dispatch` API를 직접 호출하도록 이중화 — GitHub 자체 스케줄러는 백업으로 남겨둠. 이후 30분 주기로 안정적으로 작동 확인.
3. **git push 경합(race condition)** — 워크플로 5개가 거의 동시에 `docs/index.html` 등을 각자 재생성해 커밋하면서 서로 push를 놓침(예: GOOGL 추가 시도가 AAPL 커밋과 경합해 실패). → `concurrency: group: repo-state-write`만으로는 부족했고, 결국 `scripts/commit_and_push.sh`(최대 5회 재시도 + 충돌 시 rebase, 대시보드 재생성이 필요한 워크플로는 `REGENERATE_DASHBOARD=1`로 재생성 후 재시도)로 근본 해결 (commit ef81bf8).
4. **디스코드는 오는데 휴대폰 푸시가 안 옴** — Discord 앱 내 알림 설정(전체 메시지, 서버 미음소거)은 모두 정상인데도 푸시가 안 왔음. 근본 원인은 **iOS 설정 → Discord → 알림 → "잠금 화면(Lock Screen)" 토글이 꺼져 있던 것** — 앱 내부 설정과는 완전히 별개. 웹훅 메시지가 인앱으로는 오는데 휴대폰 푸시만 안 오면, 코드/Discord 앱 설정이 아니라 OS 레벨 알림 권한(잠금화면/배너/알림센터는 iOS에서 각각 독립 스위치)부터 확인.
5. **GitHub Actions 로그 뷰어가 실행 중인 작업의 로그를 안 열어줌** — 새로고침/검색 다 시도해도 안 됨. 알고 보니 GitHub는 로그 조회에 로그인이 필요(익명 접속으로 재현 확인)했고, 완료된 작업의 로그는 정상적으로 열림. 실행 중인 작업 상태를 보고 싶으면 `GET /repos/{owner}/{repo}/actions/runs/{id}/jobs` (public repo는 인증 불필요)를 폴링.

---

## 4. 핵심 설계 결정 모음

- **종목별 IC 기반 지표 가중치** (2026-07-23): 동일가중/그리드서치 대신, 각 지표의 실측 정보계수로 가중치 산출. 사용자가 "종목마다 다른 지표가 주도해야 한다"고 명시적으로 요청.
- **워치리스트 5종목 캡 유지** (반복 확인, 2026-07-24/25): 유니버스 스캔으로 후보가 나와도 캘리브레이션된 실제 워치리스트에는 자동 추가하지 않음. 후보는 급등락 알림만.
- **비공개 정보 경계**: 저장소/대시보드가 public이므로 `data/signal_history.json`, `data/mover_history.json` 등에는 %만 기록. 실제 계좌 규모 기반 수치(주식 수 등)는 `ACCOUNT_EQUITY` 시크릿이 설정된 경우에만 비공개 Discord 메시지 안에서만 노출.
- **백테스트/캘리브레이션 결과에 대한 태도**: 표본이 극히 적음(연간 테스트 기간에 종목당 1~5건 거래)을 항상 명시. 좋아 보이는 헤드라인 수치(예: SOXL 초과수익 +152pp)도 표본 크기와 인샘플/아웃샘플 불일치를 함께 밝힘. 2026-07-23 사용자는 이 캐비어트를 받고 "몇 주간 페이퍼트레이딩으로 관찰"하기로 결정 — 추가 기능 변경을 성급히 밀어붙이지 않기로 함.
- **아직 구현 안 된 것 (의도적으로 미룸, 조용히 넘어가지 않고 사용자에게 명시)**: `backtest/engine.py`는 아직 지표 반전(vote-flip)으로만 청산하며, 새 ATR 손절/목표가 규칙을 백테스트에 반영하지 않음 — 그래서 백테스트 성과 수치는 실제 리스크 레이어가 있었다면 나왔을 결과를 반영하지 못함.

---

## 5. 남아있는 미결 과제 (plan.md 16절 + 이후 논의)

- 재캘리브레이션 주기: 현재 월간 placeholder, 분기(quarterly) 전환 여부 미정.
- Walk-forward validation 미구현 (현재는 단일 train/test split).
- Stochastic/ADX/OBV → core 승격 여부: 레버리지 ETF 워치리스트 기준 기여도 재분석 필요 (기존 분석은 AAPL/MSFT 기준).
- 매도 신호 알림의 근거를 매수보다 더 두껍게(사용자 검증 결과, 매도 타이밍이 더 고통스럽다는 점 반영) — 아직 미착수.
- `docs/index.html`에서 워치리스트/최종체크 테이블 통합 리스트업(계획했던 시각적 리팩터)은 기존 테스트 스위트 재작성 부담 때문에 보류, 검색/추가/삭제 기능만 구현.
- backtest/engine.py의 ATR 손절/목표가 청산 미반영 (위 4절 참고).

---

## 6. 작업 방식에 대한 합의 (Claude ↔ 사용자)

- Git/GitHub은 처음이라 (2026-07-23 기준) 구체적인 클릭 경로/터미널 명령을 단계별로 안내받는 것을 선호. 반면 정보계수, 샤프비율, 그리드서치 같은 퀀트/통계 개념은 이미 능숙해서 과설명 불필요.
- 실거래는 개별 종목이 아닌 **레버리지 인덱스 ETF** 중심.
- 기능을 "완료"라고 보고하기 전에 합성 테스트가 아니라 **실제 시세 데이터로 스모크테스트**를 돌리고 결과를 직접 확인하는 습관이 실제 버그(무한대 JSON 직렬화 오류, UTC 기준 장중 판단 오류, 데이터 27일뿐인 신규 상장주 캘리브레이션 오류)를 여러 번 잡아냄 — 사용자가 요청하지 않아도 이렇게 검증하는 방식이 잘 통했음.
- 백테스트/캘리브레이션 수치를 보고할 때는 항상 거래 건수(표본 크기)를 함께 밝히고, 표본이 작으면 신뢰하기 어렵다고 명시.

---

## 7. 참고 문서

- [plan.md](plan.md) — 원본 PRD (v0.2, 2026-07-22)
- [docs/assumption_validation.md](docs/assumption_validation.md) — 가정 검증 리포트
- [docs/showcase.html](docs/showcase.html) — 2주차 소개/회고 페이지
- GitHub 저장소: https://github.com/himistu0925/Quant-signal-advisor
