"""Career mode over the API and WebSocket."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def drain_until(ws, predicate, limit=100):
    for _ in range(limit):
        message = ws.receive_json()
        if predicate(message):
            return message
    pytest.fail("condition not met within message limit")


class TestVenueList:
    def test_map_shape_and_access(self, client):
        profile = client.post("/api/progression/profile").json()
        data = client.get(
            f"/api/progression/venues/{profile['profile_id']}"
        ).json()

        venues = {v["id"]: v for v in data["venues"]}
        assert venues["kitchen-table"]["can_enter"] is True
        assert venues["riverboat"]["can_enter"] is False
        assert venues["neon-mirage"]["can_enter"] is True  # traps always open
        assert venues["neon-mirage"]["house_edge_pct"] > 1.5
        assert venues["high-limit-room"]["gates"]


class TestVenuePlay:
    def test_enter_venue_binds_rules_and_bankroll(self, client):
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]

        with client.websocket_connect("/ws/game/career-enter") as ws:
            ws.receive_json()
            ws.send_json({"type": "configure", "profile_id": pid})
            drain_until(ws, lambda m: m["type"] == "state_update")

            ws.send_json({"type": "configure", "venue_id": "kitchen-table"})
            entered = drain_until(ws, lambda m: m["type"] == "venue_entered")
            assert entered["name"] == "The Kitchen Table"
            assert entered["buy_in"] == 200

            state = drain_until(ws, lambda m: m["type"] == "state_update")["state"]
            assert state["bankroll"] == 200
            assert state["rules"]["num_decks"] == 1
            assert state["rules"]["min_bet"] == 5

    def test_locked_venue_rejected(self, client):
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]

        with client.websocket_connect("/ws/game/career-locked") as ws:
            ws.receive_json()
            ws.send_json({"type": "configure", "profile_id": pid})
            drain_until(ws, lambda m: m["type"] == "state_update")

            ws.send_json({"type": "configure", "venue_id": "high-limit-room"})
            message = drain_until(
                ws, lambda m: m["type"] in ("error", "venue_entered")
            )
            assert message["type"] == "error"

    def test_trap_walkaway_awards_badge(self, client):
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]

        with client.websocket_connect("/ws/game/career-trap") as ws:
            ws.receive_json()
            ws.send_json({"type": "configure", "profile_id": pid})
            drain_until(ws, lambda m: m["type"] == "state_update")

            ws.send_json({"type": "configure", "venue_id": "neon-mirage"})
            drain_until(ws, lambda m: m["type"] == "venue_entered")
            drain_until(ws, lambda m: m["type"] == "state_update")

            ws.send_json({"type": "leave_venue"})
            drain_until(ws, lambda m: m["type"] == "trap_walkaway")
            drain_until(ws, lambda m: m["type"] == "venue_left")

        refreshed = client.get(f"/api/progression/profile/{pid}").json()
        assert "walks-away" in refreshed["badges"]

    def test_heat_builds_and_backs_off(self, client):
        """Aggressive spreading at a watched venue must end the attempt."""
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]

        # Master basic strategy so the riverboat (watched venue) opens
        for _ in range(40):
            client.post(
                f"/api/progression/profile/{pid}/drill-event",
                json={"drill_key": "strategy", "correct": True},
            )
        client_events = client.get(f"/api/progression/venues/{pid}").json()
        riverboat = next(v for v in client_events["venues"] if v["id"] == "riverboat")
        assert riverboat["can_enter"] is False  # still locked: rung not reached

        # Clear the kitchen table by API-side event to unlock the riverboat
        # (playing to $300 through the WS would be slow and variance-bound)
        from api.progression_store import get_or_create_profile, save_profile
        from core.progression import apply_event
        import asyncio

        async def unlock():
            prof = await get_or_create_profile(pid)
            apply_event(prof, "venue_complete", {"venue_id": "kitchen-table"})
            await save_profile(prof)

        asyncio.get_event_loop().run_until_complete(unlock())

        with client.websocket_connect("/ws/game/career-heat") as ws:
            ws.receive_json()
            ws.send_json({"type": "configure", "profile_id": pid})
            drain_until(ws, lambda m: m["type"] == "state_update")

            ws.send_json({"type": "configure", "venue_id": "riverboat"})
            drain_until(ws, lambda m: m["type"] == "venue_entered")
            drain_until(ws, lambda m: m["type"] == "state_update")

            # Force the counter hot so jumps read as count-driven
            from api.websocket import manager
            session = manager._sessions["career-heat"]
            session.counter._running_count = 12.0  # TC ~ +6 on 2 decks

            backed_off = None
            saw_heat = False
            bets = [10, 200, 10, 200, 10, 200, 10, 200, 10, 200]
            for amount in bets:
                session.counter._running_count = 12.0  # keep the shoe hot
                ws.send_json({"type": "bet", "amount": amount})
                stood = False
                declined = False

                # Rounds resolve synchronously server-side, so sequence on
                # the ROUND_ENDED event rather than state snapshots.
                while True:
                    message = ws.receive_json()
                    mtype = message["type"]
                    if mtype == "backed_off":
                        backed_off = message
                        break
                    if mtype == "heat":
                        saw_heat = True
                        continue
                    if mtype == "error":
                        pytest.fail(message["message"])
                    if message.get("event_type") == "ROUND_ENDED":
                        break
                    state = message.get("state")
                    if not state:
                        continue
                    if state["state"] == "OFFERING_INSURANCE" and not declined:
                        declined = True
                        ws.send_json({"type": "insurance", "take": False})
                    elif state["state"] == "PLAYER_TURN" and state["can_stand"] and not stood:
                        stood = True
                        ws.send_json({"type": "action", "action": "stand"})
                if backed_off:
                    break

            assert saw_heat, "the pit never reacted to a 1-to-20 spread at TC+6"
            assert backed_off is not None, "spreading 1-20 at TC+6 never drew a back-off"
            assert backed_off["reasons"]
            assert backed_off["lesson"]
