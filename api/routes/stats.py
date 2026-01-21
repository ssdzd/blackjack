"""Statistics API endpoints."""

from decimal import Decimal
from fastapi import APIRouter

from api.schemas import (
    HouseEdgeRequest,
    HouseEdgeResponse,
    KellyBetRequest,
    KellyBetResponse,
    SessionStatsResponse,
)
from core.strategy.rules import RuleSet
from core.statistics.house_edge import HouseEdgeCalculator
from core.statistics.kelly import KellyCalculator

router = APIRouter()


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
