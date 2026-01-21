"""Blackjack game engine with state machine."""

from dataclasses import dataclass, field
from decimal import Decimal
from random import Random
from typing import Callable

from transitions import Machine

from core.cards import Card, Shoe
from core.hand import Hand, evaluate_hands
from core.strategy.rules import RuleSet
from core.game.events import EventEmitter, EventType, GameEvent
from core.game.state import GameState


@dataclass
class PlayerState:
    """Player state during a round."""

    hands: list[Hand] = field(default_factory=list)
    current_hand_index: int = 0
    bankroll: Decimal = Decimal("1000")
    insurance_bet: Decimal = Decimal("0")

    @property
    def current_hand(self) -> Hand | None:
        """Get the current active hand."""
        if 0 <= self.current_hand_index < len(self.hands):
            return self.hands[self.current_hand_index]
        return None

    def add_hand(self, bet: int = 0) -> Hand:
        """Add a new hand."""
        hand = Hand(bet=bet)
        self.hands.append(hand)
        return hand

    def reset_hands(self) -> None:
        """Reset all hands for a new round."""
        self.hands.clear()
        self.current_hand_index = 0
        self.insurance_bet = Decimal("0")


class BlackjackGame:
    """
    Blackjack game engine using a state machine.

    This is the core game logic, completely UI-agnostic.
    Communication happens through events and return values only.
    """

    # State machine states
    STATES = [s.name.lower() for s in GameState]

    # State machine transitions
    TRANSITIONS = [
        {"trigger": "place_bet", "source": "waiting_for_bet", "dest": "dealing"},
        {"trigger": "deal_cards", "source": "dealing", "dest": "player_turn"},
        {"trigger": "dealer_blackjack", "source": "dealing", "dest": "resolving"},
        # Insurance transitions
        {"trigger": "offer_insurance", "source": "dealing", "dest": "offering_insurance"},
        {"trigger": "insurance_decision", "source": "offering_insurance", "dest": "player_turn"},
        {"trigger": "dealer_blackjack_after_insurance", "source": "offering_insurance", "dest": "resolving"},
        # Normal play transitions
        {"trigger": "player_action", "source": "player_turn", "dest": "player_turn"},
        {"trigger": "player_done", "source": "player_turn", "dest": "dealer_turn"},
        {"trigger": "player_busts_all", "source": "player_turn", "dest": "resolving"},
        {"trigger": "dealer_plays", "source": "dealer_turn", "dest": "resolving"},
        {"trigger": "resolve", "source": "resolving", "dest": "round_complete"},
        {"trigger": "new_round", "source": "round_complete", "dest": "waiting_for_bet"},
        {"trigger": "end_game", "source": "*", "dest": "game_over"},
    ]

    def __init__(
        self,
        rules: RuleSet | None = None,
        num_decks: int = 6,
        penetration: float = 0.75,
        initial_bankroll: Decimal = Decimal("1000"),
        rng: Random | None = None,
    ) -> None:
        """
        Initialize a new blackjack game.

        Args:
            rules: Game rules (uses defaults if not provided)
            num_decks: Number of decks in shoe
            penetration: Deck penetration before shuffle
            initial_bankroll: Starting bankroll
            rng: Random number generator for reproducible games
        """
        self.rules = rules or RuleSet(num_decks=num_decks)
        self.shoe = Shoe(num_decks=num_decks, penetration=penetration, rng=rng)
        self.shoe.shuffle()

        self.player = PlayerState(bankroll=initial_bankroll)
        self.dealer_hand = Hand()
        self.events = EventEmitter()

        # Initialize state machine
        self.machine = Machine(
            model=self,
            states=self.STATES,
            transitions=self.TRANSITIONS,
            initial="waiting_for_bet",
            auto_transitions=False,
            model_attribute="_machine_state",
        )

    @property
    def state(self) -> GameState:
        """Get current game state as enum."""
        return GameState[self._machine_state.upper()]  # type: ignore

    def subscribe(
        self,
        handler: Callable[[GameEvent], None],
        event_type: EventType | None = None,
    ) -> None:
        """Subscribe to game events."""
        self.events.subscribe(handler, event_type)

    def bet(self, amount: int) -> bool:
        """
        Place a bet to start a new round.

        Args:
            amount: Bet amount

        Returns:
            True if bet was accepted
        """
        if self.state != GameState.WAITING_FOR_BET:
            self.events.emit_new(
                EventType.INVALID_ACTION,
                message="Cannot bet in current state",
                state=self.state.name,
            )
            return False

        if amount < self.rules.min_bet or amount > self.rules.max_bet:
            self.events.emit_new(
                EventType.INVALID_ACTION,
                message=f"Bet must be between {self.rules.min_bet} and {self.rules.max_bet}",
            )
            return False

        if Decimal(str(amount)) > self.player.bankroll:
            self.events.emit_new(
                EventType.INSUFFICIENT_FUNDS,
                required=amount,
                available=float(self.player.bankroll),
            )
            return False

        # Reset for new round
        self.player.reset_hands()
        self.dealer_hand.clear()

        # Create player's main hand with bet
        self.player.add_hand(bet=amount)

        self.events.emit_new(EventType.BET_PLACED, amount=amount)
        self.place_bet()  # Trigger state transition

        return self._deal_initial_cards()

    def _deal_initial_cards(self) -> bool:
        """Deal the initial cards."""
        if self.shoe.needs_shuffle:
            self.shoe.shuffle()
            self.events.emit_new(EventType.SHOE_SHUFFLED)

        player_hand = self.player.current_hand
        if player_hand is None:
            return False

        # Deal: player, dealer, player, dealer (face down)
        self._deal_card_to_hand(player_hand)
        self._deal_card_to_hand(self.dealer_hand)
        self._deal_card_to_hand(player_hand)
        self._deal_card_to_hand(self.dealer_hand, face_up=False)

        self.events.emit_new(EventType.ROUND_STARTED)

        # Check for blackjacks
        player_bj = player_hand.is_blackjack
        dealer_showing_ace = (
            len(self.dealer_hand.cards) > 0 and self.dealer_hand.cards[0].is_ace
        )

        if player_bj:
            self.events.emit_new(EventType.PLAYER_BLACKJACK)

        # Offer insurance if dealer shows Ace (before checking for dealer blackjack)
        if dealer_showing_ace and not player_bj:
            self.events.emit_new(EventType.INSURANCE_OFFERED)
            self.offer_insurance()
            return True  # Wait for insurance decision

        # Check dealer blackjack (peek if allowed)
        if self.rules.dealer_peeks and self._check_dealer_blackjack():
            self.events.emit_new(EventType.DEALER_BLACKJACK)
            self.dealer_blackjack()
            return self._resolve_round()

        if player_bj:
            # Player has blackjack, dealer doesn't
            self.deal_cards()  # Move to player turn
            self.player_done()  # Skip to dealer
            self.dealer_plays()  # Skip dealer play
            return self._resolve_round()

        self.deal_cards()  # Move to player turn
        return True

    def _deal_card_to_hand(self, hand: Hand, face_up: bool = True) -> Card:
        """Deal a card to a hand."""
        card = self.shoe.draw()
        hand.add_card(card)
        self.events.emit_new(
            EventType.CARD_DEALT,
            card=str(card) if face_up else "??",
            hand="dealer" if hand is self.dealer_hand else "player",
            hand_value=hand.value if face_up or hand is not self.dealer_hand else None,
        )
        return card

    def _check_dealer_blackjack(self) -> bool:
        """Check if dealer has blackjack (without revealing)."""
        return self.dealer_hand.is_blackjack

    def hit(self) -> bool:
        """Player hits (takes another card)."""
        if self.state != GameState.PLAYER_TURN:
            return False

        hand = self.player.current_hand
        if hand is None:
            return False

        self._deal_card_to_hand(hand)
        self.events.emit_new(EventType.PLAYER_HIT, hand_value=hand.value)

        if hand.is_busted:
            self.events.emit_new(EventType.PLAYER_BUSTS, hand_index=self.player.current_hand_index)
            return self._advance_to_next_hand()

        self.player_action()  # Stay in player turn
        return True

    def stand(self) -> bool:
        """Player stands (keeps current hand)."""
        if self.state != GameState.PLAYER_TURN:
            return False

        self.events.emit_new(
            EventType.PLAYER_STAND,
            hand_value=self.player.current_hand.value if self.player.current_hand else 0,
        )
        return self._advance_to_next_hand()

    def double_down(self) -> bool:
        """Player doubles down."""
        if self.state != GameState.PLAYER_TURN:
            return False

        hand = self.player.current_hand
        if hand is None or not hand.can_double:
            self.events.emit_new(EventType.INVALID_ACTION, message="Cannot double")
            return False

        # Check if doubling is allowed for this total
        if self.rules.double_on == "9-11" and hand.value not in (9, 10, 11):
            self.events.emit_new(EventType.INVALID_ACTION, message="Can only double on 9-11")
            return False
        if self.rules.double_on == "10-11" and hand.value not in (10, 11):
            self.events.emit_new(EventType.INVALID_ACTION, message="Can only double on 10-11")
            return False

        if Decimal(str(hand.bet)) > self.player.bankroll:
            self.events.emit_new(EventType.INSUFFICIENT_FUNDS)
            return False

        hand.bet *= 2
        hand.is_doubled = True

        self._deal_card_to_hand(hand)
        self.events.emit_new(
            EventType.PLAYER_DOUBLE,
            hand_value=hand.value,
            new_bet=hand.bet,
        )

        if hand.is_busted:
            self.events.emit_new(EventType.PLAYER_BUSTS, hand_index=self.player.current_hand_index)

        return self._advance_to_next_hand()

    def split(self) -> bool:
        """Player splits a pair."""
        if self.state != GameState.PLAYER_TURN:
            return False

        hand = self.player.current_hand
        if hand is None or not hand.is_pair:
            self.events.emit_new(EventType.INVALID_ACTION, message="Cannot split")
            return False

        if len(self.player.hands) >= self.rules.max_splits:
            self.events.emit_new(EventType.INVALID_ACTION, message="Max splits reached")
            return False

        if Decimal(str(hand.bet)) > self.player.bankroll:
            self.events.emit_new(EventType.INSUFFICIENT_FUNDS)
            return False

        # Create new hand with second card
        second_card = hand.cards.pop()
        new_hand = self.player.add_hand(bet=hand.bet)
        new_hand.add_card(second_card)
        new_hand.is_split_hand = True
        hand.is_split_hand = True

        # Deal one card to each hand
        self._deal_card_to_hand(hand)
        self._deal_card_to_hand(new_hand)

        self.events.emit_new(
            EventType.PLAYER_SPLIT,
            hand1_value=hand.value,
            hand2_value=new_hand.value,
        )

        # Check if split aces get only one card
        if hand.cards[0].is_ace and not self.rules.hit_split_aces:
            return self._advance_to_next_hand()

        self.player_action()
        return True

    def surrender(self) -> bool:
        """Player surrenders."""
        if self.state != GameState.PLAYER_TURN:
            return False

        if self.rules.surrender == "none":
            self.events.emit_new(EventType.INVALID_ACTION, message="Surrender not allowed")
            return False

        hand = self.player.current_hand
        if hand is None:
            return False

        # Late surrender only allowed as first action
        if self.rules.surrender == "late" and len(hand.cards) > 2:
            self.events.emit_new(EventType.INVALID_ACTION, message="Can only surrender on first action")
            return False

        hand.is_surrendered = True
        self.events.emit_new(EventType.PLAYER_SURRENDER)

        return self._advance_to_next_hand()

    def take_insurance(self, amount: int | None = None) -> bool:
        """
        Player takes insurance bet.

        Args:
            amount: Insurance bet amount (defaults to half the main bet)

        Returns:
            True if insurance was taken
        """
        if self.state != GameState.OFFERING_INSURANCE:
            return False

        hand = self.player.current_hand
        if hand is None:
            return False

        # Insurance bet is up to half the original bet
        max_insurance = hand.bet // 2
        insurance_amount = amount if amount is not None else max_insurance

        if insurance_amount > max_insurance:
            self.events.emit_new(
                EventType.INVALID_ACTION,
                message=f"Insurance bet cannot exceed ${max_insurance}",
            )
            return False

        if Decimal(str(insurance_amount)) > self.player.bankroll:
            self.events.emit_new(EventType.INSUFFICIENT_FUNDS)
            return False

        self.player.insurance_bet = Decimal(str(insurance_amount))
        self.events.emit_new(
            EventType.INSURANCE_TAKEN,
            amount=insurance_amount,
        )

        return self._complete_insurance_decision()

    def decline_insurance(self) -> bool:
        """Player declines insurance."""
        if self.state != GameState.OFFERING_INSURANCE:
            return False

        self.player.insurance_bet = Decimal("0")
        self.events.emit_new(EventType.INSURANCE_DECLINED)

        return self._complete_insurance_decision()

    def _complete_insurance_decision(self) -> bool:
        """Complete the insurance decision and continue with the hand."""
        # Check dealer blackjack after insurance decision
        if self.rules.dealer_peeks and self._check_dealer_blackjack():
            self.events.emit_new(EventType.DEALER_BLACKJACK)
            # Insurance payout is handled in _resolve_round
            self.dealer_blackjack_after_insurance()
            return self._resolve_round()

        # No dealer blackjack, continue to player turn
        self.insurance_decision()
        return True

    @property
    def can_insure(self) -> bool:
        """Check if insurance is available."""
        if self.state != GameState.OFFERING_INSURANCE:
            return False
        hand = self.player.current_hand
        if hand is None:
            return False
        max_insurance = hand.bet // 2
        return Decimal(str(max_insurance)) <= self.player.bankroll

    def _advance_to_next_hand(self) -> bool:
        """Move to the next hand or dealer turn."""
        self.player.current_hand_index += 1

        if self.player.current_hand_index >= len(self.player.hands):
            # All hands played
            all_busted = all(h.is_busted or h.is_surrendered for h in self.player.hands)
            if all_busted:
                self.player_busts_all()
                return self._resolve_round()

            self.player_done()
            return self._play_dealer()

        self.player_action()
        return True

    def _play_dealer(self) -> bool:
        """Dealer plays their hand."""
        # Reveal hole card
        if len(self.dealer_hand.cards) >= 2:
            self.events.emit_new(
                EventType.DEALER_REVEALS,
                card=str(self.dealer_hand.cards[1]),
                hand_value=self.dealer_hand.value,
            )

        # Dealer hits until 17+ (or soft 17 if H17 rules)
        while self._dealer_should_hit():
            self._deal_card_to_hand(self.dealer_hand)
            self.events.emit_new(EventType.DEALER_HITS, hand_value=self.dealer_hand.value)

        if self.dealer_hand.is_busted:
            self.events.emit_new(EventType.DEALER_BUSTS)
        else:
            self.events.emit_new(EventType.DEALER_STANDS, hand_value=self.dealer_hand.value)

        self.dealer_plays()
        return self._resolve_round()

    def _dealer_should_hit(self) -> bool:
        """Determine if dealer should hit."""
        value = self.dealer_hand.value
        if value < 17:
            return True
        if value == 17 and self.dealer_hand.is_soft and self.rules.dealer_hits_soft_17:
            return True
        return False

    def _resolve_round(self) -> bool:
        """Resolve the round and pay out bets."""
        total_result = Decimal("0")

        # Handle insurance payout first
        if self.player.insurance_bet > 0:
            if self.dealer_hand.is_blackjack:
                # Insurance wins: pays 2:1
                insurance_payout = self.player.insurance_bet * 2
                total_result += insurance_payout
                self.events.emit_new(
                    EventType.INSURANCE_WINS,
                    amount=float(insurance_payout),
                )
            else:
                # Insurance loses
                total_result -= self.player.insurance_bet
                self.events.emit_new(
                    EventType.INSURANCE_LOSES,
                    amount=float(self.player.insurance_bet),
                )

        for i, hand in enumerate(self.player.hands):
            if hand.is_surrendered:
                # Lose half bet on surrender
                result = Decimal(str(-hand.bet)) / 2
            elif hand.is_busted:
                result = Decimal(str(-hand.bet))
            else:
                outcome = evaluate_hands(hand, self.dealer_hand)

                if outcome == 1:  # Win
                    if hand.is_blackjack:
                        result = Decimal(str(hand.bet)) * Decimal(str(self.rules.blackjack_payout))
                    else:
                        result = Decimal(str(hand.bet))
                    self.events.emit_new(EventType.PLAYER_WINS, hand_index=i, amount=float(result))
                elif outcome == -1:  # Lose
                    result = Decimal(str(-hand.bet))
                    self.events.emit_new(EventType.PLAYER_LOSES, hand_index=i, amount=float(-result))
                else:  # Push
                    result = Decimal("0")
                    self.events.emit_new(EventType.PUSH, hand_index=i)

            total_result += result

        self.player.bankroll += total_result
        self.events.emit_new(
            EventType.ROUND_ENDED,
            result=float(total_result),
            bankroll=float(self.player.bankroll),
        )

        self.resolve()

        # Check for game over
        if self.player.bankroll < Decimal(str(self.rules.min_bet)):
            self.events.emit_new(EventType.GAME_ENDED, reason="bankrupt")
            self.end_game()
            return True

        self.new_round()
        return True

    def start_new_round(self) -> bool:
        """Start a new round (alias for returning to betting state)."""
        if self.state == GameState.ROUND_COMPLETE:
            self.new_round()
            return True
        return False

    @property
    def can_hit(self) -> bool:
        """Check if hitting is allowed."""
        if self.state != GameState.PLAYER_TURN:
            return False
        hand = self.player.current_hand
        return hand is not None and not hand.is_busted

    @property
    def can_stand(self) -> bool:
        """Check if standing is allowed."""
        return self.state == GameState.PLAYER_TURN

    @property
    def can_double(self) -> bool:
        """Check if doubling is allowed."""
        if self.state != GameState.PLAYER_TURN:
            return False
        hand = self.player.current_hand
        if hand is None or not hand.can_double:
            return False
        if hand.is_split_hand and not self.rules.double_after_split:
            return False
        return Decimal(str(hand.bet)) <= self.player.bankroll

    @property
    def can_split(self) -> bool:
        """Check if splitting is allowed."""
        if self.state != GameState.PLAYER_TURN:
            return False
        hand = self.player.current_hand
        if hand is None or not hand.is_pair:
            return False
        if len(self.player.hands) >= self.rules.max_splits:
            return False
        # Check resplit aces
        if hand.cards[0].is_ace and hand.is_split_hand and not self.rules.resplit_aces:
            return False
        return Decimal(str(hand.bet)) <= self.player.bankroll

    @property
    def can_surrender(self) -> bool:
        """Check if surrender is allowed."""
        if self.state != GameState.PLAYER_TURN:
            return False
        if self.rules.surrender == "none":
            return False
        hand = self.player.current_hand
        return hand is not None and len(hand.cards) == 2 and not hand.is_split_hand
