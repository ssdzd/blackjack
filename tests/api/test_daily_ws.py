"""End-to-end daily challenge over the WebSocket."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def drain_until(ws, predicate, limit=200):
    """Receive until predicate(message) is true; returns the message."""
    for _ in range(limit):
        message = ws.receive_json()
        if predicate(message):
            return message
    pytest.fail("condition not met within message limit")


class TestDailyFlow:
    def test_full_daily_run_completes_and_locks(self, client):
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]

        with client.websocket_connect("/ws/game/daily-e2e") as ws:
            ws.receive_json()  # initial state
            ws.send_json({"type": "configure", "profile_id": pid})
            drain_until(ws, lambda m: m["type"] == "state_update")

            ws.send_json({"type": "start_daily"})
            started = drain_until(ws, lambda m: m["type"] == "daily_started")
            assert started["rounds"] == 20
            drain_until(ws, lambda m: m["type"] == "state_update")

            completed = None
            rounds_seen = 0
            stood = False
            declined = False

            # First bet opens round 1; subsequent bets fire on daily_progress.
            # Check-in requests are answered the moment they arrive.
            ws.send_json({"type": "bet", "amount": 10})

            for _ in range(2000):  # generous message budget
                message = ws.receive_json()
                mtype = message.get("type")

                if mtype == "count_checkin_request":
                    ws.send_json({"type": "count_checkin", "running_count": 0})
                    continue
                if mtype == "daily_complete":
                    completed = message
                    break
                if mtype == "daily_progress":
                    rounds_seen = message["round"]
                    if rounds_seen < message["rounds"]:
                        stood = False
                        declined = False
                        ws.send_json({"type": "bet", "amount": 10})
                    continue
                if mtype == "error":
                    pytest.fail(f"server error: {message['message']}")

                state = message.get("state")
                if not state:
                    continue
                if state["state"] == "OFFERING_INSURANCE" and not declined:
                    declined = True
                    ws.send_json({"type": "insurance", "take": False})
                elif state["state"] == "PLAYER_TURN" and state["can_stand"] and not stood:
                    stood = True
                    ws.send_json({"type": "action", "action": "stand"})

            assert completed is not None, "daily never completed"

            assert completed["score"] >= 0
            assert completed["grade"] in ("S", "A", "B", "C", "D", "F")
            assert len(completed["round_results"]) == 20
            assert "share_text" in completed
            assert rounds_seen == 20

        # Recorded on the profile
        refreshed = client.get(f"/api/progression/profile/{pid}").json()
        assert completed["date"] in refreshed["daily"]

        # One attempt per day: a second start must be refused
        with client.websocket_connect("/ws/game/daily-e2e-2") as ws:
            ws.receive_json()
            ws.send_json({"type": "configure", "profile_id": pid})
            drain_until(ws, lambda m: m["type"] == "state_update")
            ws.send_json({"type": "start_daily"})
            message = drain_until(
                ws, lambda m: m["type"] in ("error", "daily_started")
            )
            assert message["type"] == "error"
            assert "already played" in message["message"]

    def test_daily_meta_endpoint(self, client):
        meta = client.get("/api/progression/daily").json()
        assert meta["rounds"] == 20
        assert meta["attempted"] is False
        assert "Vegas Strip" in meta["rules_summary"]

    def test_daily_enforces_bet_cap(self, client):
        with client.websocket_connect("/ws/game/daily-cap") as ws:
            ws.receive_json()
            ws.send_json({"type": "start_daily"})
            drain_until(ws, lambda m: m["type"] == "daily_started")
            drain_until(ws, lambda m: m["type"] == "state_update")

            ws.send_json({"type": "bet", "amount": 500})
            message = drain_until(ws, lambda m: m["type"] == "error")
            assert "$100" in message["message"]
