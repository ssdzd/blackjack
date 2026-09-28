"""True-count conversion drill endpoints."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestTcConversion:
    def test_drill_and_correct_answer(self, client):
        drill = client.post("/api/training/tc-conversion").json()
        assert drill["running_count"] != 0
        assert drill["decks_remaining"] > 0

        expected = int(drill["running_count"] / drill["decks_remaining"])
        result = client.post(
            "/api/training/tc-conversion/verify",
            json={"drill_id": drill["drill_id"], "user_tc": expected},
        ).json()
        assert result["correct"] is True
        assert result["expected"] == expected

    def test_truncation_toward_zero(self, client):
        # RC -7 over 2 decks: exact -3.5, expected -3 (toward zero)
        drill = client.post("/api/training/tc-conversion").json()
        wrong = int(drill["running_count"] / drill["decks_remaining"]) + 5
        result = client.post(
            "/api/training/tc-conversion/verify",
            json={"drill_id": drill["drill_id"], "user_tc": wrong},
        ).json()
        assert result["correct"] is False
        assert "method_hint" in result

    def test_drill_single_use(self, client):
        drill = client.post("/api/training/tc-conversion").json()
        expected = int(drill["running_count"] / drill["decks_remaining"])
        client.post(
            "/api/training/tc-conversion/verify",
            json={"drill_id": drill["drill_id"], "user_tc": expected},
        )
        replay = client.post(
            "/api/training/tc-conversion/verify",
            json={"drill_id": drill["drill_id"], "user_tc": expected},
        ).json()
        assert replay["correct"] is False
        assert "error" in replay

    def test_feeds_progression(self, client):
        profile = client.post("/api/progression/profile").json()
        pid = profile["profile_id"]
        drill = client.post("/api/training/tc-conversion").json()
        expected = int(drill["running_count"] / drill["decks_remaining"])
        client.post(
            "/api/training/tc-conversion/verify",
            json={"drill_id": drill["drill_id"], "user_tc": expected},
            headers={"X-Profile-ID": pid},
        )
        refreshed = client.get(f"/api/progression/profile/{pid}").json()
        assert refreshed["lifetime"]["drill_tc-conversion"] == 1
