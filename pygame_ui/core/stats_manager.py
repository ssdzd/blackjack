"""Stats manager for tracking and persisting player performance data."""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class GameStats:
    """Statistics from game sessions."""
    hands_played: int = 0
    hands_won: int = 0
    hands_lost: int = 0
    hands_pushed: int = 0
    blackjacks: int = 0
    busts: int = 0
    doubles_won: int = 0
    doubles_lost: int = 0
    splits_played: int = 0
    surrenders: int = 0
    insurance_taken: int = 0
    insurance_won: int = 0
    net_result: float = 0.0  # Running profit/loss


@dataclass
class DrillStats:
    """Statistics from training drills."""
    counting_attempts: int = 0
    counting_correct: int = 0
    strategy_attempts: int = 0
    strategy_correct: int = 0
    speed_attempts: int = 0
    speed_high_score: int = 0
    speed_best_time: float = 0.0


@dataclass
class SessionStats:
    """Overall statistics."""
    total_sessions: int = 0
    total_play_time_minutes: float = 0.0
    first_session: str = ""  # ISO format date
    last_session: str = ""   # ISO format date
    game: GameStats = field(default_factory=GameStats)
    drills: DrillStats = field(default_factory=DrillStats)


class StatsManager:
    """Manages player statistics with local file persistence.

    Statistics are saved to a JSON file and loaded on startup.
    """

    def __init__(self, stats_file: str = None):
        """Initialize the stats manager.

        Args:
            stats_file: Path to stats file. Defaults to ~/.blackjack_trainer_stats.json
        """
        if stats_file is None:
            home = os.path.expanduser("~")
            stats_file = os.path.join(home, ".blackjack_trainer_stats.json")

        self.stats_file = stats_file
        self.stats = SessionStats()
        self._load()

    def _load(self) -> None:
        """Load stats from file."""
        if not os.path.exists(self.stats_file):
            return

        try:
            with open(self.stats_file, 'r') as f:
                data = json.load(f)

            # Reconstruct dataclasses from dict
            game_data = data.get("game", {})
            drill_data = data.get("drills", {})

            self.stats = SessionStats(
                total_sessions=data.get("total_sessions", 0),
                total_play_time_minutes=data.get("total_play_time_minutes", 0.0),
                first_session=data.get("first_session", ""),
                last_session=data.get("last_session", ""),
                game=GameStats(**game_data),
                drills=DrillStats(**drill_data),
            )
        except (json.JSONDecodeError, TypeError, KeyError):
            # If file is corrupted, start fresh
            self.stats = SessionStats()

    def save(self) -> None:
        """Save stats to file."""
        try:
            data = {
                "total_sessions": self.stats.total_sessions,
                "total_play_time_minutes": self.stats.total_play_time_minutes,
                "first_session": self.stats.first_session,
                "last_session": self.stats.last_session,
                "game": asdict(self.stats.game),
                "drills": asdict(self.stats.drills),
            }

            with open(self.stats_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError:
            pass  # Silently fail if can't write

    def start_session(self) -> None:
        """Mark the start of a new session."""
        self.stats.total_sessions += 1
        now = datetime.now().isoformat()

        if not self.stats.first_session:
            self.stats.first_session = now
        self.stats.last_session = now

        self.save()

    def add_play_time(self, minutes: float) -> None:
        """Add to total play time."""
        self.stats.total_play_time_minutes += minutes
        self.save()

    # Game stat updates

    def record_hand_result(
        self,
        won: bool,
        pushed: bool = False,
        is_blackjack: bool = False,
        is_bust: bool = False,
        is_double: bool = False,
        is_surrender: bool = False,
        amount: float = 0.0,
    ) -> None:
        """Record the result of a hand.

        Args:
            won: Whether the player won
            pushed: Whether the hand was a push
            is_blackjack: Whether it was a blackjack win
            is_bust: Whether the player busted
            is_double: Whether it was a doubled hand
            is_surrender: Whether player surrendered
            amount: Net gain/loss for the hand
        """
        self.stats.game.hands_played += 1
        self.stats.game.net_result += amount

        if is_surrender:
            self.stats.game.surrenders += 1
        elif pushed:
            self.stats.game.hands_pushed += 1
        elif won:
            self.stats.game.hands_won += 1
            if is_blackjack:
                self.stats.game.blackjacks += 1
            if is_double:
                self.stats.game.doubles_won += 1
        else:
            self.stats.game.hands_lost += 1
            if is_bust:
                self.stats.game.busts += 1
            if is_double:
                self.stats.game.doubles_lost += 1

        self.save()

    def record_split(self) -> None:
        """Record a split hand."""
        self.stats.game.splits_played += 1
        self.save()

    def record_insurance(self, won: bool) -> None:
        """Record insurance taken.

        Args:
            won: Whether insurance paid off
        """
        self.stats.game.insurance_taken += 1
        if won:
            self.stats.game.insurance_won += 1
        self.save()

    # Drill stat updates

    def record_counting_drill(self, correct: bool) -> None:
        """Record a counting drill result.

        Args:
            correct: Whether the count was correct
        """
        self.stats.drills.counting_attempts += 1
        if correct:
            self.stats.drills.counting_correct += 1
        self.save()

    def record_strategy_drill(self, correct: bool) -> None:
        """Record a strategy drill result.

        Args:
            correct: Whether the strategy was correct
        """
        self.stats.drills.strategy_attempts += 1
        if correct:
            self.stats.drills.strategy_correct += 1
        self.save()

    def record_speed_drill(self, score: int, time: float) -> None:
        """Record a speed drill result.

        Args:
            score: The achieved score
            time: The completion time
        """
        self.stats.drills.speed_attempts += 1
        if score > self.stats.drills.speed_high_score:
            self.stats.drills.speed_high_score = score
        if self.stats.drills.speed_best_time == 0 or time < self.stats.drills.speed_best_time:
            self.stats.drills.speed_best_time = time
        self.save()

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.stats = SessionStats()
        self.save()

    # Computed properties

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        decided = self.stats.game.hands_won + self.stats.game.hands_lost
        if decided == 0:
            return 0.0
        return (self.stats.game.hands_won / decided) * 100

    @property
    def counting_accuracy(self) -> float:
        """Calculate counting drill accuracy."""
        if self.stats.drills.counting_attempts == 0:
            return 0.0
        return (self.stats.drills.counting_correct / self.stats.drills.counting_attempts) * 100

    @property
    def strategy_accuracy(self) -> float:
        """Calculate strategy drill accuracy."""
        if self.stats.drills.strategy_attempts == 0:
            return 0.0
        return (self.stats.drills.strategy_correct / self.stats.drills.strategy_attempts) * 100


# Global singleton
_stats_manager: Optional[StatsManager] = None


def get_stats_manager() -> StatsManager:
    """Get the global stats manager instance."""
    global _stats_manager
    if _stats_manager is None:
        _stats_manager = StatsManager()
    return _stats_manager
