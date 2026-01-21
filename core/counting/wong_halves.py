"""Wong Halves card counting system."""

from typing import Mapping

from core.cards import Rank
from core.counting.base import CountingSystem


class WongHalvesSystem(CountingSystem):
    """
    Wong Halves counting system.

    A multi-level balanced system using fractional values.
    One of the most accurate systems but difficult to use.

    Tag values:
        2, 7: +0.5
        3, 4, 6: +1
        5: +1.5
        8: 0
        9: -0.5
        10-K, A: -1

    Full deck sum: 0 (balanced)

    Many players double all values to avoid fractions:
        2, 7: +1
        3, 4, 6: +2
        5: +3
        8: 0
        9: -1
        10-K, A: -2
    """

    _TAG_VALUES: Mapping[Rank, float] = {
        Rank.TWO: 0.5,
        Rank.THREE: 1.0,
        Rank.FOUR: 1.0,
        Rank.FIVE: 1.5,
        Rank.SIX: 1.0,
        Rank.SEVEN: 0.5,
        Rank.EIGHT: 0.0,
        Rank.NINE: -0.5,
        Rank.TEN: -1.0,
        Rank.JACK: -1.0,
        Rank.QUEEN: -1.0,
        Rank.KING: -1.0,
        Rank.ACE: -1.0,
    }

    # Doubled values for easier mental math
    _DOUBLED_TAG_VALUES: Mapping[Rank, float] = {
        Rank.TWO: 1,
        Rank.THREE: 2,
        Rank.FOUR: 2,
        Rank.FIVE: 3,
        Rank.SIX: 2,
        Rank.SEVEN: 1,
        Rank.EIGHT: 0,
        Rank.NINE: -1,
        Rank.TEN: -2,
        Rank.JACK: -2,
        Rank.QUEEN: -2,
        Rank.KING: -2,
        Rank.ACE: -2,
    }

    def __init__(self, use_doubled_values: bool = False) -> None:
        """
        Initialize Wong Halves system.

        Args:
            use_doubled_values: If True, use doubled (integer) values
        """
        super().__init__()
        self._use_doubled = use_doubled_values

    @property
    def name(self) -> str:
        if self._use_doubled:
            return "Wong Halves (Doubled)"
        return "Wong Halves"

    @property
    def tag_values(self) -> Mapping[Rank, float]:
        if self._use_doubled:
            return self._DOUBLED_TAG_VALUES
        return self._TAG_VALUES

    @property
    def is_balanced(self) -> bool:
        return True

    @property
    def uses_doubled_values(self) -> bool:
        """Return whether doubled values are being used."""
        return self._use_doubled
