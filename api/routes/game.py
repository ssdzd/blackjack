"""Game API endpoints."""

from decimal import Decimal
from fastapi import APIRouter, HTTPException, Header
from typing import Annotated

from api.schemas import (
    BetRequest,
    ActionRequest,
    GameStateResponse,
    HandResponse,
    CardResponse,
)
from api.session import get_session, update_session, create_session
from core.game import BlackjackGame
from core.strategy.rules import RuleSet

router = APIRouter()

# In-memory game storage (would use session in production)
_games: dict[str, BlackjackGame] = {}


def _get_game(session_id: str) -> BlackjackGame:
    """Get or create a game for the session."""
    if session_id not in _games:
        _games[session_id] = BlackjackGame(
            rules=RuleSet(),
            initial_bankroll=Decimal("1000"),
        )
    return _games[session_id]


def _hand_to_response(hand) -> HandResponse:
    """Convert a Hand to HandResponse."""
    return HandResponse(
        cards=[
            CardResponse(
                rank=str(c.rank),
                suit=str(c.suit),
                value=c.value,
            )
            for c in hand.cards
        ],
        value=hand.value,
        is_soft=hand.is_soft,
        is_blackjack=hand.is_blackjack,
        is_busted=hand.is_busted,
        bet=hand.bet,
    )


def _game_state_response(game: BlackjackGame) -> GameStateResponse:
    """Convert game state to response."""
    dealer_showing = None
    if game.dealer_hand.cards:
        c = game.dealer_hand.cards[0]
        dealer_showing = CardResponse(
            rank=str(c.rank),
            suit=str(c.suit),
            value=c.value,
        )

    return GameStateResponse(
        state=game.state.name,
        player_hands=[_hand_to_response(h) for h in game.player.hands],
        current_hand_index=game.player.current_hand_index,
        dealer_hand=_hand_to_response(game.dealer_hand),
        dealer_showing=dealer_showing,
        bankroll=float(game.player.bankroll),
        can_hit=game.can_hit,
        can_stand=game.can_stand,
        can_double=game.can_double,
        can_split=game.can_split,
        can_surrender=game.can_surrender,
    )


@router.post("/new")
async def new_game(
    session_id: Annotated[str | None, Header(alias="X-Session-ID")] = None,
) -> dict[str, str]:
    """Create a new game session."""
    if session_id is None:
        session_id = await create_session()

    # Reset game
    _games[session_id] = BlackjackGame(
        rules=RuleSet(),
        initial_bankroll=Decimal("1000"),
    )

    return {"session_id": session_id}


@router.get("/state")
async def get_state(
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> GameStateResponse:
    """Get current game state."""
    game = _get_game(session_id)
    return _game_state_response(game)


@router.post("/bet")
async def place_bet(
    request: BetRequest,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> GameStateResponse:
    """Place a bet and deal cards."""
    game = _get_game(session_id)

    if not game.bet(request.amount):
        raise HTTPException(status_code=400, detail="Invalid bet")

    return _game_state_response(game)


@router.post("/action")
async def player_action(
    request: ActionRequest,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> GameStateResponse:
    """Execute a player action."""
    game = _get_game(session_id)

    actions = {
        "hit": game.hit,
        "stand": game.stand,
        "double": game.double_down,
        "split": game.split,
        "surrender": game.surrender,
    }

    action_fn = actions.get(request.action)
    if action_fn is None:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    if not action_fn():
        raise HTTPException(status_code=400, detail=f"Cannot {request.action} now")

    return _game_state_response(game)
