"""Training drill API endpoints."""

from random import Random
from fastapi import APIRouter, Header
from typing import Annotated

from api.schemas import (
    CountingDrillRequest,
    CountingDrillResponse,
    StrategyDrillRequest,
    StrategyDrillResponse,
    CountVerifyRequest,
    CountVerifyResponse,
    CardResponse,
)
from core.cards import Deck, Rank, Suit
from core.counting import HiLoSystem, KOSystem, Omega2System, WongHalvesSystem
from core.strategy import BasicStrategy, Action
from core.strategy.deviations import find_deviation

router = APIRouter()

# Session drill state storage
_drill_sessions: dict[str, dict] = {}


def _get_counting_system(name: str):
    """Get counting system by name."""
    systems = {
        "hilo": HiLoSystem,
        "ko": KOSystem,
        "omega2": Omega2System,
        "wong_halves": WongHalvesSystem,
    }
    return systems.get(name, HiLoSystem)()


@router.post("/counting/drill")
async def counting_drill(
    request: CountingDrillRequest,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> CountingDrillResponse:
    """Generate a counting drill."""
    rng = Random()
    deck = Deck(rng=rng)
    deck.shuffle()

    # Draw cards
    cards = [deck.draw() for _ in range(min(request.num_cards, 52))]

    # Calculate correct count
    system = _get_counting_system(request.system)
    system.reset()
    for card in cards:
        system.count_card(card)

    # Store for verification
    _drill_sessions[session_id] = {
        "type": "counting",
        "correct_count": system.running_count,
        "system": request.system,
    }

    return CountingDrillResponse(
        cards=[
            CardResponse(
                rank=str(c.rank),
                suit=str(c.suit),
                value=c.value,
            )
            for c in cards
        ],
        correct_count=system.running_count,
        system=request.system,
    )


@router.post("/counting/verify")
async def verify_count(
    request: CountVerifyRequest,
) -> CountVerifyResponse:
    """Verify a user's count."""
    session_data = _drill_sessions.get(request.session_id)

    if session_data is None or session_data.get("type") != "counting":
        return CountVerifyResponse(
            correct=False,
            actual_count=0,
            difference=request.user_count,
        )

    actual = session_data["correct_count"]
    diff = abs(request.user_count - actual)

    return CountVerifyResponse(
        correct=diff < 0.01,  # Allow small floating point differences
        actual_count=actual,
        difference=diff,
    )


@router.post("/strategy/drill")
async def strategy_drill(
    request: StrategyDrillRequest,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> StrategyDrillResponse:
    """Generate a strategy drill."""
    rng = Random()
    deck = Deck(rng=rng)
    deck.shuffle()

    # Generate random player hand (2 cards)
    player_cards = [deck.draw(), deck.draw()]
    dealer_upcard = deck.draw()

    # Calculate hand properties
    player_value = sum(c.value for c in player_cards)
    # Adjust for aces
    aces = sum(1 for c in player_cards if c.is_ace)
    while player_value > 21 and aces > 0:
        player_value -= 10
        aces -= 1

    is_soft = any(c.is_ace for c in player_cards) and player_value <= 21
    is_pair = len(player_cards) == 2 and player_cards[0].rank == player_cards[1].rank

    # Get correct action
    strategy = BasicStrategy()
    pair_rank = player_cards[0].value if is_pair else None
    correct_action = strategy.get_action(
        player_total=player_value,
        dealer_upcard=dealer_upcard.value,
        is_soft=is_soft,
        is_pair=is_pair,
        pair_rank=pair_rank,
    )

    # Check for deviations if requested
    deviation_desc = None
    if request.include_deviations and request.true_count is not None:
        deviation = find_deviation(
            player_total=player_value,
            is_soft=is_soft,
            is_pair=is_pair,
            dealer_upcard=dealer_upcard.value,
            true_count=request.true_count,
        )
        if deviation:
            correct_action = deviation.get_action(request.true_count)
            deviation_desc = deviation.description

    # Store for potential verification
    _drill_sessions[session_id] = {
        "type": "strategy",
        "correct_action": correct_action.name,
        "deviation": deviation_desc,
    }

    return StrategyDrillResponse(
        player_cards=[
            CardResponse(rank=str(c.rank), suit=str(c.suit), value=c.value)
            for c in player_cards
        ],
        player_value=player_value,
        is_soft=is_soft,
        is_pair=is_pair,
        dealer_upcard=CardResponse(
            rank=str(dealer_upcard.rank),
            suit=str(dealer_upcard.suit),
            value=dealer_upcard.value,
        ),
        correct_action=correct_action.name,
        deviation=deviation_desc,
    )
