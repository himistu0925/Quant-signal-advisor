from dataclasses import dataclass

import requests

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
REQUEST_TIMEOUT_SECONDS = 30

# otherlisted.txt uses single-letter exchange codes.
_EXCHANGE_CODES = {"A": "NYSE American", "N": "NYSE", "P": "NYSE Arca", "Z": "Cboe BZX", "V": "IEXG"}


@dataclass
class Listing:
    symbol: str
    name: str
    exchange: str
    is_etf: bool


def _is_clean_symbol(symbol: str) -> bool:
    """Keep plain common-stock/ETF tickers only -- warrants/units/preferreds
    show up in these files with '.', '$', or other suffix characters that
    yfinance/the rest of this pipeline don't expect."""
    return bool(symbol) and symbol.isalpha() and symbol.isupper()


def _parse_directory(text: str, field_count: int) -> list[list[str]]:
    rows = []
    for line in text.strip().splitlines()[1:]:  # skip header row
        if line.startswith("File Creation Time"):  # footer row every NASDAQ Trader file ends with
            continue
        fields = line.split("|")
        if len(fields) >= field_count:
            rows.append(fields)
    return rows


def _parse_nasdaq_listed(text: str) -> list[Listing]:
    listings = []
    for symbol, name, _market_category, test_issue, _financial_status, _round_lot, etf, *_ in _parse_directory(text, 7):
        if test_issue == "Y" or not _is_clean_symbol(symbol):
            continue
        listings.append(Listing(symbol=symbol, name=name, exchange="NASDAQ", is_etf=etf == "Y"))
    return listings


def _parse_other_listed(text: str) -> list[Listing]:
    listings = []
    for symbol, name, exchange, _cqs_symbol, etf, _round_lot, test_issue, *_ in _parse_directory(text, 8):
        if test_issue == "Y" or not _is_clean_symbol(symbol):
            continue
        listings.append(Listing(symbol=symbol, name=name, exchange=_EXCHANGE_CODES.get(exchange, exchange), is_etf=etf == "Y"))
    return listings


def fetch_us_listing() -> list[Listing]:
    """Full US-listed common-stock + ETF universe from NASDAQ Trader's free,
    no-key symbol directories -- the standard source for this, and far more
    stable than scraping (plan.md already ruled out investpy/CNN F&G for
    exactly that fragility reason)."""
    nasdaq_resp = requests.get(NASDAQ_LISTED_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    nasdaq_resp.raise_for_status()
    other_resp = requests.get(OTHER_LISTED_URL, timeout=REQUEST_TIMEOUT_SECONDS)
    other_resp.raise_for_status()

    listings = _parse_nasdaq_listed(nasdaq_resp.text) + _parse_other_listed(other_resp.text)

    seen = set()
    deduped = []
    for listing in listings:
        if listing.symbol in seen:
            continue
        seen.add(listing.symbol)
        deduped.append(listing)
    return deduped
