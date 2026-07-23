import pytest

from advisor.data import finnhub_client as fc


def test_fetch_company_news_requires_api_key(monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    with pytest.raises(fc.FinnhubConfigError):
        fc.fetch_company_news("AAPL")


def test_fetch_company_news_calls_expected_endpoint(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"headline": "Stock surges on strong earnings beat"}]

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return FakeResponse()

    monkeypatch.setattr(fc.requests, "get", fake_get)

    articles = fc.fetch_company_news("AAPL", days=3)

    assert captured["url"] == f"{fc.FINNHUB_BASE_URL}/company-news"
    assert captured["params"]["symbol"] == "AAPL"
    assert captured["params"]["token"] == "test-key"
    assert articles == [{"headline": "Stock surges on strong earnings beat"}]
