from advisor.market_signals import news_sentiment as ns


def test_score_headlines_positive():
    headlines = [
        "Company beats earnings expectations, shares rally",
        "Analysts upgrade stock to buy",
    ]
    result = ns.score_headlines(headlines)
    assert result.vote == 1


def test_score_headlines_negative():
    headlines = [
        "Company misses earnings, shares plunge",
        "Analyst downgrades stock amid lawsuit",
    ]
    result = ns.score_headlines(headlines)
    assert result.vote == -1


def test_score_headlines_neutral_with_no_keyword_hits():
    headlines = ["Company announces quarterly conference call schedule"]
    result = ns.score_headlines(headlines)
    assert result.vote == 0


def test_score_headlines_empty_is_neutral():
    result = ns.score_headlines([])
    assert result.vote == 0


def test_sentiment_for_ticker_uses_finnhub_client(monkeypatch):
    def fake_fetch(ticker, days=3):
        assert ticker == "AAPL"
        return [{"headline": "Stock surges on strong earnings beat"}]

    monkeypatch.setattr(ns, "fetch_company_news", fake_fetch)

    result = ns.sentiment_for_ticker("AAPL")
    assert result.vote == 1
