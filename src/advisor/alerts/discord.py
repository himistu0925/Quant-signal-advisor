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
) -> str:
    """Matches the message template in plan.md section 11."""
    reasons_line = " · ".join(reasons) if reasons else "N/A"
    return (
        f"{direction} 신호 — {ticker}\n"
        f"가격: ${price:.2f} ({timestamp_et})\n"
        f"근거: {reasons_line}\n"
        f"VIX 필터: {vix_regime} ({vix_percentile:.0f}th pct)\n"
        f"신호 스코어: {score:+.0f} / 캘리브레이션된 임계값 {threshold:+.0f}"
    )


def send_discord_alert(webhook_url: str, message: str) -> None:
    response = requests.post(webhook_url, json={"content": message}, timeout=10)
    response.raise_for_status()
