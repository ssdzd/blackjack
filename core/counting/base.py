"""Abstract base class for card counting systems."""

from abc import ABC, abstractmethod
from typing import Mapping

from core.cards import Card, Rank


class CountingSystem(ABC):
    """
    Abstract base class for card counting systems.

    All counting systems track a running count and can compute a true count
    based on decks remaining.
    """

    def __init__(self) -> None:
        """Initialize the counting system."""
        self._running_count: float = 0.0
        self._cards_seen: int = 0

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the counting system."""
        ...

    @property
    @abstractmethod
    def tag_values(self) -> Mapping[Rank, float]:
        """
        Return the tag value mapping for this system.

        Maps each Rank to its count value.
        """
        ...

    @property
    @abstractmethod
    def is_balanced(self) -> bool:
        """
        Return whether this is a balanced counting system.

        A balanced system sums to 0 over a complete deck.
        An unbalanced system does not.
        """
        ...

    @property
    def full_deck_sum(self) -> float:
        """
        Calculate the sum of tag values for a full 52-card deck.

        For balanced systems, this should be 0.
        For unbalanced systems, this will be non-zero.
        """
        total = 0.0
        for rank in Rank:
            # Each rank appears 4 times in a deck (once per suit)
            total += self.tag_values[rank] * 4
        return total

    def count_card(self, card: Card) -> float:
        """
        Count a single card and update the running count.

        Args:
            card: The card to count

        Returns:
            The tag value of the card
        """
        tag_value = self.tag_values[card.rank]
        self._running_count += tag_value
        self._cards_seen += 1
        return tag_value

    def count_cards(self, cards: list[Card]) -> float:
        """
        Count multiple cards.

        Args:
            cards: List of cards to count

        Returns:
            The total tag value of all cards
        """
        total = 0.0
        for card in cards:
            total += self.count_card(card)
        return total

    @property
    def running_count(self) -> float:
        """Return the current running count."""
        return self._running_count

    def true_count(self, decks_remaining: float) -> float:
        """
        Calculate the true count.

        Args:
            decks_remaining: Number of decks remaining in the shoe

        Returns:
            The true count (running count / decks remaining)
        """
        if decks_remaining <= 0:
            return 0.0
        return self._running_count / decks_remaining

    @property
    def cards_seen(self) -> int:
        """Return the number of cards seen."""
        return self._cards_seen

    def reset(self) -> None:
        """Reset the count to zero."""
        self._running_count = 0.0
        self._cards_seen = 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(running_count={self._running_count})"
