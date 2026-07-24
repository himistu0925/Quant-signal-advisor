from dataclasses import dataclass

from advisor.data.yfinance_client import fetch_batch_daily
from advisor.live.run_check import score_ticker
from advisor.universe.listing import Listing

MIN_PRICE = 5.0
MIN_AVG_DOLLAR_VOLUME = 5_000_000.0
LIQUIDITY_LOOKBACK_PERIOD = "3mo"
SCORING_LOOKBACK_PERIOD = "1y"
TOP_N_CANDIDATES = 20


@dataclass
class Candidate:
    ticker: str
    name: str
    exchange: str
    score: float
    direction: str


def filter_by_liquidity(
    listings: list[Listing],
    min_price: float = MIN_PRICE,
    min_avg_dollar_volume: float = MIN_AVG_DOLLAR_VOLUME,
) -> list[Listing]:
    """First pass over the *entire* universe (thousands of tickers) using a
    cheap, short window -- just enough to estimate price and average dollar
    volume. Full-history scoring only happens for whatever survives this."""
    tickers = [listing.symbol for listing in listings]
    bars = fetch_batch_daily(tickers, period=LIQUIDITY_LOOKBACK_PERIOD)

    survivors = []
    for listing in listings:
        df = bars.get(listing.symbol)
        if df is None or df.empty or "Volume" not in df:
            continue
        avg_price = df["Close"].mean()
        avg_dollar_volume = (df["Close"] * df["Volume"]).mean()
        if avg_price >= min_price and avg_dollar_volume >= min_avg_dollar_volume:
            survivors.append(listing)
    return survivors


def rank_candidates(
    listings: list[Listing],
    exclude_tickers: set[str] | None = None,
    top_n: int = TOP_N_CANDIDATES,
) -> list[Candidate]:
    """Scores liquidity survivors with the exact same equal-weight fallback
    scoring live/run_check.score_ticker already uses for any uncalibrated
    ticker -- no new scoring logic needed. Keeps only tickers with an actual
    triggered BUY/SELL signal (this is a "candidates near a signal" list,
    not a full market-breadth dump), ranks by signal strength, and skips
    anything already on the real watchlist."""
    exclude_tickers = exclude_tickers or set()
    eligible = [listing for listing in listings if listing.symbol not in exclude_tickers]
    bars = fetch_batch_daily([listing.symbol for listing in eligible], period=SCORING_LOOKBACK_PERIOD)

    candidates = []
    for listing in eligible:
        df = bars.get(listing.symbol)
        if df is None or df.empty:
            continue
        direction, score, _threshold, _reasons = score_ticker(df)
        if direction is None:
            continue
        candidates.append(
            Candidate(ticker=listing.symbol, name=listing.name, exchange=listing.exchange, score=score, direction=direction)
        )

    candidates.sort(key=lambda c: abs(c.score), reverse=True)
    return candidates[:top_n]
