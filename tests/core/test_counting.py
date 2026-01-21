"""Tests for card counting systems."""

import pytest

from core.cards import Card, Deck, Rank, Suit
from core.counting import HiLoSystem, KOSystem, Omega2System, WongHalvesSystem


class TestHiLo:
    """Tests for Hi-Lo counting system."""

    def test_full_deck_sums_to_zero(self, hilo):
        """Verify Hi-Lo is balanced (full deck = 0)."""
        assert hilo.full_deck_sum == 0

    def test_is_balanced(self, hilo):
        """Test system reports as balanced."""
        assert hilo.is_balanced

    def test_count_full_deck(self, hilo, deck):
        """Test counting a full deck sums to zero."""
        for card in deck:
            hilo.count_card(card)
        assert hilo.running_count == 0

    def test_low_cards_positive(self, hilo):
        """Test low cards (2-6) are +1."""
        for rank in [Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX]:
            hilo.reset()
            card = Card(rank, Suit.SPADES)
            assert hilo.count_card(card) == 1

    def test_neutral_cards_zero(self, hilo):
        """Test neutral cards (7-9) are 0."""
        for rank in [Rank.SEVEN, Rank.EIGHT, Rank.NINE]:
            hilo.reset()
            card = Card(rank, Suit.SPADES)
            assert hilo.count_card(card) == 0

    def test_high_cards_negative(self, hilo):
        """Test high cards (10-A) are -1."""
        for rank in [Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE]:
            hilo.reset()
            card = Card(rank, Suit.SPADES)
            assert hilo.count_card(card) == -1

    def test_true_count(self, hilo):
        """Test true count calculation."""
        # Count some cards to get a running count
        hilo.count_card(Card(Rank.TWO, Suit.SPADES))  # +1
        hilo.count_card(Card(Rank.THREE, Suit.HEARTS))  # +1
        hilo.count_card(Card(Rank.FOUR, Suit.CLUBS))  # +1
        hilo.count_card(Card(Rank.FIVE, Suit.DIAMONDS))  # +1

        assert hilo.running_count == 4

        # True count = RC / decks remaining
        tc = hilo.true_count(4)  # 4 decks remaining
        assert tc == 1.0

        tc = hilo.true_count(2)  # 2 decks remaining
        assert tc == 2.0

    def test_reset(self, hilo):
        """Test resetting the count."""
        hilo.count_card(Card(Rank.TWO, Suit.SPADES))
        hilo.count_card(Card(Rank.THREE, Suit.HEARTS))
        assert hilo.running_count != 0
        assert hilo.cards_seen > 0

        hilo.reset()
        assert hilo.running_count == 0
        assert hilo.cards_seen == 0


class TestKO:
    """Tests for KO counting system."""

    def test_full_deck_sums_to_four(self, ko):
        """Verify KO is unbalanced (full deck = +4)."""
        assert ko.full_deck_sum == 4

    def test_is_not_balanced(self, ko):
        """Test system reports as unbalanced."""
        assert not ko.is_balanced

    def test_count_full_deck(self, ko, deck):
        """Test counting a full deck sums to +4."""
        for card in deck:
            ko.count_card(card)
        assert ko.running_count == 4

    def test_seven_is_positive(self, ko):
        """Test that 7 is +1 in KO (unlike Hi-Lo)."""
        card = Card(Rank.SEVEN, Suit.SPADES)
        assert ko.count_card(card) == 1

    def test_initial_running_count(self, ko):
        """Test IRC calculation for KO system."""
        # IRC = 4 - 4 * num_decks
        assert ko.initial_running_count(6) == -20  # 6 deck
        assert ko.initial_running_count(2) == -4   # 2 deck
        assert ko.initial_running_count(1) == 0    # 1 deck

    def test_reset_for_shoe(self, ko):
        """Test resetting for a new shoe with IRC."""
        ko.reset_for_shoe(6)
        assert ko.running_count == -20
        assert ko.cards_seen == 0


class TestOmega2:
    """Tests for Omega II counting system."""

    def test_full_deck_sums_to_zero(self, omega2):
        """Verify Omega II is balanced (full deck = 0)."""
        assert omega2.full_deck_sum == 0

    def test_is_balanced(self, omega2):
        """Test system reports as balanced."""
        assert omega2.is_balanced

    def test_count_full_deck(self, omega2, deck):
        """Test counting a full deck sums to zero."""
        for card in deck:
            omega2.count_card(card)
        assert omega2.running_count == 0

    def test_multi_level_values(self, omega2):
        """Test multi-level tag values."""
        # +2 cards: 4, 5, 6
        assert omega2.count_card(Card(Rank.FOUR, Suit.SPADES)) == 2
        omega2.reset()
        assert omega2.count_card(Card(Rank.FIVE, Suit.SPADES)) == 2
        omega2.reset()
        assert omega2.count_card(Card(Rank.SIX, Suit.SPADES)) == 2

        omega2.reset()
        # +1 cards: 2, 3, 7
        assert omega2.count_card(Card(Rank.TWO, Suit.SPADES)) == 1
        omega2.reset()
        assert omega2.count_card(Card(Rank.THREE, Suit.SPADES)) == 1
        omega2.reset()
        assert omega2.count_card(Card(Rank.SEVEN, Suit.SPADES)) == 1

        omega2.reset()
        # -1 card: 9
        assert omega2.count_card(Card(Rank.NINE, Suit.SPADES)) == -1

        omega2.reset()
        # -2 cards: 10, J, Q, K
        assert omega2.count_card(Card(Rank.TEN, Suit.SPADES)) == -2
        omega2.reset()
        assert omega2.count_card(Card(Rank.JACK, Suit.SPADES)) == -2

        omega2.reset()
        # 0 cards: 8, A
        assert omega2.count_card(Card(Rank.EIGHT, Suit.SPADES)) == 0
        omega2.reset()
        assert omega2.count_card(Card(Rank.ACE, Suit.SPADES)) == 0

    def test_ace_side_count(self, omega2):
        """Test ace side count tracking."""
        assert omega2.aces_seen == 0

        omega2.count_card(Card(Rank.ACE, Suit.SPADES))
        assert omega2.aces_seen == 1

        omega2.count_card(Card(Rank.KING, Suit.HEARTS))
        assert omega2.aces_seen == 1  # Still 1

        omega2.count_card(Card(Rank.ACE, Suit.HEARTS))
        assert omega2.aces_seen == 2

    def test_aces_remaining(self, omega2):
        """Test aces remaining calculation."""
        num_decks = 6
        total_aces = num_decks * 4  # 24

        assert omega2.aces_remaining(num_decks) == 24

        omega2.count_card(Card(Rank.ACE, Suit.SPADES))
        omega2.count_card(Card(Rank.ACE, Suit.HEARTS))
        assert omega2.aces_remaining(num_decks) == 22


class TestWongHalves:
    """Tests for Wong Halves counting system."""

    def test_full_deck_sums_to_zero(self, wong_halves):
        """Verify Wong Halves is balanced (full deck = 0)."""
        assert wong_halves.full_deck_sum == 0

    def test_is_balanced(self, wong_halves):
        """Test system reports as balanced."""
        assert wong_halves.is_balanced

    def test_count_full_deck(self, wong_halves, deck):
        """Test counting a full deck sums to zero."""
        for card in deck:
            wong_halves.count_card(card)
        assert abs(wong_halves.running_count) < 0.01  # Float tolerance

    def test_fractional_values(self, wong_halves):
        """Test fractional tag values."""
        # +0.5 cards: 2, 7
        assert wong_halves.count_card(Card(Rank.TWO, Suit.SPADES)) == 0.5
        wong_halves.reset()
        assert wong_halves.count_card(Card(Rank.SEVEN, Suit.SPADES)) == 0.5

        wong_halves.reset()
        # +1.5 cards: 5
        assert wong_halves.count_card(Card(Rank.FIVE, Suit.SPADES)) == 1.5

        wong_halves.reset()
        # -0.5 cards: 9
        assert wong_halves.count_card(Card(Rank.NINE, Suit.SPADES)) == -0.5

    def test_doubled_values(self):
        """Test doubled values option."""
        wong = WongHalvesSystem(use_doubled_values=True)

        # Doubled: 2 = +1 (instead of +0.5)
        assert wong.count_card(Card(Rank.TWO, Suit.SPADES)) == 1
        wong.reset()

        # Doubled: 5 = +3 (instead of +1.5)
        assert wong.count_card(Card(Rank.FIVE, Suit.SPADES)) == 3
        wong.reset()

        # Doubled: 9 = -1 (instead of -0.5)
        assert wong.count_card(Card(Rank.NINE, Suit.SPADES)) == -1

    def test_uses_doubled_values_property(self):
        """Test uses_doubled_values property."""
        normal = WongHalvesSystem(use_doubled_values=False)
        doubled = WongHalvesSystem(use_doubled_values=True)

        assert not normal.uses_doubled_values
        assert doubled.uses_doubled_values


class TestCountingSystemCommon:
    """Common tests for all counting systems."""

    @pytest.mark.parametrize("system_fixture", ["hilo", "ko", "omega2", "wong_halves"])
    def test_count_cards_batch(self, system_fixture, request):
        """Test counting multiple cards at once."""
        system = request.getfixturevalue(system_fixture)
        cards = [
            Card(Rank.TWO, Suit.SPADES),
            Card(Rank.THREE, Suit.HEARTS),
            Card(Rank.FOUR, Suit.CLUBS),
        ]

        total = system.count_cards(cards)
        assert system.cards_seen == 3
        assert system.running_count == total

    @pytest.mark.parametrize("system_fixture", ["hilo", "ko", "omega2", "wong_halves"])
    def test_system_name(self, system_fixture, request):
        """Test system has a name."""
        system = request.getfixturevalue(system_fixture)
        assert len(system.name) > 0
