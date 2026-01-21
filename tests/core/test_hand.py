"""Tests for Hand evaluation."""

import pytest

from core.cards import Card, Rank, Suit
from core.hand import Hand, evaluate_hands


class TestHand:
    """Tests for the Hand class."""

    def test_empty_hand(self, empty_hand):
        """Test empty hand properties."""
        assert len(empty_hand) == 0
        assert empty_hand.value == 0
        assert not empty_hand.is_soft
        assert not empty_hand.is_blackjack
        assert not empty_hand.is_busted

    def test_add_card(self, empty_hand):
        """Test adding cards to hand."""
        empty_hand.add_card(Card(Rank.TEN, Suit.SPADES))
        assert len(empty_hand) == 1
        assert empty_hand.value == 10

    def test_hard_hand_value(self, hard_16_hand):
        """Test hard hand value calculation."""
        assert hard_16_hand.value == 16
        assert not hard_16_hand.is_soft

    def test_soft_hand_value(self, soft_17_hand):
        """Test soft hand value calculation."""
        assert soft_17_hand.value == 17
        assert soft_17_hand.is_soft

    def test_blackjack(self, blackjack_hand):
        """Test blackjack detection."""
        assert blackjack_hand.is_blackjack
        assert blackjack_hand.value == 21
        assert blackjack_hand.is_soft

    def test_not_blackjack_three_cards(self):
        """Test that 21 with 3+ cards is not blackjack."""
        hand = Hand()
        hand.add_card(Card(Rank.SEVEN, Suit.SPADES))
        hand.add_card(Card(Rank.SEVEN, Suit.HEARTS))
        hand.add_card(Card(Rank.SEVEN, Suit.CLUBS))
        assert hand.value == 21
        assert not hand.is_blackjack

    def test_bust(self, bust_hand):
        """Test bust detection."""
        assert bust_hand.is_busted
        assert bust_hand.value == 26

    def test_soft_to_hard_transition(self):
        """Test ace switching from 11 to 1."""
        hand = Hand()
        hand.add_card(Card(Rank.ACE, Suit.SPADES))
        assert hand.value == 11
        assert hand.is_soft

        hand.add_card(Card(Rank.FIVE, Suit.HEARTS))
        assert hand.value == 16
        assert hand.is_soft

        hand.add_card(Card(Rank.EIGHT, Suit.CLUBS))
        # Ace now counts as 1
        assert hand.value == 14
        assert hand.is_hard

    def test_multiple_aces(self):
        """Test hand with multiple aces."""
        hand = Hand()
        hand.add_card(Card(Rank.ACE, Suit.SPADES))
        hand.add_card(Card(Rank.ACE, Suit.HEARTS))
        # A-A = 12 (11 + 1)
        assert hand.value == 12
        assert hand.is_soft

        hand.add_card(Card(Rank.ACE, Suit.CLUBS))
        # A-A-A = 13 (11 + 1 + 1)
        assert hand.value == 13
        assert hand.is_soft

        hand.add_card(Card(Rank.NINE, Suit.DIAMONDS))
        # A-A-A-9 = 12 (1 + 1 + 1 + 9)
        assert hand.value == 12
        assert hand.is_hard

    def test_pair_detection(self, pair_8s_hand):
        """Test pair detection."""
        assert pair_8s_hand.is_pair
        assert pair_8s_hand.value == 16

    def test_not_pair_different_ranks(self):
        """Test non-pair with different ranks."""
        hand = Hand()
        hand.add_card(Card(Rank.EIGHT, Suit.SPADES))
        hand.add_card(Card(Rank.NINE, Suit.HEARTS))
        assert not hand.is_pair

    def test_not_pair_three_cards(self):
        """Test that 3 cards is not a pair."""
        hand = Hand()
        hand.add_card(Card(Rank.EIGHT, Suit.SPADES))
        hand.add_card(Card(Rank.EIGHT, Suit.HEARTS))
        hand.add_card(Card(Rank.TWO, Suit.CLUBS))
        assert not hand.is_pair

    def test_can_double(self):
        """Test double down eligibility."""
        hand = Hand()
        hand.add_card(Card(Rank.FIVE, Suit.SPADES))
        hand.add_card(Card(Rank.SIX, Suit.HEARTS))
        assert hand.can_double

        hand.add_card(Card(Rank.TWO, Suit.CLUBS))
        assert not hand.can_double

    def test_clear_hand(self, blackjack_hand):
        """Test clearing a hand."""
        assert len(blackjack_hand) == 2
        blackjack_hand.clear()
        assert len(blackjack_hand) == 0
        assert blackjack_hand.value == 0


class TestEvaluateHands:
    """Tests for hand comparison."""

    def test_player_wins_higher_value(self):
        """Test player wins with higher value."""
        player = Hand()
        player.add_card(Card(Rank.TEN, Suit.SPADES))
        player.add_card(Card(Rank.NINE, Suit.HEARTS))  # 19

        dealer = Hand()
        dealer.add_card(Card(Rank.TEN, Suit.CLUBS))
        dealer.add_card(Card(Rank.EIGHT, Suit.DIAMONDS))  # 18

        assert evaluate_hands(player, dealer) == 1

    def test_dealer_wins_higher_value(self):
        """Test dealer wins with higher value."""
        player = Hand()
        player.add_card(Card(Rank.TEN, Suit.SPADES))
        player.add_card(Card(Rank.SEVEN, Suit.HEARTS))  # 17

        dealer = Hand()
        dealer.add_card(Card(Rank.TEN, Suit.CLUBS))
        dealer.add_card(Card(Rank.NINE, Suit.DIAMONDS))  # 19

        assert evaluate_hands(player, dealer) == -1

    def test_push(self):
        """Test push (tie)."""
        player = Hand()
        player.add_card(Card(Rank.TEN, Suit.SPADES))
        player.add_card(Card(Rank.EIGHT, Suit.HEARTS))  # 18

        dealer = Hand()
        dealer.add_card(Card(Rank.TEN, Suit.CLUBS))
        dealer.add_card(Card(Rank.EIGHT, Suit.DIAMONDS))  # 18

        assert evaluate_hands(player, dealer) == 0

    def test_player_bust_loses(self):
        """Test player busting loses."""
        player = Hand()
        player.add_card(Card(Rank.TEN, Suit.SPADES))
        player.add_card(Card(Rank.SIX, Suit.HEARTS))
        player.add_card(Card(Rank.KING, Suit.CLUBS))  # 26 - bust

        dealer = Hand()
        dealer.add_card(Card(Rank.TEN, Suit.DIAMONDS))
        dealer.add_card(Card(Rank.SEVEN, Suit.SPADES))  # 17

        assert evaluate_hands(player, dealer) == -1

    def test_dealer_bust_player_wins(self):
        """Test dealer busting means player wins."""
        player = Hand()
        player.add_card(Card(Rank.TEN, Suit.SPADES))
        player.add_card(Card(Rank.SEVEN, Suit.HEARTS))  # 17

        dealer = Hand()
        dealer.add_card(Card(Rank.TEN, Suit.CLUBS))
        dealer.add_card(Card(Rank.SIX, Suit.DIAMONDS))
        dealer.add_card(Card(Rank.KING, Suit.SPADES))  # 26 - bust

        assert evaluate_hands(player, dealer) == 1

    def test_both_bust_player_loses(self):
        """Test both busting means player loses (house edge)."""
        player = Hand()
        player.add_card(Card(Rank.TEN, Suit.SPADES))
        player.add_card(Card(Rank.SIX, Suit.HEARTS))
        player.add_card(Card(Rank.KING, Suit.CLUBS))  # 26 - bust

        dealer = Hand()
        dealer.add_card(Card(Rank.TEN, Suit.DIAMONDS))
        dealer.add_card(Card(Rank.SIX, Suit.CLUBS))
        dealer.add_card(Card(Rank.QUEEN, Suit.SPADES))  # 26 - bust

        assert evaluate_hands(player, dealer) == -1

    def test_player_blackjack_vs_dealer_21(self):
        """Test player blackjack beats dealer 21 with 3+ cards."""
        player = Hand()
        player.add_card(Card(Rank.ACE, Suit.SPADES))
        player.add_card(Card(Rank.KING, Suit.HEARTS))  # Blackjack

        dealer = Hand()
        dealer.add_card(Card(Rank.SEVEN, Suit.CLUBS))
        dealer.add_card(Card(Rank.SEVEN, Suit.DIAMONDS))
        dealer.add_card(Card(Rank.SEVEN, Suit.SPADES))  # 21 but not BJ

        assert evaluate_hands(player, dealer) == 1

    def test_both_blackjack_push(self):
        """Test both having blackjack is a push."""
        player = Hand()
        player.add_card(Card(Rank.ACE, Suit.SPADES))
        player.add_card(Card(Rank.KING, Suit.HEARTS))

        dealer = Hand()
        dealer.add_card(Card(Rank.ACE, Suit.CLUBS))
        dealer.add_card(Card(Rank.QUEEN, Suit.DIAMONDS))

        assert evaluate_hands(player, dealer) == 0

    def test_surrendered_hand_loses(self):
        """Test surrendered hand loses."""
        player = Hand()
        player.add_card(Card(Rank.TEN, Suit.SPADES))
        player.add_card(Card(Rank.SIX, Suit.HEARTS))
        player.is_surrendered = True

        dealer = Hand()
        dealer.add_card(Card(Rank.TEN, Suit.CLUBS))
        dealer.add_card(Card(Rank.FIVE, Suit.DIAMONDS))

        assert evaluate_hands(player, dealer) == -1
