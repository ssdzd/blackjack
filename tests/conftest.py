"""Pytest fixtures for blackjack trainer tests."""

import pytest
from decimal import Decimal
from random import Random

from core.cards import Card, Deck, Shoe, Rank, Suit
from core.hand import Hand
from core.counting import HiLoSystem, KOSystem, Omega2System, WongHalvesSystem
from core.strategy import BasicStrategy, RuleSet
from core.game import BlackjackGame


@pytest.fixture
def rng():
    """Seeded random number generator for reproducible tests."""
    return Random(42)


@pytest.fixture
def deck(rng):
    """A shuffled deck."""
    d = Deck(rng=rng)
    d.shuffle()
    return d


@pytest.fixture
def shoe(rng):
    """A shuffled 6-deck shoe."""
    s = Shoe(num_decks=6, penetration=0.75, rng=rng)
    s.shuffle()
    return s


@pytest.fixture
def empty_hand():
    """An empty player hand."""
    return Hand()


@pytest.fixture
def blackjack_hand():
    """A natural blackjack hand."""
    hand = Hand()
    hand.add_card(Card(Rank.ACE, Suit.SPADES))
    hand.add_card(Card(Rank.KING, Suit.HEARTS))
    return hand


@pytest.fixture
def soft_17_hand():
    """A soft 17 hand (A-6)."""
    hand = Hand()
    hand.add_card(Card(Rank.ACE, Suit.SPADES))
    hand.add_card(Card(Rank.SIX, Suit.HEARTS))
    return hand


@pytest.fixture
def hard_16_hand():
    """A hard 16 hand (10-6)."""
    hand = Hand()
    hand.add_card(Card(Rank.TEN, Suit.SPADES))
    hand.add_card(Card(Rank.SIX, Suit.HEARTS))
    return hand


@pytest.fixture
def pair_8s_hand():
    """A pair of 8s hand."""
    hand = Hand()
    hand.add_card(Card(Rank.EIGHT, Suit.SPADES))
    hand.add_card(Card(Rank.EIGHT, Suit.HEARTS))
    return hand


@pytest.fixture
def bust_hand():
    """A busted hand."""
    hand = Hand()
    hand.add_card(Card(Rank.TEN, Suit.SPADES))
    hand.add_card(Card(Rank.SIX, Suit.HEARTS))
    hand.add_card(Card(Rank.KING, Suit.CLUBS))
    return hand


@pytest.fixture
def hilo():
    """Hi-Lo counting system."""
    return HiLoSystem()


@pytest.fixture
def ko():
    """KO counting system."""
    return KOSystem()


@pytest.fixture
def omega2():
    """Omega II counting system."""
    return Omega2System()


@pytest.fixture
def wong_halves():
    """Wong Halves counting system."""
    return WongHalvesSystem()


@pytest.fixture
def rules():
    """Default ruleset."""
    return RuleSet()


@pytest.fixture
def vegas_strip_rules():
    """Vegas Strip rules."""
    return RuleSet.vegas_strip()


@pytest.fixture
def basic_strategy(rules):
    """Basic strategy for default rules."""
    return BasicStrategy(rules)


@pytest.fixture
def game(rng):
    """A new game instance."""
    return BlackjackGame(
        initial_bankroll=Decimal("1000"),
        rng=rng,
    )


# Hypothesis strategies for property-based testing
try:
    from hypothesis import strategies as st

    @st.composite
    def card_strategy(draw):
        """Generate a random card."""
        rank = draw(st.sampled_from(list(Rank)))
        suit = draw(st.sampled_from(list(Suit)))
        return Card(rank, suit)

    @st.composite
    def hand_strategy(draw, min_cards=2, max_cards=5):
        """Generate a random hand."""
        cards = draw(st.lists(card_strategy(), min_size=min_cards, max_size=max_cards))
        hand = Hand()
        for card in cards:
            hand.add_card(card)
        return hand

except ImportError:
    pass  # hypothesis not installed
