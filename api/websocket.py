"""WebSocket connection management with game engine integration."""

import asyncio
from decimal import Decimal
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Any
import json

from core.game import BlackjackGame
from core.game.events import GameEvent, EventType
from core.strategy.rules import RuleSet

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections and game instances."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._games: dict[str, BlackjackGame] = {}
        self._event_queues: dict[str, asyncio.Queue] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept and register a new connection."""
        await websocket.accept()
        self._connections[session_id] = websocket
        self._event_queues[session_id] = asyncio.Queue()

    def disconnect(self, session_id: str) -> None:
        """Remove a connection."""
        self._connections.pop(session_id, None)
        self._event_queues.pop(session_id, None)
        # Keep the game for potential reconnection

    def get_or_create_game(self, session_id: str) -> BlackjackGame:
        """Get or create a game for the session."""
        if session_id not in self._games:
            game = BlackjackGame(
                rules=RuleSet(),
                initial_bankroll=Decimal("1000"),
            )
            self._games[session_id] = game
            # Subscribe to all game events
            game.subscribe(lambda event: self._queue_event(session_id, event))
        return self._games[session_id]

    def reset_game(self, session_id: str) -> BlackjackGame:
        """Reset the game for a session."""
        game = BlackjackGame(
            rules=RuleSet(),
            initial_bankroll=Decimal("1000"),
        )
        self._games[session_id] = game
        game.subscribe(lambda event: self._queue_event(session_id, event))
        return game

    def _queue_event(self, session_id: str, event: GameEvent) -> None:
        """Queue an event for async delivery."""
        if session_id in self._event_queues:
            try:
                self._event_queues[session_id].put_nowait(event)
            except asyncio.QueueFull:
                pass  # Drop events if queue is full

    async def get_event(self, session_id: str) -> GameEvent | None:
        """Get the next event from the queue."""
        if session_id in self._event_queues:
            try:
                return await asyncio.wait_for(
                    self._event_queues[session_id].get(),
                    timeout=0.1
                )
            except asyncio.TimeoutError:
                return None
        return None

    async def send_message(self, session_id: str, message: dict[str, Any]) -> None:
        """Send a message to a specific session."""
        if session_id in self._connections:
            try:
                await self._connections[session_id].send_json(message)
            except Exception:
                pass  # Connection may be closed

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connections."""
        for websocket in self._connections.values():
            try:
                await websocket.send_json(message)
            except Exception:
                pass

    @property
    def active_connections(self) -> int:
        """Return number of active connections."""
        return len(self._connections)


# Global connection manager
manager = ConnectionManager()


def _game_state_to_dict(game: BlackjackGame, hide_hole_card: bool = False) -> dict:
    """Convert game state to a dictionary for JSON serialization."""
    dealer_cards = []
    for i, card in enumerate(game.dealer_hand.cards):
        if hide_hole_card and i == 1:
            dealer_cards.append({"rank": "?", "suit": "?", "value": 0, "hidden": True})
        else:
            dealer_cards.append({
                "rank": str(card.rank),
                "suit": str(card.suit),
                "value": card.value,
                "hidden": False,
            })

    player_hands = []
    for hand in game.player.hands:
        player_hands.append({
            "cards": [
                {"rank": str(c.rank), "suit": str(c.suit), "value": c.value}
                for c in hand.cards
            ],
            "value": hand.value,
            "is_soft": hand.is_soft,
            "is_blackjack": hand.is_blackjack,
            "is_busted": hand.is_busted,
            "bet": hand.bet,
        })

    # Calculate dealer showing value
    dealer_showing = None
    if game.dealer_hand.cards and not hide_hole_card:
        dealer_showing = game.dealer_hand.value
    elif game.dealer_hand.cards:
        dealer_showing = game.dealer_hand.cards[0].value

    return {
        "state": game.state.name,
        "player_hands": player_hands,
        "current_hand_index": game.player.current_hand_index,
        "dealer_hand": {
            "cards": dealer_cards,
            "value": dealer_showing if not hide_hole_card else None,
        },
        "dealer_showing": dealer_showing,
        "bankroll": float(game.player.bankroll),
        "can_hit": game.can_hit,
        "can_stand": game.can_stand,
        "can_double": game.can_double,
        "can_split": game.can_split,
        "can_surrender": game.can_surrender,
        "shoe_cards_remaining": game.shoe.cards_remaining,
        "shoe_decks_remaining": round(game.shoe.cards_remaining / 52, 2),
    }


def _event_to_message(event: GameEvent, game: BlackjackGame) -> dict[str, Any]:
    """Convert a game event to a WebSocket message."""
    hide_hole = game.state.name == "PLAYER_TURN"

    base_message = {
        "type": "event",
        "event_type": event.event_type.name,
        "data": event.data,
        "state": _game_state_to_dict(game, hide_hole_card=hide_hole),
    }

    # Add specific fields based on event type
    if event.event_type == EventType.ROUND_ENDED:
        base_message["round_result"] = {
            "net_result": event.data.get("result", 0),
            "bankroll": event.data.get("bankroll", 0),
        }

    return base_message


@router.websocket("/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket endpoint for real-time game updates.

    Messages from client:
    - {"type": "bet", "amount": 100}
    - {"type": "action", "action": "hit"|"stand"|"double"|"split"|"surrender"}
    - {"type": "new_round"}
    - {"type": "reset_game"}
    - {"type": "get_state"}

    Messages to client:
    - {"type": "state_update", "state": {...}}
    - {"type": "event", "event_type": "...", "data": {...}, "state": {...}}
    - {"type": "error", "message": "..."}
    """
    await manager.connect(websocket, session_id)
    game = manager.get_or_create_game(session_id)

    # Send initial state
    hide_hole = game.state.name == "PLAYER_TURN"
    await manager.send_message(session_id, {
        "type": "state_update",
        "state": _game_state_to_dict(game, hide_hole_card=hide_hole),
    })

    async def process_events():
        """Process game events and send to client."""
        while True:
            event = await manager.get_event(session_id)
            if event:
                message = _event_to_message(event, game)
                await manager.send_message(session_id, message)
            else:
                await asyncio.sleep(0.01)

    # Start event processor
    event_task = asyncio.create_task(process_events())

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "get_state":
                hide_hole = game.state.name == "PLAYER_TURN"
                await manager.send_message(session_id, {
                    "type": "state_update",
                    "state": _game_state_to_dict(game, hide_hole_card=hide_hole),
                })

            elif msg_type == "bet":
                amount = message.get("amount", 0)
                if amount < 10 or amount > 1000:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "Bet must be between $10 and $1000",
                    })
                    continue

                success = game.bet(int(amount))
                if not success:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "Cannot place bet in current state",
                    })

            elif msg_type == "action":
                action = message.get("action")
                actions = {
                    "hit": game.hit,
                    "stand": game.stand,
                    "double": game.double_down,
                    "split": game.split,
                    "surrender": game.surrender,
                }

                action_fn = actions.get(action)
                if action_fn is None:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": f"Unknown action: {action}",
                    })
                    continue

                success = action_fn()
                if not success:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": f"Cannot {action} now",
                    })

            elif msg_type == "new_round":
                # Game auto-transitions to WAITING_FOR_BET after ROUND_COMPLETE
                # Just send current state
                hide_hole = game.state.name == "PLAYER_TURN"
                await manager.send_message(session_id, {
                    "type": "state_update",
                    "state": _game_state_to_dict(game, hide_hole_card=hide_hole),
                })

            elif msg_type == "reset_game":
                game = manager.reset_game(session_id)
                await manager.send_message(session_id, {
                    "type": "state_update",
                    "state": _game_state_to_dict(game),
                })

            else:
                await manager.send_message(session_id, {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await manager.send_message(session_id, {
            "type": "error",
            "message": str(e),
        })
    finally:
        event_task.cancel()
        try:
            await event_task
        except asyncio.CancelledError:
            pass
        manager.disconnect(session_id)
