from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass
class IndicatorResult:
    vote: int  # -1 (sell), 0 (neutral), +1 (buy)
    detail: str


class Indicator(Protocol):
    name: str

    def compute(self, df: pd.DataFrame) -> IndicatorResult: ...


def crossover_vote(prev_diff: float, curr_diff: float) -> int:
    """Shared golden-cross/dead-cross decision used by any indicator that
    votes on two lines crossing (MA pairs, MACD vs signal, etc.)."""
    if prev_diff <= 0 and curr_diff > 0:
        return 1
    if prev_diff >= 0 and curr_diff < 0:
        return -1
    return 0
