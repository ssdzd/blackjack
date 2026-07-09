"""WebSocket connection management with server-authoritative game sessions.

Protocol (v2 — strictly additive over v1):

Client -> server:
- {"type": "bet", "amount": 100}
- {"type": "action", "action": "hit"|"stand"|"double"|"split"|"surrender"}
- {"type": "insurance", "take": true|false, "amount"?: 25}
- {"type": "new_round"}
- {"type": "reset_game"}
- {"type": "get_state"}
- {"type": "configure", "counting_system"?, "visibility"?, "rules_preset"?}
- {"type": "reveal_count"}                     (on_request visibility)
- {"type": "count_checkin", "running_count": 3}

Server -> client:
- {"type": "state_update", "state": {...}}     state has v:2, count/quant/rules
- {"type": "event", "event_type", "data", "state", ["round_result"]}
- {"type": "decision_result", "grade": {...}}  graded action/insurance/bet
- {"type": "count_reveal", "count": {...}, "quant": {...}}
- {"type": "count_checkin_result", {...}}
- {"type": "error", "message": "..."}
"""

import asyncio
from decimal import Decimal
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Any
import json

from api.game_session import (
    RULE_PRESETS,
    TrainingGameSession,
    VISIBILITY_MODES,
    COUNTING_SYSTEMS,
)
from api.progression_store import progress
from api.routes.stats import record_stat_for_session
from core.game.events import GameEvent, EventType

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections and training sessions."""

    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._sessions: dict[str, TrainingGameSession] = {}
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
        # Keep the session for potential reconnection

    def get_or_create_session(self, session_id: str) -> TrainingGameSession:
        """Get or create a training session."""
        if session_id not in self._sessions:
            self._register_session(session_id, TrainingGameSession())
        return self._sessions[session_id]

    def reset_session(self, session_id: str, **kwargs: Any) -> TrainingGameSession:
        """Replace the session with a freshly configured one."""
        old = self._sessions.get(session_id)
        profile_id = None
        if old is not None:
            kwargs.setdefault("counting_system", old.counting_system_name)
            kwargs.setdefault("visibility", old.visibility)
            profile_id = old.profile_id
        self._register_session(session_id, TrainingGameSession(**kwargs))
        self._sessions[session_id].profile_id = profile_id
        return self._sessions[session_id]

    def _register_session(self, session_id: str, session: TrainingGameSession) -> None:
        self._sessions[session_id] = session
        # The session subscribed its own counter first; the queue handler
        # runs after it, so serialized states already include the count.
        session.game.subscribe(lambda event: self._queue_event(session_id, event))

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


def _event_to_message(event: GameEvent, session: TrainingGameSession) -> dict[str, Any]:
    """Convert a game event to a WebSocket message."""
    base_message = {
        "type": "event",
        "event_type": event.event_type.name,
        "data": event.data,
        "state": session.state_payload(),
    }

    if event.event_type == EventType.ROUND_ENDED:
        base_message["round_result"] = {
            "net_result": event.data.get("result", 0),
            "bankroll": event.data.get("bankroll", 0),
        }

    return base_message


async def _record_round(session_id: str, session: TrainingGameSession) -> None:
    """Persist a finished round into performance stats (server-side)."""
    info = session.last_round_result
    if not info:
        return
    result = info.get("result", 0) or 0
    if result > 0:
        stat_type = "hand_blackjack" if info.get("player_blackjack") else "hand_win"
    elif result < 0:
        stat_type = "hand_loss"
    else:
        stat_type = "hand_push"
    try:
        await record_stat_for_session(
            session_id,
            stat_type,
            value=abs(result),
            details={"bankroll": info.get("bankroll", 0)},
        )
    except Exception:
        pass  # Stats persistence must never break gameplay


async def _push_progression(
    session_id: str,
    session: TrainingGameSession,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Apply a progression event and push the delta if anything happened."""
    delta = await progress(session.profile_id, event_type, payload)
    if delta is None:
        return
    if (
        delta.xp_gained > 0
        or delta.badges_awarded
        or delta.node_changes
        or delta.level_up
    ):
        await manager.send_message(session_id, {
            "type": "progression",
            "delta": delta.model_dump(mode="json"),
        })


def _grade_to_event(grade) -> tuple[str, dict[str, Any]]:
    """Translate a DecisionGrade into a progression event."""
    if grade.kind == "action":
        return "decision", {
            "correct": grade.is_correct,
            "is_deviation": grade.is_deviation,
            "visibility": "always",  # overwritten by caller
            "fab4": bool(
                grade.is_deviation
                and grade.deviation
                and grade.deviation.get("deviation_action") == "surrender"
            ),
        }
    if grade.kind == "insurance":
        return "insurance", {
            "correct": grade.is_correct,
            "correct_action": grade.correct_action,
        }
    return "bet", {"in_band": grade.is_correct}


@router.websocket("/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for real-time game updates (see module docstring)."""
    await manager.connect(websocket, session_id)
    session = manager.get_or_create_session(session_id)

    # Send initial state
    await manager.send_message(session_id, {
        "type": "state_update",
        "state": session.state_payload(),
    })

    async def process_events():
        """Process game events and send to client."""
        while True:
            event = await manager.get_event(session_id)
            if event:
                message = _event_to_message(event, session)
                await manager.send_message(session_id, message)
                if event.event_type == EventType.ROUND_ENDED:
                    await _record_round(session_id, session)
                    await _push_progression(
                        session_id, session, "round",
                        {"result": (session.last_round_result or {}).get("result", 0)},
                    )
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
                await manager.send_message(session_id, {
                    "type": "state_update",
                    "state": session.state_payload(),
                })

            elif msg_type == "configure":
                if message.get("profile_id"):
                    session.profile_id = str(message["profile_id"])
                system = message.get("counting_system")
                visibility = message.get("visibility")
                preset = message.get("rules_preset")

                if preset is not None and preset in RULE_PRESETS:
                    session = manager.reset_session(
                        session_id,
                        rules=RULE_PRESETS[preset](),
                        counting_system=message.get(
                            "counting_system", session.counting_system_name
                        ),
                        visibility=message.get("visibility", session.visibility),
                    )
                else:
                    if system in COUNTING_SYSTEMS:
                        session.set_counting_system(system)
                    if visibility in VISIBILITY_MODES:
                        session.visibility = visibility

                await manager.send_message(session_id, {
                    "type": "state_update",
                    "state": session.state_payload(),
                })

            elif msg_type == "reveal_count":
                await manager.send_message(session_id, {
                    "type": "count_reveal",
                    "count": session.count_payload(),
                    "quant": session.quant_snapshot(),
                })

            elif msg_type == "count_checkin":
                answer = message.get("running_count")
                if answer is None:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "count_checkin requires running_count",
                    })
                    continue
                result = session.grade_count_checkin(float(answer))
                await manager.send_message(session_id, {
                    "type": "count_checkin_result",
                    **result,
                })
                await _push_progression(
                    session_id, session, "checkin",
                    {"exact": result["correct"], "close": result["close"]},
                )

            elif msg_type == "bet":
                amount = message.get("amount", 0)
                rules = session.rules
                if amount < rules.min_bet or amount > rules.max_bet:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": f"Bet must be between ${rules.min_bet} and ${rules.max_bet}",
                    })
                    continue

                grade = session.grade_bet(int(amount))
                success = session.game.bet(int(amount))
                if not success:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "Cannot place bet in current state",
                    })
                elif grade:
                    await manager.send_message(session_id, {
                        "type": "decision_result",
                        "grade": grade.to_dict(),
                    })
                    event_type, payload = _grade_to_event(grade)
                    await _push_progression(session_id, session, event_type, payload)

            elif msg_type == "action":
                action = message.get("action")
                game = session.game
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

                grade = session.grade_action(action)
                success = action_fn()
                if not success:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": f"Cannot {action} now",
                    })
                elif grade:
                    await manager.send_message(session_id, {
                        "type": "decision_result",
                        "grade": grade.to_dict(),
                    })
                    event_type, payload = _grade_to_event(grade)
                    payload["visibility"] = session.visibility
                    await _push_progression(session_id, session, event_type, payload)

            elif msg_type == "insurance":
                take_insurance = message.get("take", False)
                grade = session.grade_insurance(bool(take_insurance))
                if take_insurance:
                    amount = message.get("amount")  # Optional, defaults to half bet
                    success = session.game.take_insurance(amount)
                else:
                    success = session.game.decline_insurance()

                if not success:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "Cannot make insurance decision now",
                    })
                else:
                    await manager.send_message(session_id, {
                        "type": "decision_result",
                        "grade": grade.to_dict(),
                    })
                    event_type, payload = _grade_to_event(grade)
                    await _push_progression(session_id, session, event_type, payload)

            elif msg_type == "new_round":
                # Game auto-transitions to WAITING_FOR_BET after ROUND_COMPLETE
                await manager.send_message(session_id, {
                    "type": "state_update",
                    "state": session.state_payload(),
                })

            elif msg_type == "reset_game":
                session = manager.reset_session(session_id, rules=session.rules)
                await manager.send_message(session_id, {
                    "type": "state_update",
                    "state": session.state_payload(),
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
