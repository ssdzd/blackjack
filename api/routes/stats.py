"""Statistics API endpoints."""

import time
from decimal import Decimal
from fastapi import APIRouter, Header
from typing import Annotated

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
from core.strategy.rules import RuleSet
from core.statistics.house_edge import HouseEdgeCalculator
from core.statistics.kelly import KellyCalculator

router = APIRouter()

# Performance stats storage (would use Redis/DB in production)
_performance_stats: dict[str, PerformanceStats] = {}


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
async def get_session_stats() -> SessionStatsResponse:
    """Get session statistics (placeholder)."""
    # This would be populated from actual session data
    return SessionStatsResponse(
        hands_played=0,
        win_rate=0.0,
        total_wagered=0.0,
        net_result=0.0,
        counting_accuracy=None,
        strategy_accuracy=None,
    )


def _get_or_create_performance_stats(session_id: str) -> PerformanceStats:
    """Get or create performance stats for a session."""
    if session_id not in _performance_stats:
        _performance_stats[session_id] = PerformanceStats()
    return _performance_stats[session_id]


@router.get("/performance/{session_id}")
async def get_performance_stats(session_id: str) -> PerformanceStats:
    """Get comprehensive performance statistics for a session."""
    return _get_or_create_performance_stats(session_id)


@router.post("/performance/{session_id}/record")
async def record_stat(
    session_id: str,
    request: RecordStatRequest,
) -> PerformanceStats:
    """Record a stat entry for a session."""
    stats = _get_or_create_performance_stats(session_id)
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

    return stats


@router.delete("/performance/{session_id}")
async def reset_performance_stats(session_id: str) -> PerformanceStats:
    """Reset performance statistics for a session."""
    _performance_stats[session_id] = PerformanceStats()
    return _performance_stats[session_id]
