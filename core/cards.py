"""Card, Deck, and Shoe classes - immutable card representations."""

from dataclasses import dataclass
from enum import Enum, auto
from random import Random
from typing import Iterator


class Suit(Enum):
    """Card suits."""

    CLUBS = auto()
    DIAMONDS = auto()
    HEARTS = auto()
    SPADES = auto()

    def __str__(self) -> str:
        symbols = {
            Suit.CLUBS: "♣",
            Suit.DIAMONDS: "♦",
            Suit.HEARTS: "♥",
            Suit.SPADES: "♠",
        }
        return symbols[self]


class Rank(Enum):
    """Card ranks with blackjack values."""

    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    def __str__(self) -> str:
        if self.value <= 10:
            return str(self.value)
        return {
            Rank.JACK: "J",
            Rank.QUEEN: "Q",
            Rank.KING: "K",
            Rank.ACE: "A",
        }[self]

    @property
    def blackjack_value(self) -> int:
        """Return the blackjack point value (Ace = 11, face cards = 10)."""
        if self.value <= 10:
            return self.value
        if self == Rank.ACE:
            return 11
        return 10  # Face cards

    @property
    def is_ace(self) -> bool:
        """Check if this rank is an Ace."""
        return self == Rank.ACE

    @property
    def is_ten_value(self) -> bool:
        """Check if this rank has a value of 10."""
        return self.blackjack_value == 10


@dataclass(frozen=True, slots=True)
class Card:
    """Immutable playing card."""

    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    def __repr__(self) -> str:
        return f"Card({self.rank.name}, {self.suit.name})"

    @property
    def value(self) -> int:
        """Return the blackjack point value."""
        return self.rank.blackjack_value

    @property
    def is_ace(self) -> bool:
        """Check if this card is an Ace."""
        return self.rank.is_ace

    @property
    def is_ten_value(self) -> bool:
        """Check if this card has a value of 10."""
        return self.rank.is_ten_value

    @classmethod
    def from_string(cls, s: str) -> "Card":
        """Create a card from a string like '2♣', 'AS', 'Kh'."""
        s = s.strip().upper()
        if len(s) < 2:
            raise ValueError(f"Invalid card string: {s}")

        rank_str = s[:-1]
        suit_str = s[-1]

        rank_map = {
            "2": Rank.TWO,
            "3": Rank.THREE,
            "4": Rank.FOUR,
            "5": Rank.FIVE,
            "6": Rank.SIX,
            "7": Rank.SEVEN,
            "8": Rank.EIGHT,
            "9": Rank.NINE,
            "10": Rank.TEN,
            "T": Rank.TEN,
            "J": Rank.JACK,
            "Q": Rank.QUEEN,
            "K": Rank.KING,
            "A": Rank.ACE,
        }

        suit_map = {
            "C": Suit.CLUBS,
            "♣": Suit.CLUBS,
            "D": Suit.DIAMONDS,
            "♦": Suit.DIAMONDS,
            "H": Suit.HEARTS,
            "♥": Suit.HEARTS,
            "S": Suit.SPADES,
            "♠": Suit.SPADES,
        }

        if rank_str not in rank_map:
            raise ValueError(f"Invalid rank: {rank_str}")
        if suit_str not in suit_map:
            raise ValueError(f"Invalid suit: {suit_str}")

        return cls(rank_map[rank_str], suit_map[suit_str])


class Deck:
    """A standard 52-card deck."""

    def __init__(self, rng: Random | None = None) -> None:
        """Initialize a new deck."""
        self._rng = rng or Random()
        self._cards: list[Card] = []
        self.reset()

    def reset(self) -> None:
        """Reset deck to all 52 cards in order."""
        self._cards = [Card(rank, suit) for suit in Suit for rank in Rank]

    def shuffle(self) -> None:
        """Shuffle the deck."""
        self._rng.shuffle(self._cards)

    def draw(self) -> Card:
        """Draw a card from the top of the deck."""
        if not self._cards:
            raise IndexError("Cannot draw from empty deck")
        return self._cards.pop()

    def __len__(self) -> int:
        return len(self._cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self._cards)

    @property
    def cards_remaining(self) -> int:
        """Return the number of cards remaining."""
        return len(self._cards)


class Shoe:
    """A multi-deck shoe for blackjack."""

    def __init__(
        self,
        num_decks: int = 6,
        penetration: float = 0.75,
        rng: Random | None = None,
    ) -> None:
        """
        Initialize a shoe with multiple decks.

        Args:
            num_decks: Number of decks in the shoe (typically 6 or 8)
            penetration: Fraction of shoe dealt before reshuffle (0.0-1.0)
            rng: Random number generator for shuffling
        """
        if num_decks < 1:
            raise ValueError("Shoe must have at least 1 deck")
        if not 0.0 < penetration <= 1.0:
            raise ValueError("Penetration must be between 0 and 1")

        self._num_decks = num_decks
        self._penetration = penetration
        self._rng = rng or Random()
        self._cards: list[Card] = []
        self._cut_card_position: int = 0
        self.reset()

    def reset(self) -> None:
        """Reset shoe to all cards from all decks."""
        self._cards = [
            Card(rank, suit)
            for _ in range(self._num_decks)
            for suit in Suit
            for rank in Rank
        ]
        self._cut_card_position = int(len(self._cards) * self._penetration)

    def shuffle(self) -> None:
        """Shuffle all cards in the shoe."""
        self.reset()
        self._rng.shuffle(self._cards)

    def draw(self) -> Card:
        """Draw a card from the shoe."""
        if not self._cards:
            raise IndexError("Cannot draw from empty shoe")
        return self._cards.pop()

    @property
    def needs_shuffle(self) -> bool:
        """Check if the cut card has been reached."""
        return len(self._cards) <= (self.total_cards - self._cut_card_position)

    @property
    def cards_remaining(self) -> int:
        """Return the number of cards remaining."""
        return len(self._cards)

    @property
    def cards_dealt(self) -> int:
        """Return the number of cards dealt."""
        return self.total_cards - len(self._cards)

    @property
    def total_cards(self) -> int:
        """Return the total number of cards in a full shoe."""
        return self._num_decks * 52

    @property
    def num_decks(self) -> int:
        """Return the number of decks in the shoe."""
        return self._num_decks

    @property
    def decks_remaining(self) -> float:
        """Return the estimated number of decks remaining."""
        return len(self._cards) / 52

    @property
    def penetration(self) -> float:
        """Return the configured penetration."""
        return self._penetration

    def __len__(self) -> int:
        return len(self._cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self._cards)
