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
