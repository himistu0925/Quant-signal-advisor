import pandas as pd
import pytest

from advisor.live.movers import detect_sharp_move


def _df(closes, high_pad=1.0, low_pad=1.0):
    return pd.DataFrame({
        "High": [c + high_pad for c in closes],
        "Low": [c - low_pad for c in closes],
        "Close": closes,
    })


def test_detect_sharp_move_returns_none_with_insufficient_history():
    assert detect_sharp_move(_df([10.0])) is None


def test_detect_sharp_move_returns_none_for_normal_daily_range():
    # Constant High=11/Low=9/Close=10 every day -> today's move is 0%, far
    # below any multiple of the (also ~2.0) ATR.
    assert detect_sharp_move(_df([10.0] * 20)) is None


def test_detect_sharp_move_flags_a_surge():
    closes = [10.0] * 19 + [20.0]  # +100% jump, comfortably past a 2x-ATR bar
    move = detect_sharp_move(_df(closes))

    assert move is not None
    assert move.direction == "SURGE"
    assert move.pct_change == pytest.approx(1.0)
    assert move.price == pytest.approx(20.0)


def test_detect_sharp_move_flags_a_plunge():
    closes = [10.0] * 19 + [5.0]  # -50% drop
    move = detect_sharp_move(_df(closes))

    assert move is not None
    assert move.direction == "PLUNGE"
    assert move.pct_change == pytest.approx(-0.5)


def test_detect_sharp_move_respects_a_tighter_atr_multiple():
    # A move too small to clear the default 2.0x-ATR bar should still clear
    # a looser (smaller) multiple passed in explicitly.
    closes = [10.0] * 19 + [10.5]  # +5% -- small relative to the ~2.0 ATR (20% of price)
    assert detect_sharp_move(_df(closes)) is None
    assert detect_sharp_move(_df(closes), atr_multiple=0.1) is not None
