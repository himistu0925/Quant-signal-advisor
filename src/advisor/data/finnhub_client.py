import os
from datetime import date, timedelta

import requests

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


class FinnhubConfigError(Exception):
    pass


def _get_api_key() -> str:
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        raise FinnhubConfigError("FINNHUB_API_KEY environment variable is not set")
    return api_key


def fetch_company_news(ticker: str, days: int = 3) -> list[dict]:
    api_key = _get_api_key()
    to_date = date.today()
    from_date = to_date - timedelta(days=days)

    response = requests.get(
        f"{FINNHUB_BASE_URL}/company-news",
        params={
            "symbol": ticker,
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
            "token": api_key,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
