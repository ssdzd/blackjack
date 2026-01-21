"""Progressive difficulty manager for training drills.

Automatically adjusts difficulty based on rolling accuracy,
making drills harder when the user is performing well and
easier when struggling.
"""

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


@dataclass
class DifficultyLevel:
    """Configuration for a specific difficulty level."""
    level: int
    name: str
    # Counting drill settings
    card_speed_ms: int  # Milliseconds per card
    # Strategy drill settings
    time_limit_sec: float  # 0 = no limit
    # Speed drill settings
    cards_per_sec: float
    # TC conversion settings
    deck_precision: float  # 1.0 = full decks, 0.5 = half decks, 0.25 = quarter
    rc_range: int  # Running count range (-rc to +rc)
    # Deviation drill settings
    tc_display_time_sec: float  # How long TC is shown prominently
    show_tc_hint: bool  # Whether to show TC during answer


# Predefined difficulty levels
DIFFICULTY_LEVELS: Dict[int, DifficultyLevel] = {
    1: DifficultyLevel(
        level=1,
        name="Beginner",
        card_speed_ms=2500,
        time_limit_sec=0,
        cards_per_sec=2.0,
        deck_precision=1.0,
        rc_range=10,
        tc_display_time_sec=5.0,
        show_tc_hint=True,
    ),
    2: DifficultyLevel(
        level=2,
        name="Easy",
        card_speed_ms=2000,
        time_limit_sec=10.0,
        cards_per_sec=2.5,
        deck_precision=1.0,
        rc_range=15,
        tc_display_time_sec=3.0,
        show_tc_hint=True,
    ),
    3: DifficultyLevel(
        level=3,
        name="Normal",
        card_speed_ms=1500,
        time_limit_sec=7.0,
        cards_per_sec=3.0,
        deck_precision=0.5,
        rc_range=20,
        tc_display_time_sec=2.0,
        show_tc_hint=True,
    ),
    4: DifficultyLevel(
        level=4,
        name="Hard",
        card_speed_ms=1000,
        time_limit_sec=5.0,
        cards_per_sec=3.5,
        deck_precision=0.5,
        rc_range=25,
        tc_display_time_sec=1.0,
        show_tc_hint=False,
    ),
    5: DifficultyLevel(
        level=5,
        name="Expert",
        card_speed_ms=400,
        time_limit_sec=3.0,
        cards_per_sec=4.0,
        deck_precision=0.25,
        rc_range=30,
        tc_display_time_sec=0.5,
        show_tc_hint=False,
    ),
}


class DifficultyManager:
    """Manages progressive difficulty based on performance.

    Tracks recent results in a sliding window and automatically
    adjusts difficulty level based on accuracy:
    - >= 90% accuracy: Level up (if not at max)
    - < 60% accuracy: Level down (if not at min)

    The manager provides drill-specific settings through the
    current DifficultyLevel configuration.
    """

    def __init__(
        self,
        window_size: int = 10,
        initial_level: int = 3,
        level_up_threshold: float = 0.90,
        level_down_threshold: float = 0.60,
        min_attempts_for_adjustment: int = 5,
    ):
        """Initialize the difficulty manager.

        Args:
            window_size: Number of recent results to track
            initial_level: Starting difficulty level (1-5)
            level_up_threshold: Accuracy to trigger level increase
            level_down_threshold: Accuracy to trigger level decrease
            min_attempts_for_adjustment: Minimum attempts before adjusting
        """
        self.window_size = window_size
        self.level_up_threshold = level_up_threshold
        self.level_down_threshold = level_down_threshold
        self.min_attempts_for_adjustment = min_attempts_for_adjustment

        self.recent_results: Deque[bool] = deque(maxlen=window_size)
        self._current_level = max(1, min(5, initial_level))

        # Track if we recently changed level (cooldown)
        self._change_cooldown = 0

    @property
    def current_level(self) -> int:
        """Get the current difficulty level (1-5)."""
        return self._current_level

    @current_level.setter
    def current_level(self, value: int) -> None:
        """Set the difficulty level with bounds checking."""
        self._current_level = max(1, min(5, value))
        self._change_cooldown = 3  # Cooldown after manual change

    @property
    def settings(self) -> DifficultyLevel:
        """Get the current difficulty settings."""
        return DIFFICULTY_LEVELS[self._current_level]

    @property
    def accuracy(self) -> float:
        """Get the current rolling accuracy (0.0 to 1.0)."""
        if not self.recent_results:
            return 0.0
        return sum(self.recent_results) / len(self.recent_results)

    @property
    def accuracy_percent(self) -> float:
        """Get the current rolling accuracy as percentage."""
        return self.accuracy * 100

    def record(self, correct: bool) -> Optional[str]:
        """Record a drill result and potentially adjust difficulty.

        Args:
            correct: Whether the answer was correct

        Returns:
            Message if difficulty changed ("Level Up!" or "Level Down"), else None
        """
        self.recent_results.append(correct)

        # Reduce cooldown
        if self._change_cooldown > 0:
            self._change_cooldown -= 1
            return None

        return self._adjust_difficulty()

    def _adjust_difficulty(self) -> Optional[str]:
        """Adjust difficulty based on recent performance.

        Returns:
            Message if difficulty changed, else None
        """
        if len(self.recent_results) < self.min_attempts_for_adjustment:
            return None

        accuracy = self.accuracy

        if accuracy >= self.level_up_threshold and self._current_level < 5:
            self._current_level += 1
            self._change_cooldown = 5  # Longer cooldown after auto-change
            self.recent_results.clear()  # Reset window after change
            return f"Level Up! Now at {self.settings.name}"

        elif accuracy < self.level_down_threshold and self._current_level > 1:
            self._current_level -= 1
            self._change_cooldown = 3
            self.recent_results.clear()
            return f"Level Down - Now at {self.settings.name}"

        return None

    def reset(self, level: int = 3) -> None:
        """Reset the manager to a specific level.

        Args:
            level: The level to reset to (1-5)
        """
        self._current_level = max(1, min(5, level))
        self.recent_results.clear()
        self._change_cooldown = 0

    def get_progress_to_next(self) -> float:
        """Get progress toward the next level (0.0 to 1.0).

        Returns:
            Progress percentage, or 1.0 if at max level
        """
        if self._current_level >= 5:
            return 1.0

        if len(self.recent_results) < self.min_attempts_for_adjustment:
            return 0.0

        # Map accuracy from threshold range to 0-1
        accuracy = self.accuracy
        range_size = self.level_up_threshold - self.level_down_threshold

        if accuracy <= self.level_down_threshold:
            return 0.0

        progress = (accuracy - self.level_down_threshold) / range_size
        return min(1.0, max(0.0, progress))

    def get_status_text(self) -> str:
        """Get a status string showing current level and accuracy.

        Returns:
            Formatted status string
        """
        level_name = self.settings.name
        accuracy = self.accuracy_percent

        if len(self.recent_results) < self.min_attempts_for_adjustment:
            return f"Level {self._current_level}: {level_name}"

        return f"Level {self._current_level}: {level_name} ({accuracy:.0f}%)"


# Factory functions for drill-specific managers

def create_counting_drill_manager() -> DifficultyManager:
    """Create a difficulty manager tuned for counting drills."""
    return DifficultyManager(
        window_size=10,
        initial_level=3,
        level_up_threshold=0.90,
        level_down_threshold=0.60,
    )


def create_strategy_drill_manager() -> DifficultyManager:
    """Create a difficulty manager tuned for strategy drills."""
    return DifficultyManager(
        window_size=15,
        initial_level=3,
        level_up_threshold=0.85,
        level_down_threshold=0.55,
    )


def create_speed_drill_manager() -> DifficultyManager:
    """Create a difficulty manager tuned for speed drills."""
    return DifficultyManager(
        window_size=5,
        initial_level=2,
        level_up_threshold=0.80,
        level_down_threshold=0.40,
    )


def create_deviation_drill_manager() -> DifficultyManager:
    """Create a difficulty manager tuned for deviation drills."""
    return DifficultyManager(
        window_size=10,
        initial_level=2,
        level_up_threshold=0.85,
        level_down_threshold=0.50,
    )


def create_tc_conversion_manager() -> DifficultyManager:
    """Create a difficulty manager tuned for TC conversion drills."""
    return DifficultyManager(
        window_size=8,
        initial_level=2,
        level_up_threshold=0.90,
        level_down_threshold=0.60,
    )


def create_deck_estimation_manager() -> DifficultyManager:
    """Create a difficulty manager tuned for deck estimation drills."""
    return DifficultyManager(
        window_size=10,
        initial_level=2,
        level_up_threshold=0.85,
        level_down_threshold=0.50,
    )
