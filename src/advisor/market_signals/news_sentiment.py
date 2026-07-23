import re

from advisor.data.finnhub_client import fetch_company_news
from advisor.indicators.base import IndicatorResult

POSITIVE_KEYWORDS = {
    "beat", "beats", "surge", "surges", "rally", "rallies", "upgrade", "upgrades",
    "upgraded", "record", "growth", "profit", "profits", "outperform", "bullish",
    "gain", "gains", "soar", "soars", "strong", "buy",
}
NEGATIVE_KEYWORDS = {
    "miss", "misses", "plunge", "plunges", "downgrade", "downgrades", "downgraded",
    "recall", "lawsuit", "loss", "losses", "bearish", "decline", "declines", "weak",
    "sell", "fraud", "investigation", "layoff", "layoffs", "crash", "crashes",
}


def score_headlines(headlines: list[str]) -> IndicatorResult:
    """Keyword-based sentiment (plan.md section 8): a starting point, not a
    real NLP model -- upgrade this if the keyword lexicon proves too noisy."""
    if not headlines:
        return IndicatorResult(vote=0, detail="News: no headlines available")

    pos_hits = 0
    neg_hits = 0
    for headline in headlines:
        words = re.findall(r"[a-zA-Z']+", headline.lower())
        pos_hits += sum(1 for w in words if w in POSITIVE_KEYWORDS)
        neg_hits += sum(1 for w in words if w in NEGATIVE_KEYWORDS)

    score = pos_hits - neg_hits
    vote = 1 if score > 0 else (-1 if score < 0 else 0)
    detail = f"News: {pos_hits} positive / {neg_hits} negative keyword hits across {len(headlines)} headlines"
    return IndicatorResult(vote=vote, detail=detail)


def sentiment_for_ticker(ticker: str, days: int = 3) -> IndicatorResult:
    articles = fetch_company_news(ticker, days=days)
    headlines = [a["headline"] for a in articles if a.get("headline")]
    return score_headlines(headlines)
