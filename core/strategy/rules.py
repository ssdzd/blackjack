"""Blackjack rule variations."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RuleSet:
    """
    Blackjack table rules configuration.

    All rules that affect strategy decisions and house edge.
    """

    # Deck configuration
    num_decks: int = 6

    # Betting limits
    min_bet: int = 10
    max_bet: int = 1000

    # Dealer rules
    dealer_hits_soft_17: bool = True  # H17 vs S17

    # Blackjack payout (3:2 = 1.5, 6:5 = 1.2)
    blackjack_payout: float = 1.5

    # Double down rules
    double_after_split: bool = True  # DAS
    double_on: Literal["any", "9-11", "10-11"] = "any"

    # Split rules
    resplit_aces: bool = False  # RSA
    hit_split_aces: bool = False  # Usually only one card to split aces
    max_splits: int = 4  # Maximum number of hands from splitting

    # Surrender rules
    surrender: Literal["none", "early", "late"] = "late"

    # Insurance
    insurance_allowed: bool = True

    # Peek rules (dealer checks for blackjack)
    dealer_peeks: bool = True  # US rules (ENHC = European No Hole Card if False)

    def __post_init__(self) -> None:
        """Validate rule combinations."""
        if self.num_decks < 1 or self.num_decks > 8:
            raise ValueError("num_decks must be between 1 and 8")
        if self.blackjack_payout < 1.0:
            raise ValueError("blackjack_payout must be at least 1.0")
        if self.max_splits < 1:
            raise ValueError("max_splits must be at least 1")

    @classmethod
    def vegas_strip(cls) -> "RuleSet":
        """Standard Vegas Strip rules."""
        return cls(
            num_decks=6,
            dealer_hits_soft_17=False,
            blackjack_payout=1.5,
            double_after_split=True,
            double_on="any",
            resplit_aces=False,
            surrender="late",
        )

    @classmethod
    def downtown_vegas(cls) -> "RuleSet":
        """Downtown Las Vegas rules (typically H17)."""
        return cls(
            num_decks=6,
            dealer_hits_soft_17=True,
            blackjack_payout=1.5,
            double_after_split=True,
            double_on="any",
            resplit_aces=False,
            surrender="late",
        )

    @classmethod
    def single_deck(cls) -> "RuleSet":
        """Single deck rules."""
        return cls(
            num_decks=1,
            dealer_hits_soft_17=True,
            blackjack_payout=1.5,
            double_after_split=False,
            double_on="any",
            resplit_aces=False,
            surrender="none",
        )

    @classmethod
    def atlantic_city(cls) -> "RuleSet":
        """Atlantic City rules."""
        return cls(
            num_decks=8,
            dealer_hits_soft_17=False,
            blackjack_payout=1.5,
            double_after_split=True,
            double_on="any",
            resplit_aces=False,
            surrender="late",
        )
