"""Game API endpoints."""

import time
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Header
from typing import Annotated, Any

from api.schemas import (
    BetRequest,
    ActionRequest,
    GameStateResponse,
    HandResponse,
    CardResponse,
)
from api.session import get_session, update_session, create_session, get_session_store
from core.cards import Card, Rank, Suit
from core.game import BlackjackGame
from core.hand import Hand
from core.strategy.rules import RuleSet

router = APIRouter()

# In-memory game cache (for performance, backed by session store)
_games: dict[str, BlackjackGame] = {}

# Session data keys
SESSION_KEY_GAME = "game"
SESSION_KEY_PERFORMANCE = "performance"
SESSION_KEY_CREATED_AT = "created_at"
SESSION_KEY_LAST_ACTIVITY = "last_activity"


def _serialize_card(card: Card) -> dict[str, int]:
    """Serialize a card to a dict."""
    return {"rank": card.rank.value, "suit": card.suit.value}


def _deserialize_card(data: dict[str, int]) -> Card:
    """Deserialize a card from a dict."""
    return Card(Rank(data["rank"]), Suit(data["suit"]))


def _serialize_hand(hand: Hand) -> dict[str, Any]:
    """Serialize a hand to a dict."""
    return {
        "cards": [_serialize_card(c) for c in hand.cards],
        "bet": hand.bet,
        "is_doubled": hand.is_doubled,
        "is_split_hand": hand.is_split_hand,
        "is_surrendered": hand.is_surrendered,
    }


def _deserialize_hand(data: dict[str, Any]) -> Hand:
    """Deserialize a hand from a dict."""
    hand = Hand(
        cards=[_deserialize_card(c) for c in data["cards"]],
        bet=data["bet"],
        is_doubled=data["is_doubled"],
        is_split_hand=data["is_split_hand"],
        is_surrendered=data["is_surrendered"],
    )
    return hand


def _serialize_game(game: BlackjackGame) -> dict[str, Any]:
    """Serialize game state for session storage."""
    return {
        "state": game._machine_state,
        "bankroll": str(game.player.bankroll),
        "insurance_bet": str(game.player.insurance_bet),
        "current_hand_index": game.player.current_hand_index,
        "shoe_cards": [_serialize_card(c) for c in game.shoe._cards],
        "shoe_num_decks": game.shoe._num_decks,
        "shoe_penetration": game.shoe._penetration,
        "player_hands": [_serialize_hand(h) for h in game.player.hands],
        "dealer_hand": _serialize_hand(game.dealer_hand),
        "rules": {
            "num_decks": game.rules.num_decks,
            "min_bet": game.rules.min_bet,
            "max_bet": game.rules.max_bet,
            "dealer_hits_soft_17": game.rules.dealer_hits_soft_17,
            "blackjack_payout": game.rules.blackjack_payout,
            "double_after_split": game.rules.double_after_split,
            "double_on": game.rules.double_on,
            "resplit_aces": game.rules.resplit_aces,
            "hit_split_aces": game.rules.hit_split_aces,
            "max_splits": game.rules.max_splits,
            "surrender": game.rules.surrender,
            "insurance_allowed": game.rules.insurance_allowed,
            "dealer_peeks": game.rules.dealer_peeks,
        },
    }


def _deserialize_game(data: dict[str, Any]) -> BlackjackGame:
    """Restore game from session data."""
    rules_data = data["rules"]
    rules = RuleSet(
        num_decks=rules_data["num_decks"],
        min_bet=rules_data["min_bet"],
        max_bet=rules_data["max_bet"],
        dealer_hits_soft_17=rules_data["dealer_hits_soft_17"],
        blackjack_payout=rules_data["blackjack_payout"],
        double_after_split=rules_data["double_after_split"],
        double_on=rules_data["double_on"],
        resplit_aces=rules_data["resplit_aces"],
        hit_split_aces=rules_data["hit_split_aces"],
        max_splits=rules_data["max_splits"],
        surrender=rules_data["surrender"],
        insurance_allowed=rules_data["insurance_allowed"],
        dealer_peeks=rules_data["dealer_peeks"],
    )

    # Create game with restored rules
    game = BlackjackGame(
        rules=rules,
        num_decks=data["shoe_num_decks"],
        penetration=data["shoe_penetration"],
        initial_bankroll=Decimal(data["bankroll"]),
    )

    # Restore state machine state
    game._machine_state = data["state"]

    # Restore player state
    game.player.bankroll = Decimal(data["bankroll"])
    game.player.insurance_bet = Decimal(data["insurance_bet"])
    game.player.current_hand_index = data["current_hand_index"]
    game.player.hands = [_deserialize_hand(h) for h in data["player_hands"]]

    # Restore dealer hand
    game.dealer_hand = _deserialize_hand(data["dealer_hand"])

    # Restore shoe cards
    game.shoe._cards = [_deserialize_card(c) for c in data["shoe_cards"]]

    return game


async def _load_game(session_id: str) -> BlackjackGame | None:
    """Load game from session store."""
    store = await get_session_store()
    session_data = await store.get(session_id)
    if session_data and SESSION_KEY_GAME in session_data:
        return _deserialize_game(session_data[SESSION_KEY_GAME])
    return None


async def _save_game(session_id: str, game: BlackjackGame) -> None:
    """Save game to session store."""
    store = await get_session_store()
    session_data = await store.get(session_id) or {}
    session_data[SESSION_KEY_GAME] = _serialize_game(game)
    session_data[SESSION_KEY_LAST_ACTIVITY] = int(time.time())
    if SESSION_KEY_CREATED_AT not in session_data:
        session_data[SESSION_KEY_CREATED_AT] = int(time.time())
    await store.set(session_id, session_data)


async def _get_game(session_id: str) -> BlackjackGame:
    """Get or create a game for the session."""
    # Check memory cache first
    if session_id in _games:
        return _games[session_id]

    # Try to load from session store
    game = await _load_game(session_id)
    if game is not None:
        _games[session_id] = game
        return game

    # Create new game
    game = BlackjackGame(
        rules=RuleSet(),
        initial_bankroll=Decimal("1000"),
    )
    _games[session_id] = game
    await _save_game(session_id, game)
    return game


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
    game = BlackjackGame(
        rules=RuleSet(),
        initial_bankroll=Decimal("1000"),
    )
    _games[session_id] = game
    await _save_game(session_id, game)

    return {"session_id": session_id}


@router.get("/state")
async def get_state(
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> GameStateResponse:
    """Get current game state."""
    game = await _get_game(session_id)
    return _game_state_response(game)


@router.post("/bet")
async def place_bet(
    request: BetRequest,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> GameStateResponse:
    """Place a bet and deal cards."""
    game = await _get_game(session_id)

    if not game.bet(request.amount):
        raise HTTPException(status_code=400, detail="Invalid bet")

    await _save_game(session_id, game)
    return _game_state_response(game)


@router.post("/action")
async def player_action(
    request: ActionRequest,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> GameStateResponse:
    """Execute a player action."""
    game = await _get_game(session_id)

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

    await _save_game(session_id, game)
    return _game_state_response(game)
