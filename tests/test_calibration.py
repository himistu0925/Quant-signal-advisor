import pandas as pd

from advisor.backtest.calibration import compute_vote_matrix, grid_search
from tests.helpers import FakeIndicator


def test_compute_vote_matrix_aligns_votes_with_dates():
    dates = pd.date_range("2020-01-01", periods=6)
    df = pd.DataFrame({"Close": [1, 2, 3, 4, 5, 6]}, index=dates)
    votes = [0, 0, 1, 1, -1, -1]

    matrix = compute_vote_matrix(df, {"Fake": FakeIndicator(votes)}, min_lookback=2)

    assert list(matrix.index) == list(dates[2:])
    assert list(matrix["Fake"]) == votes[2:]


def test_grid_search_prefers_threshold_that_actually_trades():
    n = 16
    dates = pd.date_range("2020-01-01", periods=n)
    prices = [100 + i for i in range(n)]
    df = pd.DataFrame({"Close": prices}, index=dates)
    votes = [0, 0, 0] + [1] * (n - 3)

    result = grid_search(
        df=df,
        indicators={"Fake": FakeIndicator(votes)},
        weight_grid=[1.0],
        threshold_grid=[1.0, 5.0],
        min_lookback=3,
        test_years=0.001,
    )

    assert result.weights == {"Fake": 1.0}
    assert result.buy_threshold == 1.0
    assert result.sell_threshold == -1.0
