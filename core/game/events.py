"""Game events for the event system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable


class EventType(Enum):
    """Types of game events."""

    # Game flow events
    GAME_STARTED = auto()
    GAME_ENDED = auto()
    ROUND_STARTED = auto()
    ROUND_ENDED = auto()

    # Betting events
    BET_PLACED = auto()
    BET_RESOLVED = auto()

    # Card events
    CARD_DEALT = auto()
    SHOE_SHUFFLED = auto()

    # Player action events
    PLAYER_HIT = auto()
    PLAYER_STAND = auto()
    PLAYER_DOUBLE = auto()
    PLAYER_SPLIT = auto()
    PLAYER_SURRENDER = auto()
    PLAYER_INSURANCE = auto()

    # Insurance events
    INSURANCE_OFFERED = auto()
    INSURANCE_TAKEN = auto()
    INSURANCE_DECLINED = auto()
    INSURANCE_WINS = auto()
    INSURANCE_LOSES = auto()

    # Dealer events
    DEALER_REVEALS = auto()
    DEALER_HITS = auto()
    DEALER_STANDS = auto()
    DEALER_BUSTS = auto()
    DEALER_BLACKJACK = auto()

    # Outcome events
    PLAYER_BLACKJACK = auto()
    PLAYER_BUSTS = auto()
    PLAYER_WINS = auto()
    PLAYER_LOSES = auto()
    PUSH = auto()

    # Error events
    INVALID_ACTION = auto()
    INSUFFICIENT_FUNDS = auto()


@dataclass(frozen=True)
class GameEvent:
    """
    Immutable game event.

    Events are the primary communication mechanism between the core engine
    and the presentation layer.
    """

    event_type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"{self.event_type.name}: {self.data}"


# Type alias for event handlers
EventHandler = Callable[[GameEvent], None]


class EventEmitter:
    """
    Simple event emitter for game events.

    Allows subscribing to specific event types or all events.
    """

    def __init__(self) -> None:
        """Initialize the event emitter."""
        self._handlers: dict[EventType | None, list[EventHandler]] = {}
        self._event_history: list[GameEvent] = []

    def subscribe(
        self,
        handler: EventHandler,
        event_type: EventType | None = None,
    ) -> None:
        """
        Subscribe to events.

        Args:
            handler: Function to call when event occurs
            event_type: Specific event type to subscribe to, or None for all events
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        handler: EventHandler,
        event_type: EventType | None = None,
    ) -> None:
        """
        Unsubscribe from events.

        Args:
            handler: Handler to remove
            event_type: Event type to unsubscribe from
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def emit(self, event: GameEvent) -> None:
        """
        Emit an event to all subscribers.

        Args:
            event: The event to emit
        """
        self._event_history.append(event)

        # Call type-specific handlers
        if event.event_type in self._handlers:
            for handler in self._handlers[event.event_type]:
                handler(event)

        # Call catch-all handlers
        if None in self._handlers:
            for handler in self._handlers[None]:
                handler(event)

    def emit_new(
        self,
        event_type: EventType,
        **data: Any,
    ) -> GameEvent:
        """
        Create and emit a new event.

        Args:
            event_type: Type of event
            **data: Event data

        Returns:
            The created event
        """
        event = GameEvent(event_type=event_type, data=data)
        self.emit(event)
        return event

    @property
    def history(self) -> list[GameEvent]:
        """Return the event history."""
        return self._event_history.copy()

    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()
