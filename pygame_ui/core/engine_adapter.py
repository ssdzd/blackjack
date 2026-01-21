"""Adapter connecting the core blackjack engine to the PyGame UI."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Optional, TYPE_CHECKING

from core.cards import Card, Rank, Suit
from core.game.engine import BlackjackGame
from core.game.events import EventType, GameEvent
from core.game.state import GameState
from core.counting.hilo import HiLoSystem
from core.strategy.rules import RuleSet
from pygame_ui.core.game_settings import get_settings_manager

if TYPE_CHECKING:
    from pygame_ui.components.card import CardSprite


# Map core Suit to pygame_ui suit names
SUIT_MAP = {
    Suit.HEARTS: "hearts",
    Suit.DIAMONDS: "diamonds",
    Suit.CLUBS: "clubs",
    Suit.SPADES: "spades",
}

# Map core Rank to pygame_ui value strings
RANK_MAP = {
    Rank.TWO: "2",
    Rank.THREE: "3",
    Rank.FOUR: "4",
    Rank.FIVE: "5",
    Rank.SIX: "6",
    Rank.SEVEN: "7",
    Rank.EIGHT: "8",
    Rank.NINE: "9",
    Rank.TEN: "10",
    Rank.JACK: "J",
    Rank.QUEEN: "Q",
    Rank.KING: "K",
    Rank.ACE: "A",
}


@dataclass
class UICardInfo:
    """Card information for the UI layer."""

    value: str  # "A", "2", "K", etc.
    suit: str   # "hearts", "diamonds", "clubs", "spades"
    face_up: bool = True

    @classmethod
    def from_core_card(cls, card: Card, face_up: bool = True) -> "UICardInfo":
        """Create UICardInfo from a core Card."""
        return cls(
            value=RANK_MAP[card.rank],
            suit=SUIT_MAP[card.suit],
            face_up=face_up,
        )


@dataclass
class GameSnapshot:
    """Snapshot of game state for UI rendering."""

    state: GameState
    player_hands: list[list[UICardInfo]]
    dealer_hand: list[UICardInfo]
    dealer_hole_card_hidden: bool
    player_hand_values: list[int]
    dealer_hand_value: int
    current_hand_index: int
    bankroll: float
    current_bet: int
    running_count: int
    true_count: float
    cards_remaining: int
    decks_remaining: float
    can_hit: bool
    can_stand: bool
    can_double: bool
    can_split: bool
    can_surrender: bool
    can_insure: bool
    offering_insurance: bool


class EngineAdapter:
    """Adapter between the core BlackjackGame and PyGame UI.

    Subscribes to engine events and translates them to UI callbacks.
    Provides a clean interface for UI code to interact with the engine.
    """

    def __init__(
        self,
        rules: RuleSet = None,
        initial_bankroll: float = 1000,
    ):
        """Initialize the adapter.

        Args:
            rules: Game rules (defaults to settings or standard 6-deck)
            initial_bankroll: Starting bankroll
        """
        # Use rules from settings if not provided
        if rules is None:
            rules = self._rules_from_settings()
        self.rules = rules
        self._initial_bankroll = Decimal(str(initial_bankroll))

        # Core engine
        self.game: Optional[BlackjackGame] = None

        # Counting system
        self.counter = HiLoSystem()

        # UI callbacks
        self._on_card_dealt: Optional[Callable[[str, UICardInfo, int], None]] = None
        self._on_hand_result: Optional[Callable[[str, int, float], None]] = None
        self._on_dealer_reveal: Optional[Callable[[UICardInfo], None]] = None
        self._on_shuffle: Optional[Callable[[], None]] = None
        self._on_state_change: Optional[Callable[[GameState], None]] = None
        self._on_invalid_action: Optional[Callable[[str], None]] = None
        self._on_count_update: Optional[Callable[[int, float], None]] = None
        self._on_insurance_offered: Optional[Callable[[], None]] = None

        # Initialize engine
        self._init_game()

    def _rules_from_settings(self) -> RuleSet:
        """Create RuleSet from game settings."""
        settings = get_settings_manager()
        table_rules = settings.table_rules
        return RuleSet(
            num_decks=table_rules.num_decks,
            dealer_hits_soft_17=table_rules.dealer_hits_soft_17,
            blackjack_payout=table_rules.blackjack_payout,
            double_after_split=table_rules.double_after_split,
            double_on=table_rules.double_on,
            resplit_aces=table_rules.resplit_aces,
            max_splits=table_rules.max_splits,
            surrender=table_rules.surrender,
        )

    def _get_penetration(self) -> float:
        """Get penetration from settings."""
        return get_settings_manager().table_rules.penetration

    def _init_game(self) -> None:
        """Initialize a new game engine."""
        penetration = self._get_penetration()
        self.game = BlackjackGame(
            rules=self.rules,
            num_decks=self.rules.num_decks,
            penetration=penetration,
            initial_bankroll=self._initial_bankroll,
        )
        self.counter.reset()

        # Subscribe to all events
        self.game.subscribe(self._handle_event)

    def reload_rules(self) -> None:
        """Reload rules from settings (e.g. when returning from settings)."""
        self.rules = self._rules_from_settings()

    def _handle_event(self, event: GameEvent) -> None:
        """Handle events from the core engine."""
        etype = event.event_type
        data = event.data

        if etype == EventType.CARD_DEALT:
            self._handle_card_dealt(data)
        elif etype == EventType.DEALER_REVEALS:
            self._handle_dealer_reveal(data)
        elif etype == EventType.SHOE_SHUFFLED:
            self.counter.reset()
            if self._on_shuffle:
                self._on_shuffle()
        elif etype == EventType.PLAYER_WINS:
            if self._on_hand_result:
                self._on_hand_result("win", data.get("hand_index", 0), data.get("amount", 0))
        elif etype == EventType.PLAYER_LOSES:
            if self._on_hand_result:
                self._on_hand_result("lose", data.get("hand_index", 0), data.get("amount", 0))
        elif etype == EventType.PUSH:
            if self._on_hand_result:
                self._on_hand_result("push", data.get("hand_index", 0), 0)
        elif etype == EventType.PLAYER_BLACKJACK:
            if self._on_hand_result:
                self._on_hand_result("blackjack", 0, 0)
        elif etype == EventType.PLAYER_BUSTS:
            if self._on_hand_result:
                self._on_hand_result("bust", data.get("hand_index", 0), 0)
        elif etype == EventType.DEALER_BUSTS:
            pass  # Will be handled by win events
        elif etype == EventType.INVALID_ACTION:
            if self._on_invalid_action:
                self._on_invalid_action(data.get("message", "Invalid action"))
        elif etype == EventType.INSURANCE_OFFERED:
            if self._on_insurance_offered:
                self._on_insurance_offered()

    def _handle_card_dealt(self, data: dict) -> None:
        """Handle a card dealt event."""
        card_str = data.get("card", "??")
        hand_type = data.get("hand", "player")  # "player" or "dealer"
        face_up = card_str != "??"

        if face_up and card_str:
            # Parse the card string to update count
            try:
                card = Card.from_string(card_str)
                tag = self.counter.count_card(card)

                # Notify count update
                if self._on_count_update:
                    self._on_count_update(
                        int(self.counter.running_count),
                        self.counter.true_count(self.game.shoe.decks_remaining),
                    )

                # Create UI card info
                ui_card = UICardInfo.from_core_card(card, face_up=True)
            except (ValueError, KeyError):
                # Fallback for unknown card format
                ui_card = UICardInfo(value="?", suit="spades", face_up=False)
        else:
            # Face-down card
            ui_card = UICardInfo(value="?", suit="spades", face_up=False)

        if self._on_card_dealt:
            hand_index = 0
            if hand_type == "player" and self.game:
                hand_index = self.game.player.current_hand_index
            self._on_card_dealt(hand_type, ui_card, hand_index)

    def _handle_dealer_reveal(self, data: dict) -> None:
        """Handle dealer hole card reveal."""
        card_str = data.get("card", "")
        if card_str:
            try:
                card = Card.from_string(card_str)
                self.counter.count_card(card)

                if self._on_count_update:
                    self._on_count_update(
                        int(self.counter.running_count),
                        self.counter.true_count(self.game.shoe.decks_remaining),
                    )

                ui_card = UICardInfo.from_core_card(card, face_up=True)
                if self._on_dealer_reveal:
                    self._on_dealer_reveal(ui_card)
            except (ValueError, KeyError):
                pass

    # Public API for UI

    def set_callbacks(
        self,
        on_card_dealt: Callable[[str, UICardInfo, int], None] = None,
        on_hand_result: Callable[[str, int, float], None] = None,
        on_dealer_reveal: Callable[[UICardInfo], None] = None,
        on_shuffle: Callable[[], None] = None,
        on_state_change: Callable[[GameState], None] = None,
        on_invalid_action: Callable[[str], None] = None,
        on_count_update: Callable[[int, float], None] = None,
        on_insurance_offered: Callable[[], None] = None,
    ) -> None:
        """Set UI callback functions.

        Args:
            on_card_dealt: Called when card dealt (hand_type, card_info, hand_index)
            on_hand_result: Called on hand result (result, hand_index, amount)
            on_dealer_reveal: Called when dealer reveals hole card
            on_shuffle: Called when deck is shuffled
            on_state_change: Called when game state changes
            on_invalid_action: Called on invalid action (message)
            on_count_update: Called when count changes (running, true)
            on_insurance_offered: Called when insurance is offered
        """
        self._on_card_dealt = on_card_dealt
        self._on_hand_result = on_hand_result
        self._on_dealer_reveal = on_dealer_reveal
        self._on_shuffle = on_shuffle
        self._on_state_change = on_state_change
        self._on_invalid_action = on_invalid_action
        self._on_count_update = on_count_update
        self._on_insurance_offered = on_insurance_offered

    @property
    def state(self) -> GameState:
        """Get current game state."""
        return self.game.state if self.game else GameState.WAITING_FOR_BET

    @property
    def bankroll(self) -> float:
        """Get current bankroll."""
        return float(self.game.player.bankroll) if self.game else 0

    @property
    def running_count(self) -> int:
        """Get current running count."""
        return int(self.counter.running_count)

    @property
    def true_count(self) -> float:
        """Get current true count."""
        if self.game:
            return self.counter.true_count(self.game.shoe.decks_remaining)
        return 0.0

    @property
    def cards_remaining(self) -> int:
        """Get cards remaining in shoe."""
        return self.game.shoe.cards_remaining if self.game else 0

    @property
    def decks_remaining(self) -> float:
        """Get decks remaining in shoe."""
        return self.game.shoe.decks_remaining if self.game else 0

    def get_snapshot(self) -> GameSnapshot:
        """Get a snapshot of the current game state."""
        if not self.game:
            return GameSnapshot(
                state=GameState.WAITING_FOR_BET,
                player_hands=[],
                dealer_hand=[],
                dealer_hole_card_hidden=True,
                player_hand_values=[],
                dealer_hand_value=0,
                current_hand_index=0,
                bankroll=float(self._initial_bankroll),
                current_bet=0,
                running_count=0,
                true_count=0.0,
                cards_remaining=0,
                decks_remaining=0,
                can_hit=False,
                can_stand=False,
                can_double=False,
                can_split=False,
                can_surrender=False,
                can_insure=False,
                offering_insurance=False,
            )

        # Convert player hands
        player_hands = []
        player_values = []
        for hand in self.game.player.hands:
            cards = [UICardInfo.from_core_card(c) for c in hand.cards]
            player_hands.append(cards)
            player_values.append(hand.value)

        # Convert dealer hand
        dealer_cards = []
        hole_hidden = self.game.state in (GameState.PLAYER_TURN, GameState.DEALING, GameState.OFFERING_INSURANCE)
        for i, card in enumerate(self.game.dealer_hand.cards):
            face_up = not (i == 1 and hole_hidden)
            dealer_cards.append(UICardInfo.from_core_card(card, face_up=face_up))

        current_bet = 0
        if self.game.player.current_hand:
            current_bet = self.game.player.current_hand.bet

        return GameSnapshot(
            state=self.game.state,
            player_hands=player_hands,
            dealer_hand=dealer_cards,
            dealer_hole_card_hidden=hole_hidden,
            player_hand_values=player_values,
            dealer_hand_value=self.game.dealer_hand.value,
            current_hand_index=self.game.player.current_hand_index,
            bankroll=float(self.game.player.bankroll),
            current_bet=current_bet,
            running_count=self.running_count,
            true_count=self.true_count,
            cards_remaining=self.cards_remaining,
            decks_remaining=self.decks_remaining,
            can_hit=self.game.can_hit,
            can_stand=self.game.can_stand,
            can_double=self.game.can_double,
            can_split=self.game.can_split,
            can_surrender=self.game.can_surrender,
            can_insure=self.game.can_insure,
            offering_insurance=self.game.state == GameState.OFFERING_INSURANCE,
        )

    # Game actions

    def place_bet(self, amount: int) -> bool:
        """Place a bet to start a new round."""
        if not self.game:
            return False
        return self.game.bet(amount)

    def hit(self) -> bool:
        """Player hits."""
        if not self.game:
            return False
        return self.game.hit()

    def stand(self) -> bool:
        """Player stands."""
        if not self.game:
            return False
        return self.game.stand()

    def double_down(self) -> bool:
        """Player doubles down."""
        if not self.game:
            return False
        return self.game.double_down()

    def split(self) -> bool:
        """Player splits."""
        if not self.game:
            return False
        return self.game.split()

    def surrender(self) -> bool:
        """Player surrenders."""
        if not self.game:
            return False
        return self.game.surrender()

    def take_insurance(self) -> bool:
        """Player takes insurance."""
        if not self.game:
            return False
        return self.game.take_insurance()

    def decline_insurance(self) -> bool:
        """Player declines insurance."""
        if not self.game:
            return False
        return self.game.decline_insurance()

    def new_game(self) -> None:
        """Start a completely new game."""
        self._init_game()

    def reset_count(self) -> None:
        """Reset the card count (for practice)."""
        self.counter.reset()
        if self._on_count_update:
            self._on_count_update(0, 0.0)
