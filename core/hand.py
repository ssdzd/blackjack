"""Hand evaluation for blackjack."""

from dataclasses import dataclass, field
from typing import Iterator

from core.cards import Card


@dataclass
class Hand:
    """A blackjack hand with value calculation."""

    cards: list[Card] = field(default_factory=list)
    bet: int = 0
    is_doubled: bool = False
    is_split_hand: bool = False
    is_surrendered: bool = False

    def add_card(self, card: Card) -> None:
        """Add a card to the hand."""
        self.cards.append(card)

    def clear(self) -> None:
        """Remove all cards from the hand."""
        self.cards.clear()
        self.is_doubled = False
        self.is_split_hand = False
        self.is_surrendered = False

    @property
    def value(self) -> int:
        """
        Calculate the best hand value.

        Returns the highest value that doesn't bust, or the lowest bust value.
        """
        total = 0
        aces = 0

        for card in self.cards:
            if card.is_ace:
                aces += 1
                total += 11
            else:
                total += card.value

        # Reduce aces from 11 to 1 as needed
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    @property
    def is_soft(self) -> bool:
        """
        Check if the hand is soft (has an ace counted as 11).

        A hand is soft if it contains an ace that can be counted as 11
        without busting.
        """
        if not any(card.is_ace for card in self.cards):
            return False

        # Calculate value without any aces as 11
        total_hard = sum(1 if card.is_ace else card.value for card in self.cards)

        # If we can add 10 (making one ace worth 11) without busting, it's soft
        return total_hard + 10 <= 21

    @property
    def is_hard(self) -> bool:
        """Check if the hand is hard (not soft)."""
        return not self.is_soft

    @property
    def is_blackjack(self) -> bool:
        """Check if the hand is a natural blackjack (21 with 2 cards)."""
        return (
            len(self.cards) == 2
            and self.value == 21
            and not self.is_split_hand
        )

    @property
    def is_busted(self) -> bool:
        """Check if the hand has busted (value > 21)."""
        return self.value > 21

    @property
    def is_pair(self) -> bool:
        """Check if the hand is a pair (two cards of same rank)."""
        return (
            len(self.cards) == 2
            and self.cards[0].rank == self.cards[1].rank
        )

    @property
    def is_splittable(self) -> bool:
        """Check if the hand can be split."""
        return self.is_pair and not self.is_split_hand

    @property
    def can_double(self) -> bool:
        """Check if the hand can be doubled down."""
        return len(self.cards) == 2 and not self.is_doubled

    @property
    def num_cards(self) -> int:
        """Return the number of cards in the hand."""
        return len(self.cards)

    def __len__(self) -> int:
        return len(self.cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self.cards)

    def __str__(self) -> str:
        cards_str = " ".join(str(card) for card in self.cards)
        value_str = f"({self.value})"
        if self.is_soft:
            value_str = f"(soft {self.value})"
        if self.is_blackjack:
            value_str = "(BLACKJACK)"
        if self.is_busted:
            value_str = "(BUST)"
        return f"{cards_str} {value_str}"

    def __repr__(self) -> str:
        return f"Hand({self.cards!r}, value={self.value})"


def evaluate_hands(player_hand: Hand, dealer_hand: Hand) -> int:
    """
    Compare player and dealer hands.

    Returns:
        1 if player wins
        -1 if dealer wins
        0 if push (tie)
    """
    player_value = player_hand.value
    dealer_value = dealer_hand.value

    # Handle surrendered hands
    if player_hand.is_surrendered:
        return -1

    # Player busts always loses
    if player_hand.is_busted:
        return -1

    # Dealer busts, player wins
    if dealer_hand.is_busted:
        return 1

    # Blackjack comparisons
    player_bj = player_hand.is_blackjack
    dealer_bj = dealer_hand.is_blackjack

    if player_bj and dealer_bj:
        return 0  # Push
    if player_bj:
        return 1  # Player blackjack wins
    if dealer_bj:
        return -1  # Dealer blackjack wins

    # Compare values
    if player_value > dealer_value:
        return 1
    if dealer_value > player_value:
        return -1
    return 0  # Push
