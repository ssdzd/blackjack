"""Statistics API endpoints."""

import time
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Header

from api.schemas import (
    HouseEdgeRequest,
    HouseEdgeResponse,
    KellyBetRequest,
    KellyBetResponse,
    SessionStatsResponse,
    PerformanceStats,
    RecordStatRequest,
    SessionHistoryEntry,
)
from api.session import get_session_store
from core.strategy.rules import RuleSet
from core.statistics.house_edge import HouseEdgeCalculator
from core.statistics.kelly import KellyCalculator

router = APIRouter()

# Performance stats memory cache (backed by session store)
_performance_stats: dict[str, PerformanceStats] = {}

# Session data keys
SESSION_KEY_PERFORMANCE = "performance"
SESSION_KEY_LAST_ACTIVITY = "last_activity"


def _serialize_performance_stats(stats: PerformanceStats) -> dict[str, Any]:
    """Serialize performance stats for session storage."""
    return {
        "hands_played": stats.hands_played,
        "wins": stats.wins,
        "losses": stats.losses,
        "pushes": stats.pushes,
        "blackjacks": stats.blackjacks,
        "total_wagered": stats.total_wagered,
        "net_result": stats.net_result,
        "count_drills_attempted": stats.count_drills_attempted,
        "count_drills_correct": stats.count_drills_correct,
        "count_average_error": stats.count_average_error,
        "strategy_drills_attempted": stats.strategy_drills_attempted,
        "strategy_drills_correct": stats.strategy_drills_correct,
        "deviation_drills_attempted": stats.deviation_drills_attempted,
        "deviation_drills_correct": stats.deviation_drills_correct,
        "speed_drills_attempted": stats.speed_drills_attempted,
        "speed_drills_correct": stats.speed_drills_correct,
        "speed_drill_best_score": stats.speed_drill_best_score,
        "speed_drill_best_time_ms": stats.speed_drill_best_time_ms,
        "history": [h.model_dump() for h in stats.history],
    }


def _deserialize_performance_stats(data: dict[str, Any]) -> PerformanceStats:
    """Deserialize performance stats from session storage."""
    history = [SessionHistoryEntry(**h) for h in data.get("history", [])]
    return PerformanceStats(
        hands_played=data.get("hands_played", 0),
        wins=data.get("wins", 0),
        losses=data.get("losses", 0),
        pushes=data.get("pushes", 0),
        blackjacks=data.get("blackjacks", 0),
        total_wagered=data.get("total_wagered", 0.0),
        net_result=data.get("net_result", 0.0),
        count_drills_attempted=data.get("count_drills_attempted", 0),
        count_drills_correct=data.get("count_drills_correct", 0),
        count_average_error=data.get("count_average_error", 0.0),
        strategy_drills_attempted=data.get("strategy_drills_attempted", 0),
        strategy_drills_correct=data.get("strategy_drills_correct", 0),
        deviation_drills_attempted=data.get("deviation_drills_attempted", 0),
        deviation_drills_correct=data.get("deviation_drills_correct", 0),
        speed_drills_attempted=data.get("speed_drills_attempted", 0),
        speed_drills_correct=data.get("speed_drills_correct", 0),
        speed_drill_best_score=data.get("speed_drill_best_score", 0),
        speed_drill_best_time_ms=data.get("speed_drill_best_time_ms"),
        history=history,
    )


async def _load_performance_stats(session_id: str) -> PerformanceStats | None:
    """Load performance stats from session store."""
    store = await get_session_store()
    session_data = await store.get(session_id)
    if session_data and SESSION_KEY_PERFORMANCE in session_data:
        return _deserialize_performance_stats(session_data[SESSION_KEY_PERFORMANCE])
    return None


async def _save_performance_stats(session_id: str, stats: PerformanceStats) -> None:
    """Save performance stats to session store."""
    store = await get_session_store()
    session_data = await store.get(session_id) or {}
    session_data[SESSION_KEY_PERFORMANCE] = _serialize_performance_stats(stats)
    session_data[SESSION_KEY_LAST_ACTIVITY] = int(time.time())
    await store.set(session_id, session_data)


@router.post("/house-edge")
async def calculate_house_edge(request: HouseEdgeRequest) -> HouseEdgeResponse:
    """Calculate house edge for given rules."""
    rules = RuleSet(
        num_decks=request.num_decks,
        dealer_hits_soft_17=request.dealer_hits_soft_17,
        blackjack_payout=request.blackjack_payout,
        double_after_split=request.double_after_split,
        surrender=request.surrender,
    )

    calculator = HouseEdgeCalculator(rules)
    house_edge = calculator.calculate()

    # Calculate player advantage at various true counts
    tc_advantages = {}
    for tc in range(-5, 11):
        advantage = calculator.player_advantage_with_count(float(tc), house_edge)
        tc_advantages[tc] = float(advantage)

    return HouseEdgeResponse(
        house_edge_percent=float(house_edge),
        player_advantage_at_tc=tc_advantages,
    )


@router.post("/kelly-bet")
async def calculate_kelly_bet(request: KellyBetRequest) -> KellyBetResponse:
    """Calculate Kelly-optimal bet size."""
    calculator = KellyCalculator(
        bankroll=Decimal(str(request.bankroll)),
        min_bet=Decimal("10"),
        max_bet=Decimal("1000"),
        kelly_fraction=request.kelly_fraction,
    )

    player_edge = Decimal(str(request.player_edge_percent)) / 100
    optimal_bet = calculator.optimal_bet(player_edge)

    bet_percent = (optimal_bet / Decimal(str(request.bankroll))) * 100

    return KellyBetResponse(
        optimal_bet=float(optimal_bet),
        bet_as_percent_of_bankroll=float(bet_percent),
    )


@router.get("/session")
async def get_session_stats(
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> SessionStatsResponse:
    """Get session statistics."""
    stats = await _get_or_create_performance_stats(session_id)

    win_rate = stats.wins / stats.hands_played if stats.hands_played > 0 else 0.0

    counting_accuracy = None
    if stats.count_drills_attempted > 0:
        counting_accuracy = stats.count_drills_correct / stats.count_drills_attempted

    strategy_accuracy = None
    if stats.strategy_drills_attempted > 0:
        strategy_accuracy = stats.strategy_drills_correct / stats.strategy_drills_attempted

    return SessionStatsResponse(
        hands_played=stats.hands_played,
        win_rate=win_rate,
        total_wagered=stats.total_wagered,
        net_result=stats.net_result,
        counting_accuracy=counting_accuracy,
        strategy_accuracy=strategy_accuracy,
    )


async def _get_or_create_performance_stats(session_id: str) -> PerformanceStats:
    """Get or create performance stats for a session."""
    # Check memory cache first
    if session_id in _performance_stats:
        return _performance_stats[session_id]

    # Try to load from session store
    stats = await _load_performance_stats(session_id)
    if stats is not None:
        _performance_stats[session_id] = stats
        return stats

    # Create new stats
    stats = PerformanceStats()
    _performance_stats[session_id] = stats
    await _save_performance_stats(session_id, stats)
    return stats


@router.get("/performance/{session_id}")
async def get_performance_stats(session_id: str) -> PerformanceStats:
    """Get comprehensive performance statistics for a session."""
    return await _get_or_create_performance_stats(session_id)


@router.post("/performance/{session_id}/record")
async def record_stat(
    session_id: str,
    request: RecordStatRequest,
) -> PerformanceStats:
    """Record a stat entry for a session."""
    stats = await _get_or_create_performance_stats(session_id)
    now = int(time.time() * 1000)

    # Update stats based on type
    if request.stat_type == "hand_win":
        stats.hands_played += 1
        stats.wins += 1
        if request.value:
            stats.total_wagered += request.value
            stats.net_result += request.value
    elif request.stat_type == "hand_loss":
        stats.hands_played += 1
        stats.losses += 1
        if request.value:
            stats.total_wagered += request.value
            stats.net_result -= request.value
    elif request.stat_type == "hand_push":
        stats.hands_played += 1
        stats.pushes += 1
        if request.value:
            stats.total_wagered += request.value
    elif request.stat_type == "hand_blackjack":
        stats.hands_played += 1
        stats.wins += 1
        stats.blackjacks += 1
        if request.value:
            stats.total_wagered += request.value
            stats.net_result += request.value * 1.5
    elif request.stat_type == "count_drill":
        stats.count_drills_attempted += 1
        if request.correct:
            stats.count_drills_correct += 1
        if request.value is not None:
            # Update average error
            total_error = stats.count_average_error * (stats.count_drills_attempted - 1)
            total_error += request.value
            stats.count_average_error = total_error / stats.count_drills_attempted
    elif request.stat_type == "strategy_drill":
        stats.strategy_drills_attempted += 1
        if request.correct:
            stats.strategy_drills_correct += 1
    elif request.stat_type == "deviation_drill":
        stats.deviation_drills_attempted += 1
        if request.correct:
            stats.deviation_drills_correct += 1
    elif request.stat_type == "speed_drill":
        stats.speed_drills_attempted += 1
        if request.correct:
            stats.speed_drills_correct += 1
        if request.value is not None:
            score = int(request.value)
            if score > stats.speed_drill_best_score:
                stats.speed_drill_best_score = score
        if request.details and "time_ms" in request.details:
            time_ms = request.details["time_ms"]
            if stats.speed_drill_best_time_ms is None or time_ms < stats.speed_drill_best_time_ms:
                stats.speed_drill_best_time_ms = time_ms

    # Add to history (keep last 100 entries)
    entry = SessionHistoryEntry(
        timestamp=now,
        bankroll=stats.net_result,  # Approximation
        event_type=request.stat_type,
        details=request.details,
    )
    stats.history.append(entry)
    if len(stats.history) > 100:
        stats.history = stats.history[-100:]

    # Save to session store
    await _save_performance_stats(session_id, stats)

    return stats


@router.delete("/performance/{session_id}")
async def reset_performance_stats(session_id: str) -> PerformanceStats:
    """Reset performance statistics for a session."""
    stats = PerformanceStats()
    _performance_stats[session_id] = stats
    await _save_performance_stats(session_id, stats)
    return stats
