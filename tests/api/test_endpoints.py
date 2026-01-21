"""Tests for API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from api.main import app


@pytest_asyncio.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_new_game(client):
    """Test creating a new game."""
    response = await client.post("/api/game/new")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data


@pytest.mark.asyncio
async def test_game_state(client):
    """Test getting game state."""
    # Create a new game first
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    # Get state
    response = await client.get(
        "/api/game/state",
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 200
    data = response.json()

    assert "state" in data
    assert "bankroll" in data
    assert data["state"] == "WAITING_FOR_BET"


@pytest.mark.asyncio
async def test_place_bet(client):
    """Test placing a bet."""
    # Create a new game
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    # Place bet
    response = await client.post(
        "/api/game/bet",
        json={"amount": 100},
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be in player turn after dealing
    assert data["state"] in ["PLAYER_TURN", "RESOLVING", "ROUND_COMPLETE"]
    assert len(data["player_hands"]) >= 1


@pytest.mark.asyncio
async def test_invalid_bet_amount(client):
    """Test placing an invalid bet."""
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    # Try to bet more than bankroll
    response = await client.post(
        "/api/game/bet",
        json={"amount": 10000},
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_house_edge_calculation(client):
    """Test house edge calculation endpoint."""
    response = await client.post(
        "/api/stats/house-edge",
        json={
            "num_decks": 6,
            "dealer_hits_soft_17": True,
            "blackjack_payout": 1.5,
            "double_after_split": True,
            "surrender": "late",
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert "house_edge_percent" in data
    assert "player_advantage_at_tc" in data
    assert 0 < data["house_edge_percent"] < 2


@pytest.mark.asyncio
async def test_kelly_bet_calculation(client):
    """Test Kelly bet calculation endpoint."""
    response = await client.post(
        "/api/stats/kelly-bet",
        json={
            "bankroll": 10000,
            "player_edge_percent": 1.0,
            "kelly_fraction": 0.5,
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert "optimal_bet" in data
    assert "bet_as_percent_of_bankroll" in data


@pytest.mark.asyncio
async def test_counting_drill(client):
    """Test counting drill endpoint."""
    # Create session
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    response = await client.post(
        "/api/training/counting/drill",
        json={"system": "hilo", "num_cards": 10},
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 200
    data = response.json()

    assert "cards" in data
    assert "correct_count" in data
    assert "system" in data
    assert len(data["cards"]) == 10


@pytest.mark.asyncio
async def test_strategy_drill(client):
    """Test strategy drill endpoint."""
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    response = await client.post(
        "/api/training/strategy/drill",
        json={"include_deviations": False},
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 200
    data = response.json()

    assert "player_cards" in data
    assert "dealer_upcard" in data
    assert "correct_action" in data
    assert len(data["player_cards"]) == 2


# Session stats endpoint tests

@pytest.mark.asyncio
async def test_session_stats_returns_zeros_initially(client):
    """Test that session stats returns zeros for a new session."""
    # Create a new game/session
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    # Get session stats
    response = await client.get(
        "/api/stats/session",
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["hands_played"] == 0
    assert data["win_rate"] == 0.0
    assert data["total_wagered"] == 0.0
    assert data["net_result"] == 0.0
    assert data["counting_accuracy"] is None
    assert data["strategy_accuracy"] is None


@pytest.mark.asyncio
async def test_session_stats_after_recording(client):
    """Test session stats reflect recorded data."""
    # Create a new game/session
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    # Record some stats
    await client.post(
        f"/api/stats/performance/{session_id}/record",
        json={"stat_type": "hand_win", "value": 100},
    )
    await client.post(
        f"/api/stats/performance/{session_id}/record",
        json={"stat_type": "hand_loss", "value": 100},
    )

    # Get session stats
    response = await client.get(
        "/api/stats/session",
        headers={"X-Session-ID": session_id},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["hands_played"] == 2
    assert data["win_rate"] == 0.5  # 1 win / 2 hands
    assert data["total_wagered"] == 200.0


@pytest.mark.asyncio
async def test_performance_stats_record_hand_win(client):
    """Test recording a hand win updates performance stats."""
    # Create a new game/session
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    # Record a win
    response = await client.post(
        f"/api/stats/performance/{session_id}/record",
        json={"stat_type": "hand_win", "value": 50},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["hands_played"] == 1
    assert data["wins"] == 1
    assert data["total_wagered"] == 50.0
    assert data["net_result"] == 50.0


@pytest.mark.asyncio
async def test_performance_stats_record_hand_loss(client):
    """Test recording a hand loss updates performance stats."""
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    response = await client.post(
        f"/api/stats/performance/{session_id}/record",
        json={"stat_type": "hand_loss", "value": 75},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["hands_played"] == 1
    assert data["losses"] == 1
    assert data["total_wagered"] == 75.0
    assert data["net_result"] == -75.0


@pytest.mark.asyncio
async def test_performance_stats_record_blackjack(client):
    """Test recording a blackjack win updates performance stats."""
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    response = await client.post(
        f"/api/stats/performance/{session_id}/record",
        json={"stat_type": "hand_blackjack", "value": 100},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["hands_played"] == 1
    assert data["wins"] == 1
    assert data["blackjacks"] == 1
    assert data["total_wagered"] == 100.0
    assert data["net_result"] == 150.0  # 1.5x payout


@pytest.mark.asyncio
async def test_performance_stats_reset(client):
    """Test resetting performance stats."""
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    # Record some stats first
    await client.post(
        f"/api/stats/performance/{session_id}/record",
        json={"stat_type": "hand_win", "value": 100},
    )

    # Reset
    response = await client.delete(f"/api/stats/performance/{session_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["hands_played"] == 0
    assert data["wins"] == 0
    assert data["net_result"] == 0.0


@pytest.mark.asyncio
async def test_performance_stats_get(client):
    """Test getting performance stats by session ID."""
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    # Record some data
    await client.post(
        f"/api/stats/performance/{session_id}/record",
        json={"stat_type": "count_drill", "correct": True},
    )
    await client.post(
        f"/api/stats/performance/{session_id}/record",
        json={"stat_type": "count_drill", "correct": False},
    )

    # Get performance stats
    response = await client.get(f"/api/stats/performance/{session_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["count_drills_attempted"] == 2
    assert data["count_drills_correct"] == 1


@pytest.mark.asyncio
async def test_performance_stats_history_limited(client):
    """Test that history is limited to 100 entries."""
    new_response = await client.post("/api/game/new")
    session_id = new_response.json()["session_id"]

    # Record more than 100 entries
    for _ in range(105):
        await client.post(
            f"/api/stats/performance/{session_id}/record",
            json={"stat_type": "hand_win", "value": 10},
        )

    # Get performance stats
    response = await client.get(f"/api/stats/performance/{session_id}")
    assert response.status_code == 200
    data = response.json()

    # History should be capped at 100
    assert len(data["history"]) == 100
