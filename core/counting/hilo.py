"""Hi-Lo card counting system."""

from typing import Mapping

from core.cards import Rank
from core.counting.base import CountingSystem


class HiLoSystem(CountingSystem):
    """
    Hi-Lo counting system.

    The most popular and widely taught counting system.

    Tag values:
        2-6: +1 (low cards)
        7-9: 0  (neutral)
        10-A: -1 (high cards)

    Full deck sum: 0 (balanced)
    """

    _TAG_VALUES: Mapping[Rank, float] = {
        Rank.TWO: 1,
        Rank.THREE: 1,
        Rank.FOUR: 1,
        Rank.FIVE: 1,
        Rank.SIX: 1,
        Rank.SEVEN: 0,
        Rank.EIGHT: 0,
        Rank.NINE: 0,
        Rank.TEN: -1,
        Rank.JACK: -1,
        Rank.QUEEN: -1,
        Rank.KING: -1,
        Rank.ACE: -1,
    }

    @property
    def name(self) -> str:
        return "Hi-Lo"

    @property
    def tag_values(self) -> Mapping[Rank, float]:
        return self._TAG_VALUES

    @property
    def is_balanced(self) -> bool:
        return True
