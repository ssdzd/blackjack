"""Pydantic schemas for API requests and responses."""

from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Literal


# Game schemas
class BetRequest(BaseModel):
    """Request to place a bet."""

    amount: int = Field(..., ge=1, description="Bet amount")


class ActionRequest(BaseModel):
    """Request for player action."""

    action: Literal["hit", "stand", "double", "split", "surrender"]


class CardResponse(BaseModel):
    """Card representation."""

    rank: str
    suit: str
    value: int

    class Config:
        from_attributes = True


class HandResponse(BaseModel):
    """Hand representation."""

    cards: list[CardResponse]
    value: int
    is_soft: bool
    is_blackjack: bool
    is_busted: bool
    bet: int


class GameStateResponse(BaseModel):
    """Current game state."""

    state: str
    player_hands: list[HandResponse]
    current_hand_index: int
    dealer_hand: HandResponse
    dealer_showing: CardResponse | None
    bankroll: float
    can_hit: bool
    can_stand: bool
    can_double: bool
    can_split: bool
    can_surrender: bool


class RoundResultResponse(BaseModel):
    """Round result."""

    outcome: Literal["win", "lose", "push", "blackjack", "surrender"]
    amount: float
    new_bankroll: float


# Training schemas
class CountingDrillRequest(BaseModel):
    """Request for counting drill."""

    system: Literal["hilo", "ko", "omega2", "wong_halves"] = "hilo"
    num_cards: int = Field(default=20, ge=1, le=52)


class CountingDrillResponse(BaseModel):
    """Counting drill result."""

    cards: list[CardResponse]
    correct_count: float
    system: str


class StrategyDrillRequest(BaseModel):
    """Request for strategy drill."""

    include_deviations: bool = False
    true_count: float | None = None


class StrategyDrillResponse(BaseModel):
    """Strategy drill result."""

    player_cards: list[CardResponse]
    player_value: int
    is_soft: bool
    is_pair: bool
    dealer_upcard: CardResponse
    correct_action: str
    deviation: str | None = None


class CountVerifyRequest(BaseModel):
    """Request to verify a count."""

    user_count: float
    session_id: str


class CountVerifyResponse(BaseModel):
    """Count verification result."""

    correct: bool
    actual_count: float
    difference: float


# Statistics schemas
class HouseEdgeRequest(BaseModel):
    """Request for house edge calculation."""

    num_decks: int = Field(default=6, ge=1, le=8)
    dealer_hits_soft_17: bool = True
    blackjack_payout: float = 1.5
    double_after_split: bool = True
    surrender: Literal["none", "early", "late"] = "late"


class HouseEdgeResponse(BaseModel):
    """House edge calculation result."""

    house_edge_percent: float
    player_advantage_at_tc: dict[int, float]


class KellyBetRequest(BaseModel):
    """Request for Kelly bet calculation."""

    bankroll: float
    player_edge_percent: float
    kelly_fraction: float = Field(default=0.5, ge=0.1, le=1.0)


class KellyBetResponse(BaseModel):
    """Kelly bet calculation result."""

    optimal_bet: float
    bet_as_percent_of_bankroll: float


class SessionStatsResponse(BaseModel):
    """Session statistics."""

    hands_played: int
    win_rate: float
    total_wagered: float
    net_result: float
    counting_accuracy: float | None
    strategy_accuracy: float | None
