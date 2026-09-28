"""WebSocket protocol v2 tests: legacy fields intact, new capabilities work."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def recv_until(ws, msg_type, limit=60):
    """Receive messages until one of the given type arrives."""
    for _ in range(limit):
        message = ws.receive_json()
        if message.get("type") == msg_type:
            return message
    pytest.fail(f"no {msg_type} message within {limit} messages")


def recv_until_state(ws, predicate, limit=60):
    """Receive until a message carrying state matches the predicate."""
    for _ in range(limit):
        message = ws.receive_json()
        state = message.get("state")
        if state and predicate(state):
            return message
    pytest.fail("no matching state within limit")


LEGACY_KEYS = (
    "state", "player_hands", "dealer_hand", "dealer_showing", "bankroll",
    "can_hit", "can_stand", "can_double", "can_split", "can_surrender",
    "can_insure", "insurance_bet", "shoe_cards_remaining",
    "shoe_decks_remaining",
)


class TestProtocolV2:
    def test_initial_state_has_legacy_and_v2_fields(self, client):
        with client.websocket_connect("/ws/game/test-v2-init") as ws:
            message = ws.receive_json()
            assert message["type"] == "state_update"
            state = message["state"]
            for key in LEGACY_KEYS:
                assert key in state, f"legacy key {key} missing"
            assert state["v"] == 2
            assert "count" in state  # default visibility: always
            assert "quant" in state
            assert "rules" in state

    def test_bet_and_action_produce_decision_results(self, client):
        with client.websocket_connect("/ws/game/test-v2-grade") as ws:
            ws.receive_json()  # initial state

            ws.send_json({"type": "bet", "amount": 25})
            bet_grade = recv_until(ws, "decision_result")
            assert bet_grade["grade"]["kind"] == "bet"

            # Wait until the deal settles into a decision point
            message = recv_until_state(
                ws,
                lambda s: s["state"] in (
                    "PLAYER_TURN", "OFFERING_INSURANCE", "WAITING_FOR_BET",
                    "ROUND_COMPLETE",
                ),
            )
            state = message["state"]

            if state["state"] == "OFFERING_INSURANCE":
                ws.send_json({"type": "insurance", "take": False})
                grade = recv_until(ws, "decision_result")
                assert grade["grade"]["kind"] == "insurance"
                message = recv_until_state(
                    ws,
                    lambda s: s["state"] in (
                        "PLAYER_TURN", "WAITING_FOR_BET", "ROUND_COMPLETE",
                    ),
                )
                state = message["state"]

            if state["state"] == "PLAYER_TURN":
                ws.send_json({"type": "action", "action": "stand"})
                grade = recv_until(ws, "decision_result")
                g = grade["grade"]
                assert g["kind"] == "action"
                assert g["action"] == "stand"
                assert g["correct_action"] in (
                    "hit", "stand", "double", "split", "surrender",
                )
                assert isinstance(g["is_correct"], bool)
                assert "dealer_bust_pct" in g["why"]

    def test_bet_limits_follow_rules(self, client):
        with client.websocket_connect("/ws/game/test-v2-limits") as ws:
            ws.receive_json()
            ws.send_json({"type": "bet", "amount": 5})
            message = ws.receive_json()
            assert message["type"] == "error"
            assert "$10" in message["message"]

    def test_reveal_count_message(self, client):
        with client.websocket_connect("/ws/game/test-v2-reveal") as ws:
            ws.receive_json()
            ws.send_json({"type": "reveal_count"})
            message = recv_until(ws, "count_reveal")
            assert "running" in message["count"]
            assert "player_edge_pct" in message["quant"]

    def test_count_checkin(self, client):
        with client.websocket_connect("/ws/game/test-v2-checkin") as ws:
            ws.receive_json()
            ws.send_json({"type": "count_checkin", "running_count": 0})
            message = recv_until(ws, "count_checkin_result")
            assert message["correct"] is True  # fresh shoe: count is 0

    def test_configure_visibility_hides_count(self, client):
        with client.websocket_connect("/ws/game/test-v2-visibility") as ws:
            ws.receive_json()
            ws.send_json({"type": "configure", "visibility": "hidden"})
            message = recv_until(ws, "state_update")
            assert "count" not in message["state"]
            assert message["state"]["visibility"] == "hidden"

    def test_configure_rules_preset_rebuilds_game(self, client):
        with client.websocket_connect("/ws/game/test-v2-preset") as ws:
            ws.receive_json()
            ws.send_json({"type": "configure", "rules_preset": "single_deck"})
            message = recv_until(ws, "state_update")
            assert message["state"]["rules"]["num_decks"] == 1

    def test_configure_counting_system(self, client):
        with client.websocket_connect("/ws/game/test-v2-system") as ws:
            ws.receive_json()
            ws.send_json({"type": "configure", "counting_system": "ko"})
            message = recv_until(ws, "state_update")
            count = message["state"]["count"]
            assert count["system"] == "ko"
            assert count["balanced"] is False
            assert count["running"] == -20  # KO IRC for 6 decks
            assert count["true"] is None

    def test_round_auto_records_performance(self, client):
        session_id = "test-v2-autorecord"
        with client.websocket_connect(f"/ws/game/{session_id}") as ws:
            ws.receive_json()
            ws.send_json({"type": "bet", "amount": 10})

            message = recv_until_state(
                ws,
                lambda s: s["state"] in (
                    "PLAYER_TURN", "OFFERING_INSURANCE", "WAITING_FOR_BET",
                    "ROUND_COMPLETE",
                ),
            )
            state = message["state"]
            if state["state"] == "OFFERING_INSURANCE":
                ws.send_json({"type": "insurance", "take": False})
                message = recv_until_state(
                    ws,
                    lambda s: s["state"] in (
                        "PLAYER_TURN", "WAITING_FOR_BET", "ROUND_COMPLETE",
                    ),
                )
                state = message["state"]
            if state["state"] == "PLAYER_TURN":
                ws.send_json({"type": "action", "action": "stand"})
                recv_until(ws, "event")

            # Drain until the round has ended
            recv_until_state(
                ws,
                lambda s: s["state"] in ("WAITING_FOR_BET", "ROUND_COMPLETE", "GAME_OVER"),
            )

        response = client.get(f"/api/stats/performance/{session_id}")
        assert response.status_code == 200
        stats = response.json()
        assert stats["hands_played"] >= 1
