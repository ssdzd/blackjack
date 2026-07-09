"""Tests for the progression API: profiles, settings, drill events, WS pushes."""

import pytest
from fastapi.testclient import TestClient

import api.progression_store as store_module
from api.main import app
from api.progression_store import PROFILE_TTL, save_profile
from core.progression import new_profile


@pytest.fixture
def client():
    return TestClient(app)


class TestProfileLifecycle:
    def test_create_and_fetch(self, client):
        created = client.post("/api/progression/profile").json()
        assert created["xp"] == 0
        assert created["level"] == 1
        assert created["title"] == "Tourist"
        assert created["nodes"]["basic-strategy"]["status"] == "available"

        fetched = client.get(f"/api/progression/profile/{created['profile_id']}").json()
        assert fetched["profile_id"] == created["profile_id"]

    def test_get_unknown_profile_creates_it(self, client):
        fetched = client.get("/api/progression/profile/reborn-123").json()
        assert fetched["profile_id"] == "reborn-123"
        assert fetched["xp"] == 0

    @pytest.mark.asyncio
    async def test_profiles_persist_with_long_ttl(self, monkeypatch):
        calls = {}

        class RecordingStore:
            async def set(self, key, data, ttl=None):
                calls["key"] = key
                calls["ttl"] = ttl

            async def get(self, key):
                return None

        async def fake_get_store():
            return RecordingStore()

        monkeypatch.setattr(store_module, "get_session_store", fake_get_store)
        await save_profile(new_profile("ttl-test"))

        assert calls["key"] == "profile:ttl-test"
        assert calls["ttl"] == PROFILE_TTL
        assert PROFILE_TTL >= 30 * 24 * 3600  # never the 1-hour session default


class TestSettings:
    def test_patch_settings(self, client):
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]

        response = client.patch(
            f"/api/progression/profile/{pid}/settings",
            json={"counting_system": "ko", "visibility": "hidden"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["settings"]["counting_system"] == "ko"
        assert data["settings"]["visibility"] == "hidden"

    def test_patch_rejects_unknown_system(self, client):
        profile = client.post("/api/progression/profile").json()
        response = client.patch(
            f"/api/progression/profile/{profile['profile_id']}/settings",
            json={"counting_system": "psychic"},
        )
        assert response.status_code == 422

    def test_patch_unknown_profile_404(self, client):
        response = client.patch(
            "/api/progression/profile/nope/settings", json={"sound": False}
        )
        assert response.status_code == 404


class TestDrillEvents:
    def test_client_drill_event_awards_xp(self, client):
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]

        delta = client.post(
            f"/api/progression/profile/{pid}/drill-event",
            json={"drill_key": "strategy", "correct": True},
        ).json()
        assert delta["xp_gained"] > 0

        refreshed = client.get(f"/api/progression/profile/{pid}").json()
        assert refreshed["xp"] == delta["xp_total"]
        assert refreshed["lifetime"]["drill_strategy"] == 1

    def test_server_verified_drills_rejected_here(self, client):
        profile = client.post("/api/progression/profile").json()
        response = client.post(
            f"/api/progression/profile/{profile['profile_id']}/drill-event",
            json={"drill_key": "speed", "correct": True},
        )
        assert response.status_code == 422

    def test_speed_drill_verify_feeds_progression(self, client):
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]

        drill = client.post(
            "/api/training/counting/speed-drill",
            json={"num_cards": 52, "system": "hilo", "card_speed_ms": 300},
            headers={"X-Session-ID": "speed-prog-test"},
        ).json()

        client.post(
            "/api/training/counting/speed-drill/verify",
            json={
                "drill_id": drill["drill_id"],
                "user_count": drill["correct_count"],
                "completion_time_ms": 18000,
            },
            headers={"X-Profile-ID": pid},
        )

        refreshed = client.get(f"/api/progression/profile/{pid}").json()
        assert refreshed["lifetime"]["deck_countdown_pass"] == 1
        assert "twenty-second-deck" in refreshed["badges"]


class TestSkillTreeEndpoint:
    def test_tree_shape(self, client):
        profile = client.post("/api/progression/profile").json()
        tree = client.get(
            f"/api/progression/skill-tree/{profile['profile_id']}"
        ).json()

        nodes = {n["id"]: n for n in tree["nodes"]}
        assert nodes["basic-strategy"]["status"] == "available"
        assert nodes["card-values"]["status"] == "locked"
        assert "≥" in nodes["basic-strategy"]["gate"]
        assert nodes["casino-ready"]["prerequisites"]


class TestBadgeBook:
    def test_badges_listed(self, client):
        data = client.get("/api/progression/badges").json()
        ids = {b["id"] for b in data["badges"]}
        assert "twenty-second-deck" in ids
        assert "perfect-shoe" in ids


class TestWebSocketProgression:
    def test_checkin_pushes_progression(self, client):
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]

        with client.websocket_connect("/ws/game/prog-ws-test") as ws:
            ws.receive_json()  # initial state
            ws.send_json({"type": "configure", "profile_id": pid})
            ws.receive_json()  # state_update ack

            ws.send_json({"type": "count_checkin", "running_count": 0})
            got_result = False
            got_progression = False
            for _ in range(10):
                message = ws.receive_json()
                if message["type"] == "count_checkin_result":
                    got_result = True
                    assert message["correct"] is True
                if message["type"] == "progression":
                    got_progression = True
                    assert message["delta"]["xp_gained"] > 0
                if got_result and got_progression:
                    break
            assert got_result and got_progression

        refreshed = client.get(f"/api/progression/profile/{pid}").json()
        assert refreshed["lifetime"]["checkins_exact"] == 1
