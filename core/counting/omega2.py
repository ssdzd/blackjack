"""Omega II card counting system."""

from typing import Mapping

from core.cards import Card, Rank
from core.counting.base import CountingSystem


class Omega2System(CountingSystem):
    """
    Omega II counting system.

    A multi-level balanced system with a separate ace side count.
    More accurate than Hi-Lo but more complex.

    Tag values:
        2, 3, 7: +1
        4, 5, 6: +2
        8, A: 0
        9: -1
        10-K: -2

    Full deck sum: 0 (balanced)

    Additionally tracks aces separately for insurance and betting decisions.
    """

    _TAG_VALUES: Mapping[Rank, float] = {
        Rank.TWO: 1,
        Rank.THREE: 1,
        Rank.FOUR: 2,
        Rank.FIVE: 2,
        Rank.SIX: 2,
        Rank.SEVEN: 1,
        Rank.EIGHT: 0,
        Rank.NINE: -1,
        Rank.TEN: -2,
        Rank.JACK: -2,
        Rank.QUEEN: -2,
        Rank.KING: -2,
        Rank.ACE: 0,  # Aces are tracked separately
    }

    def __init__(self) -> None:
        """Initialize Omega II with ace side count."""
        super().__init__()
        self._aces_seen: int = 0

    @property
    def name(self) -> str:
        return "Omega II"

    @property
    def tag_values(self) -> Mapping[Rank, float]:
        return self._TAG_VALUES

    @property
    def is_balanced(self) -> bool:
        return True

    def count_card(self, card: Card) -> float:
        """Count a card and track aces separately."""
        if card.is_ace:
            self._aces_seen += 1
        return super().count_card(card)

    @property
    def aces_seen(self) -> int:
        """Return the number of aces seen."""
        return self._aces_seen

    def aces_remaining(self, num_decks: int) -> int:
        """
        Calculate the number of aces remaining.

        Args:
            num_decks: Number of decks in the shoe

        Returns:
            Number of aces remaining
        """
        total_aces = num_decks * 4
        return total_aces - self._aces_seen

    def ace_richness(self, num_decks: int, decks_remaining: float) -> float:
        """
        Calculate the ace richness of the remaining deck.

        Args:
            num_decks: Number of decks in the shoe
            decks_remaining: Number of decks remaining

        Returns:
            Ratio of actual aces remaining to expected aces remaining.
            > 1.0 means ace-rich, < 1.0 means ace-poor.
        """
        if decks_remaining <= 0:
            return 1.0
        expected_aces = decks_remaining * 4
        if expected_aces == 0:
            return 1.0
        actual_aces = self.aces_remaining(num_decks)
        return actual_aces / expected_aces

    def reset(self) -> None:
        """Reset the count and ace side count."""
        super().reset()
        self._aces_seen = 0

    def __repr__(self) -> str:
        return (
            f"Omega2System(running_count={self._running_count}, "
            f"aces_seen={self._aces_seen})"
        )
