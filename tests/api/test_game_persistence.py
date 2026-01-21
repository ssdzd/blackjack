"""Tests for game state persistence (serialization/deserialization)."""

import pytest
from decimal import Decimal

from api.routes.game import (
    _serialize_card,
    _deserialize_card,
    _serialize_hand,
    _deserialize_hand,
    _serialize_game,
    _deserialize_game,
)
from core.cards import Card, Rank, Suit
from core.hand import Hand
from core.game import BlackjackGame
from core.strategy.rules import RuleSet


class TestCardSerialization:
    """Tests for card serialization."""

    def test_serialize_card_roundtrip(self):
        """Test that a card can be serialized and deserialized."""
        card = Card(Rank.ACE, Suit.SPADES)

        serialized = _serialize_card(card)
        restored = _deserialize_card(serialized)

        assert restored.rank == card.rank
        assert restored.suit == card.suit

    def test_deserialize_card_preserves_rank_suit(self):
        """Test that deserialization preserves rank and suit values."""
        # Test with various cards
        test_cards = [
            Card(Rank.TWO, Suit.CLUBS),
            Card(Rank.TEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.SPADES),
            Card(Rank.KING, Suit.CLUBS),
            Card(Rank.ACE, Suit.HEARTS),
        ]

        for card in test_cards:
            serialized = _serialize_card(card)
            restored = _deserialize_card(serialized)

            assert restored.rank == card.rank, f"Rank mismatch for {card}"
            assert restored.suit == card.suit, f"Suit mismatch for {card}"

    def test_serialize_card_structure(self):
        """Test that serialized card has expected structure."""
        card = Card(Rank.SEVEN, Suit.DIAMONDS)

        serialized = _serialize_card(card)

        assert "rank" in serialized
        assert "suit" in serialized
        assert serialized["rank"] == Rank.SEVEN.value
        assert serialized["suit"] == Suit.DIAMONDS.value


class TestHandSerialization:
    """Tests for hand serialization."""

    def test_serialize_hand_with_cards(self):
        """Test serializing a hand with cards."""
        hand = Hand(
            cards=[
                Card(Rank.TEN, Suit.SPADES),
                Card(Rank.ACE, Suit.HEARTS),
            ],
            bet=100,
        )

        serialized = _serialize_hand(hand)

        assert len(serialized["cards"]) == 2
        assert serialized["bet"] == 100
        assert serialized["is_doubled"] is False
        assert serialized["is_split_hand"] is False
        assert serialized["is_surrendered"] is False

    def test_deserialize_hand_preserves_flags(self):
        """Test that deserialization preserves hand flags."""
        hand = Hand(
            cards=[Card(Rank.EIGHT, Suit.CLUBS)],
            bet=50,
            is_doubled=True,
            is_split_hand=True,
            is_surrendered=False,
        )

        serialized = _serialize_hand(hand)
        restored = _deserialize_hand(serialized)

        assert restored.bet == 50
        assert restored.is_doubled is True
        assert restored.is_split_hand is True
        assert restored.is_surrendered is False
        assert len(restored.cards) == 1

    def test_hand_roundtrip_preserves_cards(self):
        """Test that hand roundtrip preserves card values."""
        original_cards = [
            Card(Rank.FIVE, Suit.DIAMONDS),
            Card(Rank.SIX, Suit.HEARTS),
            Card(Rank.TEN, Suit.CLUBS),
        ]
        hand = Hand(cards=original_cards, bet=25)

        serialized = _serialize_hand(hand)
        restored = _deserialize_hand(serialized)

        assert len(restored.cards) == len(original_cards)
        for orig, rest in zip(original_cards, restored.cards):
            assert rest.rank == orig.rank
            assert rest.suit == orig.suit

    def test_deserialize_hand_surrendered(self):
        """Test deserialization of surrendered hand."""
        hand = Hand(
            cards=[Card(Rank.NINE, Suit.SPADES), Card(Rank.SEVEN, Suit.CLUBS)],
            bet=100,
            is_surrendered=True,
        )

        serialized = _serialize_hand(hand)
        restored = _deserialize_hand(serialized)

        assert restored.is_surrendered is True


class TestGameSerialization:
    """Tests for game state serialization."""

    @pytest.fixture
    def game(self):
        """Create a fresh game."""
        rules = RuleSet(
            num_decks=6,
            min_bet=10,
            max_bet=1000,
            dealer_hits_soft_17=True,
            blackjack_payout=1.5,
        )
        return BlackjackGame(
            rules=rules,
            num_decks=6,
            penetration=0.75,
            initial_bankroll=Decimal("1000"),
        )

    def test_serialize_game_preserves_state(self, game):
        """Test that serialization captures game state."""
        serialized = _serialize_game(game)

        assert "state" in serialized
        assert "bankroll" in serialized
        assert "shoe_cards" in serialized
        assert "rules" in serialized

    def test_deserialize_game_restores_bankroll(self, game):
        """Test that deserialization restores bankroll correctly."""
        # Modify bankroll
        game.player.bankroll = Decimal("750.50")

        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert restored.player.bankroll == Decimal("750.50")

    def test_game_roundtrip_preserves_shoe(self, game):
        """Test that game roundtrip preserves shoe configuration."""
        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert restored.shoe._num_decks == game.shoe._num_decks
        assert restored.shoe._penetration == game.shoe._penetration

    def test_game_roundtrip_preserves_rules(self, game):
        """Test that game roundtrip preserves rules."""
        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert restored.rules.num_decks == game.rules.num_decks
        assert restored.rules.min_bet == game.rules.min_bet
        assert restored.rules.max_bet == game.rules.max_bet
        assert restored.rules.dealer_hits_soft_17 == game.rules.dealer_hits_soft_17
        assert restored.rules.blackjack_payout == game.rules.blackjack_payout

    def test_game_roundtrip_preserves_player_hands(self, game):
        """Test that roundtrip preserves player hands."""
        # Place a bet and deal
        game.bet(100)

        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert len(restored.player.hands) == len(game.player.hands)
        for orig_hand, rest_hand in zip(game.player.hands, restored.player.hands):
            assert len(rest_hand.cards) == len(orig_hand.cards)
            assert rest_hand.bet == orig_hand.bet

    def test_game_roundtrip_mid_hand(self, game):
        """Test roundtrip during active hand (PLAYER_TURN state)."""
        # Start a hand
        game.bet(100)

        # Get initial state
        initial_state = game._machine_state
        initial_bankroll = game.player.bankroll
        initial_hand_count = len(game.player.hands)

        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert restored._machine_state == initial_state
        assert restored.player.bankroll == initial_bankroll
        assert len(restored.player.hands) == initial_hand_count

    def test_game_roundtrip_preserves_dealer_hand(self, game):
        """Test that dealer hand is preserved in roundtrip."""
        game.bet(100)

        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert len(restored.dealer_hand.cards) == len(game.dealer_hand.cards)

    def test_serialize_game_includes_insurance_bet(self, game):
        """Test that insurance bet is serialized."""
        game.player.insurance_bet = Decimal("50")

        serialized = _serialize_game(game)

        assert serialized["insurance_bet"] == "50"

    def test_deserialize_game_restores_insurance_bet(self, game):
        """Test that insurance bet is restored."""
        game.player.insurance_bet = Decimal("50")

        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert restored.player.insurance_bet == Decimal("50")

    def test_game_roundtrip_preserves_current_hand_index(self, game):
        """Test that current hand index is preserved."""
        game.bet(100)
        original_index = game.player.current_hand_index

        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert restored.player.current_hand_index == original_index

    def test_serialize_game_with_custom_rules(self):
        """Test serialization with custom rules."""
        custom_rules = RuleSet(
            num_decks=8,
            min_bet=25,
            max_bet=5000,
            dealer_hits_soft_17=False,
            blackjack_payout=1.2,
            double_after_split=False,
            resplit_aces=True,
            max_splits=2,
            surrender="early",
        )
        game = BlackjackGame(
            rules=custom_rules,
            num_decks=8,
            penetration=0.80,
            initial_bankroll=Decimal("5000"),
        )

        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert restored.rules.num_decks == 8
        assert restored.rules.min_bet == 25
        assert restored.rules.max_bet == 5000
        assert restored.rules.dealer_hits_soft_17 is False
        assert restored.rules.blackjack_payout == 1.2
        assert restored.rules.double_after_split is False
        assert restored.rules.resplit_aces is True
        assert restored.rules.max_splits == 2
        assert restored.rules.surrender == "early"

    def test_game_roundtrip_after_multiple_hands(self, game):
        """Test roundtrip after multiple hands have been played."""
        # Play a few rounds to change shoe state
        for _ in range(3):
            if game.shoe.needs_shuffle:
                game.shoe.shuffle()
            game.bet(100)
            while game.can_stand:
                game.stand()

        cards_before = len(game.shoe._cards)

        serialized = _serialize_game(game)
        restored = _deserialize_game(serialized)

        assert len(restored.shoe._cards) == cards_before
