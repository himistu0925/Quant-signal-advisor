import pandas as pd

from advisor.backtest.engine import BacktestEngine
from advisor.backtest.report import generate_report
from tests.helpers import FakeIndicator


def test_generate_report_splits_trades_into_train_and_test():
    n = 1460
    dates = pd.date_range("2015-01-01", periods=n)
    prices = [100 + i * 0.1 for i in range(n)]
    df = pd.DataFrame({"Close": prices}, index=dates)
    benchmark_df = pd.DataFrame({"Close": [50 + i * 0.05 for i in range(n)]}, index=dates)

    votes = [0] * n
    # one full trade early (train period), one full trade near the end (test period)
    for i in range(100, 110):
        votes[i] = 1
    votes[110] = -1
    for i in range(1200, 1210):
        votes[i] = 1
    votes[1210] = -1

    engine = BacktestEngine(
        indicators={"Fake": FakeIndicator(votes)},
        buy_threshold=1,
        sell_threshold=-1,
        min_lookback=50,
    )

    report = generate_report(df, benchmark_df, engine, test_years=1.0)

    assert report.full.total_trades == 2
    assert report.train.total_trades == 1
    assert report.test.total_trades == 1
