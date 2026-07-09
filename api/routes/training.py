"""Training drill API endpoints."""

import time
import uuid
from random import Random
from fastapi import APIRouter, Header
from typing import Annotated

from api.schemas import (
    CountingDrillRequest,
    CountingDrillResponse,
    StrategyDrillRequest,
    StrategyDrillResponse,
    DeviationDrillRequest,
    DeviationDrillResponse,
    CountVerifyRequest,
    CountVerifyResponse,
    SpeedDrillRequest,
    SpeedDrillResponse,
    SpeedDrillVerifyRequest,
    SpeedDrillVerifyResponse,
    CardResponse,
)
from core.cards import Deck, Rank, Suit, Card
from core.counting import HiLoSystem, KOSystem, Omega2System, WongHalvesSystem
from core.strategy import BasicStrategy, Action
from core.strategy.deviations import find_deviation, ILLUSTRIOUS_18, FAB_4, IndexPlay

router = APIRouter()

# Session drill state storage
_drill_sessions: dict[str, dict] = {}
# Speed drill storage (separate for scoring)
_speed_drills: dict[str, dict] = {}
# True-count conversion drills
_tc_drills: dict[str, dict] = {}


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
    profile_id: Annotated[str | None, Header(alias="X-Profile-ID")] = None,
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
    correct = diff < 0.01  # Allow small floating point differences

    from api.progression_store import progress

    drill_key = (
        "counting" if session_data.get("system", "hilo") in ("hilo", "ko")
        else "counting-adv"
    )
    await progress(
        profile_id, "drill", {"drill_key": drill_key, "correct": correct}
    )

    return CountVerifyResponse(
        correct=correct,
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


@router.post("/counting/speed-drill")
async def speed_drill(
    request: SpeedDrillRequest,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> SpeedDrillResponse:
    """Generate a speed counting drill with timing."""
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

    # Generate unique drill ID
    drill_id = f"speed_{uuid.uuid4().hex[:12]}"

    # Store for verification with timestamp
    _speed_drills[drill_id] = {
        "correct_count": system.running_count,
        "system": request.system,
        "num_cards": request.num_cards,
        "card_speed_ms": request.card_speed_ms,
        "start_time": int(time.time() * 1000),
        "session_id": session_id,
    }

    return SpeedDrillResponse(
        drill_id=drill_id,
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
        card_speed_ms=request.card_speed_ms,
        num_cards=request.num_cards,
    )


@router.post("/counting/speed-drill/verify")
async def verify_speed_drill(
    request: SpeedDrillVerifyRequest,
    profile_id: Annotated[str | None, Header(alias="X-Profile-ID")] = None,
) -> SpeedDrillVerifyResponse:
    """Verify a speed drill result and calculate score."""
    drill_data = _speed_drills.get(request.drill_id)

    if drill_data is None:
        return SpeedDrillVerifyResponse(
            correct=False,
            actual_count=0,
            difference=abs(request.user_count),
            completion_time_ms=request.completion_time_ms,
            score=0,
            breakdown={"base": 0, "time_bonus": 0, "accuracy": 0},
        )

    actual = drill_data["correct_count"]
    diff = abs(request.user_count - actual)
    correct = diff < 0.01  # Allow small floating point differences

    # Calculate score
    # Base score: 100 points for correct answer
    base_score = 100 if correct else 0

    # Accuracy bonus: partial credit for close answers (up to 50 points)
    accuracy_bonus = 0
    if not correct and diff <= 2:
        accuracy_bonus = int(50 * (1 - diff / 2))

    # Time bonus: faster = more points (up to 50 points)
    # Expected time = num_cards * card_speed_ms + 2000ms buffer
    expected_time = drill_data["num_cards"] * drill_data["card_speed_ms"] + 2000
    time_bonus = 0
    if correct and request.completion_time_ms < expected_time:
        time_ratio = request.completion_time_ms / expected_time
        time_bonus = int(50 * (1 - time_ratio))

    total_score = base_score + accuracy_bonus + time_bonus

    # Clean up drill data after verification
    del _speed_drills[request.drill_id]

    from api.progression_store import progress

    await progress(
        profile_id,
        "drill",
        {
            "drill_key": "speed",
            "correct": correct,
            "num_cards": drill_data["num_cards"],
            "time_ms": request.completion_time_ms,
        },
    )

    return SpeedDrillVerifyResponse(
        correct=correct,
        actual_count=actual,
        difference=diff,
        completion_time_ms=request.completion_time_ms,
        score=total_score,
        breakdown={
            "base": base_score,
            "time_bonus": time_bonus,
            "accuracy": accuracy_bonus,
        },
    )


@router.post("/tc-conversion")
async def tc_conversion_drill() -> dict:
    """Generate a true-count conversion problem (stage 5 of the pedagogy)."""
    rng = Random()
    running_count = rng.choice([c for c in range(-18, 19) if c != 0])
    decks_remaining = rng.choice([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0])

    drill_id = str(uuid.uuid4())
    _tc_drills[drill_id] = {
        "running_count": running_count,
        "decks_remaining": decks_remaining,
        "created": time.time(),
    }
    # Opportunistic cleanup of stale drills
    if len(_tc_drills) > 500:
        cutoff = time.time() - 3600
        for key in [k for k, v in _tc_drills.items() if v["created"] < cutoff]:
            _tc_drills.pop(key, None)

    return {
        "drill_id": drill_id,
        "running_count": running_count,
        "decks_remaining": decks_remaining,
    }


@router.post("/tc-conversion/verify")
async def tc_conversion_verify(
    payload: dict,
    profile_id: Annotated[str | None, Header(alias="X-Profile-ID")] = None,
) -> dict:
    """Verify a true-count conversion answer.

    Convention: truncate toward zero (the conservative floor counters use),
    so RC +7 across 2 decks is TC +3, and RC -7 across 2 decks is TC -3.
    """
    drill = _tc_drills.pop(payload.get("drill_id", ""), None)
    if drill is None:
        return {"correct": False, "error": "Unknown or expired drill"}

    exact = drill["running_count"] / drill["decks_remaining"]
    expected = int(exact)  # truncates toward zero
    try:
        answer = int(payload.get("user_tc"))
    except (TypeError, ValueError):
        return {"correct": False, "error": "user_tc must be an integer"}

    correct = answer == expected

    from api.progression_store import progress

    await progress(
        profile_id, "drill", {"drill_key": "tc-conversion", "correct": correct}
    )

    return {
        "correct": correct,
        "expected": expected,
        "exact": round(exact, 2),
        "running_count": drill["running_count"],
        "decks_remaining": drill["decks_remaining"],
        "method_hint": (
            "Divide the running count by decks remaining and keep the "
            "integer part (truncate toward zero)."
        ),
    }


def _create_hand_for_deviation(deviation: IndexPlay, rng: Random) -> tuple[list[Card], Card]:
    """Create a hand that matches the deviation situation."""
    deck = Deck(rng=rng)
    deck.shuffle()

    # Find appropriate cards for the player hand
    player_cards = []

    if deviation.is_pair:
        # Need a pair - find the right value
        pair_value = deviation.player_total // 2
        if pair_value == 10:
            # 10,10 pair - use face cards or 10s
            ranks = [Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING]
            rank = rng.choice(ranks)
            suits = list(Suit)
            rng.shuffle(suits)
            player_cards = [Card(rank, suits[0]), Card(rank, suits[1])]
        else:
            rank = list(Rank)[pair_value - 1] if pair_value <= 10 else Rank.ACE
            suits = list(Suit)
            rng.shuffle(suits)
            player_cards = [Card(rank, suits[0]), Card(rank, suits[1])]
    else:
        # Non-pair hand
        total = deviation.player_total

        if deviation.is_soft:
            # Soft hand - need an Ace + another card
            other_value = total - 11
            other_rank = list(Rank)[other_value - 1] if other_value <= 10 else Rank.ACE
            suits = list(Suit)
            rng.shuffle(suits)
            player_cards = [Card(Rank.ACE, suits[0]), Card(other_rank, suits[1])]
        else:
            # Hard hand - find two cards that sum to total
            # Avoid creating pairs or soft hands
            if total <= 11:
                # Low total - use small cards
                card1_val = rng.randint(2, min(total - 2, 10))
                card2_val = total - card1_val
            else:
                # Higher total - need to be careful
                card1_val = rng.randint(max(2, total - 10), min(10, total - 2))
                card2_val = total - card1_val

            # Convert values to ranks
            ranks = []
            for val in [card1_val, card2_val]:
                if val == 10:
                    rank = rng.choice([Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING])
                elif val == 11:
                    rank = Rank.ACE
                else:
                    rank = list(Rank)[val - 1]
                ranks.append(rank)

            suits = list(Suit)
            rng.shuffle(suits)
            player_cards = [Card(ranks[0], suits[0]), Card(ranks[1], suits[1])]

    # Create dealer upcard
    if deviation.dealer_upcard == 11:
        dealer_rank = Rank.ACE
    elif deviation.dealer_upcard == 10:
        dealer_rank = rng.choice([Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING])
    else:
        dealer_rank = list(Rank)[deviation.dealer_upcard - 1]

    dealer_upcard = Card(dealer_rank, rng.choice(list(Suit)))

    return player_cards, dealer_upcard


@router.post("/strategy/deviation-drill")
async def deviation_drill(
    request: DeviationDrillRequest,
    session_id: Annotated[str, Header(alias="X-Session-ID")],
) -> DeviationDrillResponse:
    """Generate a deviation-focused drill (I18/Fab4 situations)."""
    rng = Random()

    # Build list of applicable deviations
    available_deviations = []
    for dev in ILLUSTRIOUS_18:
        # Skip insurance (player_total=0)
        if dev.player_total == 0:
            continue
        # Check if index is in our TC range
        if request.true_count_range_min <= dev.index <= request.true_count_range_max:
            available_deviations.append(dev)

    if request.include_fab4:
        for dev in FAB_4:
            if request.true_count_range_min <= dev.index <= request.true_count_range_max:
                available_deviations.append(dev)

    if not available_deviations:
        # Fallback to any deviation
        available_deviations = [d for d in ILLUSTRIOUS_18 if d.player_total > 0]

    # Pick a random deviation
    deviation = rng.choice(available_deviations)

    # Generate a true count that might or might not trigger the deviation
    # 50% chance it triggers, 50% it doesn't
    if rng.random() < 0.5:
        # TC that triggers deviation
        if deviation.direction == "at_or_above":
            tc = deviation.index + rng.randint(0, 3)
        else:
            tc = deviation.index - rng.randint(0, 3)
    else:
        # TC that doesn't trigger deviation
        if deviation.direction == "at_or_above":
            tc = deviation.index - rng.randint(1, 4)
        else:
            tc = deviation.index + rng.randint(1, 4)

    # Clamp to requested range
    tc = max(request.true_count_range_min, min(request.true_count_range_max, tc))

    # Create the hand
    player_cards, dealer_upcard = _create_hand_for_deviation(deviation, rng)

    # Determine correct action based on TC
    correct_action = deviation.get_action(tc)

    # Store for verification
    _drill_sessions[session_id] = {
        "type": "deviation",
        "correct_action": correct_action.name,
        "deviation": deviation.description,
        "true_count": tc,
    }

    return DeviationDrillResponse(
        player_cards=[
            CardResponse(rank=str(c.rank), suit=str(c.suit), value=c.value)
            for c in player_cards
        ],
        player_value=deviation.player_total,
        is_soft=deviation.is_soft,
        is_pair=deviation.is_pair,
        dealer_upcard=CardResponse(
            rank=str(dealer_upcard.rank),
            suit=str(dealer_upcard.suit),
            value=dealer_upcard.value,
        ),
        true_count=tc,
        index_threshold=deviation.index,
        basic_strategy_action=deviation.basic_action.name,
        deviation_action=deviation.deviation_action.name,
        correct_action=correct_action.name,
        deviation_name=deviation.description,
        direction=deviation.direction,
    )
