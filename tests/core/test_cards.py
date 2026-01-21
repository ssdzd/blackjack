"""Tests for Card, Deck, and Shoe classes."""

import pytest
from random import Random

from core.cards import Card, Deck, Shoe, Rank, Suit


class TestCard:
    """Tests for the Card class."""

    def test_card_creation(self):
        """Test creating a card."""
        card = Card(Rank.ACE, Suit.SPADES)
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES

    def test_card_immutability(self):
        """Test that cards are immutable."""
        card = Card(Rank.ACE, Suit.SPADES)
        with pytest.raises(AttributeError):
            card.rank = Rank.KING

    def test_card_value(self):
        """Test card blackjack values."""
        assert Card(Rank.TWO, Suit.HEARTS).value == 2
        assert Card(Rank.TEN, Suit.HEARTS).value == 10
        assert Card(Rank.JACK, Suit.HEARTS).value == 10
        assert Card(Rank.QUEEN, Suit.HEARTS).value == 10
        assert Card(Rank.KING, Suit.HEARTS).value == 10
        assert Card(Rank.ACE, Suit.HEARTS).value == 11

    def test_card_is_ace(self):
        """Test ace detection."""
        assert Card(Rank.ACE, Suit.SPADES).is_ace
        assert not Card(Rank.KING, Suit.SPADES).is_ace

    def test_card_is_ten_value(self):
        """Test ten-value detection."""
        assert Card(Rank.TEN, Suit.SPADES).is_ten_value
        assert Card(Rank.JACK, Suit.SPADES).is_ten_value
        assert Card(Rank.QUEEN, Suit.SPADES).is_ten_value
        assert Card(Rank.KING, Suit.SPADES).is_ten_value
        assert not Card(Rank.NINE, Suit.SPADES).is_ten_value
        assert not Card(Rank.ACE, Suit.SPADES).is_ten_value

    def test_card_from_string(self):
        """Test creating cards from strings."""
        assert Card.from_string("AS") == Card(Rank.ACE, Suit.SPADES)
        assert Card.from_string("2H") == Card(Rank.TWO, Suit.HEARTS)
        assert Card.from_string("10D") == Card(Rank.TEN, Suit.DIAMONDS)
        assert Card.from_string("KC") == Card(Rank.KING, Suit.CLUBS)

    def test_card_from_string_with_symbols(self):
        """Test creating cards from strings with suit symbols."""
        assert Card.from_string("A♠") == Card(Rank.ACE, Suit.SPADES)
        assert Card.from_string("K♥") == Card(Rank.KING, Suit.HEARTS)

    def test_card_str(self):
        """Test string representation."""
        card = Card(Rank.ACE, Suit.SPADES)
        assert "A" in str(card)
        assert "♠" in str(card)

    def test_card_equality(self):
        """Test card equality."""
        card1 = Card(Rank.ACE, Suit.SPADES)
        card2 = Card(Rank.ACE, Suit.SPADES)
        card3 = Card(Rank.KING, Suit.SPADES)
        assert card1 == card2
        assert card1 != card3

    def test_card_hash(self):
        """Test that cards can be used in sets/dicts."""
        card1 = Card(Rank.ACE, Suit.SPADES)
        card2 = Card(Rank.ACE, Suit.SPADES)
        cards = {card1, card2}
        assert len(cards) == 1


class TestDeck:
    """Tests for the Deck class."""

    def test_deck_creation(self):
        """Test creating a new deck."""
        deck = Deck()
        assert len(deck) == 52

    def test_deck_has_all_cards(self):
        """Test that deck contains all 52 unique cards."""
        deck = Deck()
        cards = list(deck)
        assert len(cards) == 52
        assert len(set(cards)) == 52  # All unique

    def test_deck_shuffle(self):
        """Test shuffling changes card order."""
        rng = Random(42)
        deck1 = Deck(rng=rng)
        order_before = list(deck1)

        deck1.shuffle()
        order_after = list(deck1)

        # Should have same cards but different order
        assert set(order_before) == set(order_after)
        assert order_before != order_after

    def test_deck_draw(self):
        """Test drawing cards from deck."""
        deck = Deck()
        card = deck.draw()
        assert isinstance(card, Card)
        assert len(deck) == 51

    def test_deck_draw_all(self):
        """Test drawing all cards from deck."""
        deck = Deck()
        cards = [deck.draw() for _ in range(52)]
        assert len(deck) == 0
        assert len(cards) == 52

    def test_deck_draw_empty_raises(self):
        """Test that drawing from empty deck raises error."""
        deck = Deck()
        for _ in range(52):
            deck.draw()

        with pytest.raises(IndexError):
            deck.draw()

    def test_deck_reset(self):
        """Test resetting deck."""
        deck = Deck()
        deck.draw()
        deck.draw()
        assert len(deck) == 50

        deck.reset()
        assert len(deck) == 52


class TestShoe:
    """Tests for the Shoe class."""

    def test_shoe_creation(self):
        """Test creating a shoe with multiple decks."""
        shoe = Shoe(num_decks=6)
        assert len(shoe) == 312  # 6 * 52
        assert shoe.num_decks == 6

    def test_shoe_single_deck(self):
        """Test single deck shoe."""
        shoe = Shoe(num_decks=1)
        assert len(shoe) == 52

    def test_shoe_eight_deck(self):
        """Test eight deck shoe."""
        shoe = Shoe(num_decks=8)
        assert len(shoe) == 416

    def test_shoe_invalid_decks_raises(self):
        """Test that invalid deck count raises error."""
        with pytest.raises(ValueError):
            Shoe(num_decks=0)

    def test_shoe_invalid_penetration_raises(self):
        """Test that invalid penetration raises error."""
        with pytest.raises(ValueError):
            Shoe(num_decks=6, penetration=0)
        with pytest.raises(ValueError):
            Shoe(num_decks=6, penetration=1.5)

    def test_shoe_shuffle(self):
        """Test shuffling shoe."""
        shoe = Shoe(num_decks=6)
        shoe.shuffle()
        assert len(shoe) == 312

    def test_shoe_draw(self):
        """Test drawing from shoe."""
        shoe = Shoe(num_decks=6)
        shoe.shuffle()
        card = shoe.draw()
        assert isinstance(card, Card)
        assert len(shoe) == 311

    def test_shoe_needs_shuffle(self):
        """Test cut card detection."""
        shoe = Shoe(num_decks=6, penetration=0.75)
        shoe.shuffle()

        # Draw until we hit the cut card
        initial_remaining = len(shoe)
        cards_to_cut = int(initial_remaining * 0.75)

        for _ in range(cards_to_cut - 1):
            shoe.draw()
            assert not shoe.needs_shuffle

        shoe.draw()
        assert shoe.needs_shuffle

    def test_shoe_decks_remaining(self):
        """Test decks remaining calculation."""
        shoe = Shoe(num_decks=6)
        shoe.shuffle()
        assert shoe.decks_remaining == 6.0

        # Draw one deck worth
        for _ in range(52):
            shoe.draw()

        assert abs(shoe.decks_remaining - 5.0) < 0.01

    def test_shoe_cards_dealt(self):
        """Test cards dealt tracking."""
        shoe = Shoe(num_decks=6)
        shoe.shuffle()
        assert shoe.cards_dealt == 0

        shoe.draw()
        shoe.draw()
        shoe.draw()
        assert shoe.cards_dealt == 3
