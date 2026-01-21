"""Hand history logger for tracking every hand played."""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class DecisionType(Enum):
    """Types of player decisions."""
    HIT = "hit"
    STAND = "stand"
    DOUBLE = "double"
    SPLIT = "split"
    SURRENDER = "surrender"
    INSURANCE_YES = "insurance_yes"
    INSURANCE_NO = "insurance_no"


class HandOutcome(Enum):
    """Hand outcomes."""
    WIN = "win"
    LOSE = "lose"
    PUSH = "push"
    BLACKJACK = "blackjack"
    BUST = "bust"
    SURRENDER = "surrender"


@dataclass
class Decision:
    """A single decision made during a hand."""

    action: str  # DecisionType value
    player_total: int
    is_soft: bool
    is_pair: bool
    dealer_upcard: int
    running_count: int
    true_count: float
    correct_action: str  # What basic strategy says
    is_correct: bool
    is_deviation: bool = False  # Was this a deviation situation
    deviation_index: Optional[float] = None  # Index for deviation
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class HandRecord:
    """Complete record of a single hand."""

    id: str = ""
    timestamp: str = ""

    # Cards
    player_cards: List[str] = field(default_factory=list)
    dealer_cards: List[str] = field(default_factory=list)
    dealer_upcard: str = ""

    # Values
    player_final_value: int = 0
    dealer_final_value: int = 0

    # Betting
    initial_bet: int = 0
    final_bet: int = 0  # After doubles/splits

    # Count at start of hand
    running_count: int = 0
    true_count: float = 0.0

    # Decisions made
    decisions: List[Dict[str, Any]] = field(default_factory=list)

    # Outcome
    outcome: str = ""  # HandOutcome value
    profit_loss: float = 0.0

    # Analysis
    mistakes: List[Dict[str, Any]] = field(default_factory=list)
    was_split_hand: bool = False
    was_doubled: bool = False
    took_insurance: bool = False
    insurance_won: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def add_decision(self, decision: Decision) -> None:
        """Add a decision to this hand."""
        self.decisions.append(asdict(decision))
        if not decision.is_correct:
            self.mistakes.append({
                "action": decision.action,
                "correct_action": decision.correct_action,
                "player_total": decision.player_total,
                "dealer_upcard": decision.dealer_upcard,
                "is_soft": decision.is_soft,
                "is_pair": decision.is_pair,
                "true_count": decision.true_count,
                "is_deviation": decision.is_deviation,
            })

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandRecord":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MistakeStats:
    """Statistics about a specific type of mistake."""

    situation: str  # e.g., "16 vs 10"
    correct_action: str
    wrong_action: str
    count: int = 0
    is_deviation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HandLogger:
    """Logs and manages hand history."""

    DEFAULT_PATH = os.path.expanduser("~/.blackjack_trainer_history.json")
    MAX_HANDS = 1000  # Keep last N hands

    def __init__(self, path: Optional[str] = None):
        self.path = path or self.DEFAULT_PATH
        self._history: List[HandRecord] = []
        self._current_hand: Optional[HandRecord] = None
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure history is loaded from disk."""
        if not self._loaded:
            self._load()
            self._loaded = True

    def _load(self) -> None:
        """Load history from disk."""
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    data = json.load(f)
                self._history = [HandRecord.from_dict(h) for h in data.get("hands", [])]
        except (json.JSONDecodeError, IOError, KeyError):
            self._history = []

    def _save(self) -> None:
        """Save history to disk."""
        try:
            # Trim to max hands
            if len(self._history) > self.MAX_HANDS:
                self._history = self._history[-self.MAX_HANDS:]

            data = {
                "version": 1,
                "hands": [h.to_dict() for h in self._history],
            }
            with open(self.path, "w") as f:
                json.dump(data, f, indent=2)
        except IOError:
            pass

    def start_hand(
        self,
        initial_bet: int,
        running_count: int,
        true_count: float,
    ) -> HandRecord:
        """Start recording a new hand."""
        self._ensure_loaded()
        self._current_hand = HandRecord(
            initial_bet=initial_bet,
            final_bet=initial_bet,
            running_count=running_count,
            true_count=true_count,
        )
        return self._current_hand

    def add_player_card(self, card: str) -> None:
        """Add a card to the player's hand."""
        if self._current_hand:
            self._current_hand.player_cards.append(card)

    def add_dealer_card(self, card: str, is_upcard: bool = False) -> None:
        """Add a card to the dealer's hand."""
        if self._current_hand:
            self._current_hand.dealer_cards.append(card)
            if is_upcard:
                self._current_hand.dealer_upcard = card

    def record_decision(self, decision: Decision) -> None:
        """Record a decision made during the hand."""
        if self._current_hand:
            self._current_hand.add_decision(decision)

    def set_doubled(self, new_bet: int) -> None:
        """Mark that the hand was doubled."""
        if self._current_hand:
            self._current_hand.was_doubled = True
            self._current_hand.final_bet = new_bet

    def set_split(self) -> None:
        """Mark that the hand was split."""
        if self._current_hand:
            self._current_hand.was_split_hand = True

    def set_insurance(self, taken: bool, won: bool = False) -> None:
        """Record insurance decision."""
        if self._current_hand:
            self._current_hand.took_insurance = taken
            self._current_hand.insurance_won = won

    def end_hand(
        self,
        outcome: HandOutcome,
        player_value: int,
        dealer_value: int,
        profit_loss: float,
    ) -> None:
        """End the current hand and save it."""
        if self._current_hand:
            self._current_hand.outcome = outcome.value
            self._current_hand.player_final_value = player_value
            self._current_hand.dealer_final_value = dealer_value
            self._current_hand.profit_loss = profit_loss

            self._history.append(self._current_hand)
            self._save()
            self._current_hand = None

    def cancel_hand(self) -> None:
        """Cancel the current hand without saving."""
        self._current_hand = None

    @property
    def current_hand(self) -> Optional[HandRecord]:
        """Get the current hand being recorded."""
        return self._current_hand

    @property
    def history(self) -> List[HandRecord]:
        """Get all recorded hands."""
        self._ensure_loaded()
        return self._history

    def get_recent_hands(self, count: int = 50) -> List[HandRecord]:
        """Get the most recent N hands."""
        self._ensure_loaded()
        return self._history[-count:]

    def get_hands_by_date(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[HandRecord]:
        """Get hands within a date range."""
        self._ensure_loaded()
        hands = []
        for hand in self._history:
            try:
                hand_date = datetime.fromisoformat(hand.timestamp)
                if start_date and hand_date < start_date:
                    continue
                if end_date and hand_date > end_date:
                    continue
                hands.append(hand)
            except ValueError:
                continue
        return hands

    def get_hands_by_outcome(self, outcome: HandOutcome) -> List[HandRecord]:
        """Get hands with a specific outcome."""
        self._ensure_loaded()
        return [h for h in self._history if h.outcome == outcome.value]

    def get_hands_with_mistakes(self) -> List[HandRecord]:
        """Get hands where mistakes were made."""
        self._ensure_loaded()
        return [h for h in self._history if len(h.mistakes) > 0]

    def get_mistake_breakdown(self) -> Dict[str, MistakeStats]:
        """Analyze all mistakes and return breakdown."""
        self._ensure_loaded()
        mistakes: Dict[str, MistakeStats] = {}

        for hand in self._history:
            for mistake in hand.mistakes:
                # Create unique key for this mistake type
                is_soft = mistake.get("is_soft", False)
                is_pair = mistake.get("is_pair", False)
                player_total = mistake.get("player_total", 0)
                dealer_upcard = mistake.get("dealer_upcard", 0)

                if is_pair:
                    situation = f"Pair {player_total // 2} vs {dealer_upcard}"
                elif is_soft:
                    situation = f"Soft {player_total} vs {dealer_upcard}"
                else:
                    situation = f"Hard {player_total} vs {dealer_upcard}"

                key = f"{situation}_{mistake.get('correct_action', '')}"

                if key not in mistakes:
                    mistakes[key] = MistakeStats(
                        situation=situation,
                        correct_action=mistake.get("correct_action", ""),
                        wrong_action=mistake.get("action", ""),
                        is_deviation=mistake.get("is_deviation", False),
                    )
                mistakes[key].count += 1

        return mistakes

    def get_strategy_accuracy(self) -> Dict[str, Dict[str, Any]]:
        """Calculate accuracy for each strategy situation.

        Returns dict mapping "player_total,dealer_upcard,is_soft,is_pair" to accuracy stats.
        """
        self._ensure_loaded()
        stats: Dict[str, Dict[str, Any]] = {}

        for hand in self._history:
            for decision in hand.decisions:
                player_total = decision.get("player_total", 0)
                dealer_upcard = decision.get("dealer_upcard", 0)
                is_soft = decision.get("is_soft", False)
                is_pair = decision.get("is_pair", False)
                is_correct = decision.get("is_correct", True)

                key = f"{player_total},{dealer_upcard},{is_soft},{is_pair}"

                if key not in stats:
                    stats[key] = {
                        "player_total": player_total,
                        "dealer_upcard": dealer_upcard,
                        "is_soft": is_soft,
                        "is_pair": is_pair,
                        "correct": 0,
                        "incorrect": 0,
                    }

                if is_correct:
                    stats[key]["correct"] += 1
                else:
                    stats[key]["incorrect"] += 1

        # Calculate accuracy
        for key, s in stats.items():
            total = s["correct"] + s["incorrect"]
            s["accuracy"] = s["correct"] / total if total > 0 else 1.0
            s["total"] = total

        return stats

    def get_session_summary(self, session_start: datetime) -> Dict[str, Any]:
        """Get summary stats for hands since session_start."""
        hands = self.get_hands_by_date(start_date=session_start)

        if not hands:
            return {
                "hands_played": 0,
                "wins": 0,
                "losses": 0,
                "pushes": 0,
                "blackjacks": 0,
                "total_profit": 0.0,
                "mistakes": 0,
                "accuracy": 1.0,
            }

        wins = sum(1 for h in hands if h.outcome in ("win", "blackjack"))
        losses = sum(1 for h in hands if h.outcome in ("lose", "bust"))
        pushes = sum(1 for h in hands if h.outcome == "push")
        blackjacks = sum(1 for h in hands if h.outcome == "blackjack")
        profit = sum(h.profit_loss for h in hands)

        total_decisions = sum(len(h.decisions) for h in hands)
        total_mistakes = sum(len(h.mistakes) for h in hands)
        accuracy = (total_decisions - total_mistakes) / total_decisions if total_decisions > 0 else 1.0

        return {
            "hands_played": len(hands),
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "blackjacks": blackjacks,
            "total_profit": profit,
            "mistakes": total_mistakes,
            "accuracy": accuracy,
        }

    def clear_history(self) -> None:
        """Clear all hand history."""
        self._history = []
        self._save()


# Singleton instance
_hand_logger: Optional[HandLogger] = None


def get_hand_logger() -> HandLogger:
    """Get the singleton hand logger."""
    global _hand_logger
    if _hand_logger is None:
        _hand_logger = HandLogger()
    return _hand_logger
