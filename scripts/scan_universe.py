from datetime import datetime, timezone

from advisor.universe.listing import fetch_us_listing
from advisor.universe.screen import filter_by_liquidity, rank_candidates
from advisor.universe.store import save_candidates
from advisor.watchlist import load_watchlist


def main() -> None:
    watchlist = load_watchlist("config/watchlist.yaml")

    listings = fetch_us_listing()
    print(f"fetched {len(listings)} listed tickers")

    survivors = filter_by_liquidity(listings)
    print(f"{len(survivors)} passed the liquidity filter")

    candidates = rank_candidates(survivors, exclude_tickers=set(watchlist.tickers))
    print(f"{len(candidates)} candidates with a live BUY/SELL signal")

    as_of = datetime.now(tz=timezone.utc).isoformat()
    save_candidates(candidates, as_of=as_of)
    for c in candidates:
        print(f"  {c.ticker} ({c.exchange}): {c.direction} score={c.score:.2f}")


if __name__ == "__main__":
    main()
