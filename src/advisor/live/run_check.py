import os
from datetime import datetime

import pandas as pd
import requests

from advisor.alerts.cooldown import DEFAULT_STATE_PATH, CooldownTracker
from advisor.alerts.discord import format_signal_message, send_discord_alert
from advisor.alerts.history import DEFAULT_HISTORY_PATH, append_signal_event
from advisor.alerts.market_hours import NY_TZ, is_market_open
from advisor.backtest.calibration_store import InsufficientDataMarker, load_calibration_entry
from advisor.data.finnhub_client import FinnhubConfigError
from advisor.data.yfinance_client import fetch_daily, fetch_vix
from advisor.indicators import split_registered
from advisor.market_signals.news_sentiment import sentiment_for_ticker
from advisor.market_signals.vix_filter import VixFilter
from advisor.watchlist import load_watchlist

DEFAULT_BUY_THRESHOLD = 3.0
DEFAULT_SELL_THRESHOLD = -3.0
VOLUME_MULTIPLIER = 1.5
NEWS_SENTIMENT_WEIGHT = 0.5  # plan.md section 8/9: secondary confirmation, not a full vote
VIX_FEAR_THRESHOLD_PENALTY = 1.0  # section 8: raise the buy bar when VIX is in extreme_fear


def score_ticker(df: pd.DataFrame, calibration=None, vix_state=None, news_result=None):
    """One evaluation of every registered indicator on a ticker's current
    price history. Uses calibrated weights/thresholds if available
    (calibration/{ticker}.json from Phase 4), otherwise the same equal-weight
    defaults the backtest engine starts from. vix_state/news_result are
    optional macro/sentiment inputs (plan.md section 8) -- both None
    reproduces the plain indicator-only score."""
    directional, volume_indicator = split_registered()
    weights = calibration.weights if calibration else {name: 1.0 for name in directional}
    buy_threshold = calibration.buy_threshold if calibration else DEFAULT_BUY_THRESHOLD
    sell_threshold = calibration.sell_threshold if calibration else DEFAULT_SELL_THRESHOLD

    results = {name: indicator.compute(df) for name, indicator in directional.items()}
    score = sum(result.vote * weights.get(name, 1.0) for name, result in results.items())

    if volume_indicator is not None:
        volume_result = volume_indicator.compute(df)
        if volume_result.vote == 1:
            score *= VOLUME_MULTIPLIER

    reasons = [result.detail for result in results.values() if result.vote != 0]

    if news_result is not None:
        score += news_result.vote * NEWS_SENTIMENT_WEIGHT
        if news_result.vote != 0:
            reasons.append(news_result.detail)

    if vix_state is not None and vix_state.regime == "extreme_fear":
        buy_threshold += VIX_FEAR_THRESHOLD_PENALTY

    if score >= buy_threshold:
        direction = "BUY"
        threshold = buy_threshold
    elif score <= sell_threshold:
        direction = "SELL"
        threshold = sell_threshold
    else:
        direction = None
        threshold = None

    return direction, score, threshold, reasons


def run(
    watchlist_path: str = "config/watchlist.yaml",
    now: datetime | None = None,
    cooldown_path=DEFAULT_STATE_PATH,
    history_path=DEFAULT_HISTORY_PATH,
) -> None:
    # datetime.now() with no tz would be naive local time -- wrong on a UTC
    # GitHub Actions runner, since is_market_open() treats naive input as
    # already being NY wall-clock time. Anchor explicitly to NY time instead.
    now = now or datetime.now(tz=NY_TZ)
    if not is_market_open(now):
        return  # plan.md section 3: quietly exit outside regular trading hours

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    watchlist = load_watchlist(watchlist_path)
    vix_state = VixFilter().evaluate(fetch_vix(period="1y"))
    cooldown = CooldownTracker(path=cooldown_path)

    for ticker in watchlist.tickers:
        df = fetch_daily(ticker, period="1y")

        try:
            entry = load_calibration_entry(ticker)
            calibration = None if isinstance(entry, InsufficientDataMarker) else entry
        except FileNotFoundError:
            calibration = None

        try:
            news_result = sentiment_for_ticker(ticker)
        except (FinnhubConfigError, requests.RequestException):
            # plan.md section 8: source outage -> drop it, keep scoring with what's left
            news_result = None

        direction, score, threshold, reasons = score_ticker(df, calibration, vix_state, news_result)
        if direction is None:
            continue
        if not cooldown.should_alert(ticker, direction, now):
            continue

        price = df["Close"].iloc[-1]
        message = format_signal_message(
            ticker=ticker,
            direction=direction,
            price=price,
            timestamp_et=now.isoformat(),
            reasons=reasons,
            vix_regime=vix_state.regime,
            vix_percentile=vix_state.percentile,
            score=score,
            threshold=threshold,
        )

        if webhook_url:
            send_discord_alert(webhook_url, message)

        append_signal_event(
            {
                "ticker": ticker,
                "direction": direction,
                "price": price,
                "timestamp": now.isoformat(),
                "score": score,
                "threshold": threshold,
                "reasons": reasons,
            },
            path=history_path,
        )
        cooldown.record(ticker, direction, now)

    cooldown.save()


if __name__ == "__main__":
    run()
