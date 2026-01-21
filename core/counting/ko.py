"""Knock-Out (KO) card counting system."""

from typing import Mapping

from core.cards import Rank
from core.counting.base import CountingSystem


class KOSystem(CountingSystem):
    """
    Knock-Out (KO) counting system.

    An unbalanced system that eliminates the need for true count conversion.
    Similar to Hi-Lo but counts 7 as +1.

    Tag values:
        2-7: +1 (includes 7 unlike Hi-Lo)
        8-9: 0  (neutral)
        10-A: -1 (high cards)

    Full deck sum: +4 (unbalanced)
    """

    _TAG_VALUES: Mapping[Rank, float] = {
        Rank.TWO: 1,
        Rank.THREE: 1,
        Rank.FOUR: 1,
        Rank.FIVE: 1,
        Rank.SIX: 1,
        Rank.SEVEN: 1,  # Key difference from Hi-Lo
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
        return "Knock-Out (KO)"

    @property
    def tag_values(self) -> Mapping[Rank, float]:
        return self._TAG_VALUES

    @property
    def is_balanced(self) -> bool:
        return False

    def initial_running_count(self, num_decks: int) -> int:
        """
        Calculate the initial running count for KO system.

        The IRC is set so that key count (pivot point) is 0.
        IRC = 4 - (4 * num_decks)

        Args:
            num_decks: Number of decks in the shoe

        Returns:
            The initial running count
        """
        return 4 - (4 * num_decks)

    def reset_for_shoe(self, num_decks: int) -> None:
        """
        Reset the count for a new shoe with appropriate IRC.

        Args:
            num_decks: Number of decks in the shoe
        """
        self._running_count = float(self.initial_running_count(num_decks))
        self._cards_seen = 0
