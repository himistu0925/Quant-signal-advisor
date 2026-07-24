import requests


def format_signal_message(
    ticker: str,
    direction: str,
    price: float,
    timestamp_et: str,
    reasons: list[str],
    vix_regime: str,
    vix_percentile: float,
    score: float,
    threshold: float,
    stop_price: float | None = None,
    target_price: float | None = None,
    position_pct: float | None = None,
    shares: int | None = None,
) -> str:
    """Matches the message template in plan.md section 11, extended with an
    optional ATR-based risk block (BUY signals only). shares is only ever
    populated when ACCOUNT_EQUITY is configured -- this message goes to a
    private Discord webhook only and is never committed to the repo."""
    reasons_line = " · ".join(reasons) if reasons else "N/A"
    message = (
        f"{direction} 신호 — {ticker}\n"
        f"가격: ${price:.2f} ({timestamp_et})\n"
        f"근거: {reasons_line}\n"
        f"VIX 필터: {vix_regime} ({vix_percentile:.0f}th pct)\n"
        f"신호 스코어: {score:+.0f} / 캘리브레이션된 임계값 {threshold:+.0f}"
    )

    if stop_price is not None and target_price is not None and position_pct is not None:
        message += (
            f"\n손절: ${stop_price:.2f} / 익절: ${target_price:.2f} (ATR 기준) "
            f"· 제안 비중: 계좌의 {position_pct:.1%}"
        )
        if shares is not None:
            message += f" (~{shares}주)"

    return message


def send_discord_alert(webhook_url: str, message: str) -> None:
    response = requests.post(webhook_url, json={"content": message}, timeout=10)
    response.raise_for_status()
