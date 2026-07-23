from advisor.indicators.base import IndicatorResult


class FakeIndicator:
    """Deterministic test double: votes[i] is used when the expanding
    window passed to compute() ends at index i (len(window) - 1 == i)."""

    def __init__(self, votes, name="Fake"):
        self.votes = votes
        self.name = name

    def compute(self, window):
        i = len(window) - 1
        vote = self.votes[i]
        return IndicatorResult(vote=vote, detail=f"{self.name}={vote}")
