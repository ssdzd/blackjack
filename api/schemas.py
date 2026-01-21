"""Pydantic schemas for API requests and responses."""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
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

    model_config = ConfigDict(from_attributes=True)

    rank: str
    suit: str
    value: int


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


class DeviationDrillRequest(BaseModel):
    """Request for deviation-focused drill."""

    true_count_range_min: float = -5.0
    true_count_range_max: float = 10.0
    include_fab4: bool = True  # Include Fab 4 surrender deviations


class StrategyDrillResponse(BaseModel):
    """Strategy drill result."""

    player_cards: list[CardResponse]
    player_value: int
    is_soft: bool
    is_pair: bool
    dealer_upcard: CardResponse
    correct_action: str
    deviation: str | None = None


class DeviationDrillResponse(BaseModel):
    """Deviation drill result."""

    player_cards: list[CardResponse]
    player_value: int
    is_soft: bool
    is_pair: bool
    dealer_upcard: CardResponse
    true_count: float
    index_threshold: float
    basic_strategy_action: str
    deviation_action: str
    correct_action: str  # What player should do at this TC
    deviation_name: str
    direction: str  # "at_or_above" or "at_or_below"


class CountVerifyRequest(BaseModel):
    """Request to verify a count."""

    user_count: float
    session_id: str


class CountVerifyResponse(BaseModel):
    """Count verification result."""

    correct: bool
    actual_count: float
    difference: float


# Speed Drill schemas
class SpeedDrillRequest(BaseModel):
    """Request for speed drill."""

    system: Literal["hilo", "ko", "omega2", "wong_halves"] = "hilo"
    num_cards: int = Field(default=20, ge=5, le=52)
    card_speed_ms: int = Field(default=1000, ge=250, le=3000)


class SpeedDrillResponse(BaseModel):
    """Speed drill result."""

    drill_id: str
    cards: list[CardResponse]
    correct_count: float
    system: str
    card_speed_ms: int
    num_cards: int


class SpeedDrillVerifyRequest(BaseModel):
    """Request to verify speed drill result."""

    drill_id: str
    user_count: float
    completion_time_ms: int


class SpeedDrillVerifyResponse(BaseModel):
    """Speed drill verification result."""

    correct: bool
    actual_count: float
    difference: float
    completion_time_ms: int
    score: int
    breakdown: dict[str, int]  # {"base": 100, "time_bonus": 20, "accuracy": 50}


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


# Performance Tracking schemas
class SessionHistoryEntry(BaseModel):
    """Single entry in session history."""

    timestamp: int  # Unix timestamp in milliseconds
    bankroll: float
    running_count: int | None = None
    true_count: float | None = None
    event_type: str  # "hand_result", "drill_result", etc.
    details: dict | None = None


class PerformanceStats(BaseModel):
    """Comprehensive performance statistics."""

    # Game stats
    hands_played: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    blackjacks: int = 0
    total_wagered: float = 0.0
    net_result: float = 0.0

    # Counting drill stats
    count_drills_attempted: int = 0
    count_drills_correct: int = 0
    count_average_error: float = 0.0

    # Strategy drill stats
    strategy_drills_attempted: int = 0
    strategy_drills_correct: int = 0

    # Deviation drill stats
    deviation_drills_attempted: int = 0
    deviation_drills_correct: int = 0

    # Speed drill stats
    speed_drills_attempted: int = 0
    speed_drills_correct: int = 0
    speed_drill_best_score: int = 0
    speed_drill_best_time_ms: int | None = None

    # Session history for charts
    history: list[SessionHistoryEntry] = []


class RecordStatRequest(BaseModel):
    """Request to record a stat entry."""

    stat_type: Literal[
        "hand_win", "hand_loss", "hand_push", "hand_blackjack",
        "count_drill", "strategy_drill", "deviation_drill", "speed_drill"
    ]
    value: float | None = None  # For wager amounts or drill scores
    correct: bool | None = None  # For drill results
    details: dict | None = None  # Additional context


# Game State Persistence schemas
class CardData(BaseModel):
    """Serialized card data."""

    rank: int
    suit: int


class HandData(BaseModel):
    """Serialized hand data."""

    cards: list[CardData]
    bet: int
    is_doubled: bool = False
    is_split_hand: bool = False
    is_surrendered: bool = False


class RulesData(BaseModel):
    """Serialized rules data."""

    num_decks: int = 6
    min_bet: int = 10
    max_bet: int = 1000
    dealer_hits_soft_17: bool = True
    blackjack_payout: float = 1.5
    double_after_split: bool = True
    double_on: Literal["any", "9-11", "10-11"] = "any"
    resplit_aces: bool = False
    hit_split_aces: bool = False
    max_splits: int = 4
    surrender: Literal["none", "early", "late"] = "late"
    insurance_allowed: bool = True
    dealer_peeks: bool = True


class GameStateData(BaseModel):
    """Serialized game state for session storage."""

    state: str
    bankroll: str
    insurance_bet: str
    current_hand_index: int
    shoe_cards: list[CardData]
    shoe_num_decks: int
    shoe_penetration: float
    player_hands: list[HandData]
    dealer_hand: HandData
    rules: RulesData


class SessionData(BaseModel):
    """Complete session data structure."""

    game: GameStateData | None = None
    performance: PerformanceStats | None = None
    created_at: int
    last_activity: int
