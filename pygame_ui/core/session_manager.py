"""Session manager for tracking bankroll goals and limits."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, List

from pygame_ui.core.game_settings import get_settings_manager, SessionGoals


class SessionStatus(Enum):
    """Current session status relative to goals."""

    ACTIVE = "active"
    WIN_GOAL_REACHED = "win_goal_reached"
    LOSS_LIMIT_REACHED = "loss_limit_reached"
    APPROACHING_WIN = "approaching_win"  # Within 20%
    APPROACHING_LOSS = "approaching_loss"  # Within 20%


@dataclass
class SessionState:
    """Current session state."""

    initial_bankroll: float
    current_bankroll: float
    hands_played: int = 0
    hands_won: int = 0
    hands_lost: int = 0
    hands_pushed: int = 0
    peak_bankroll: float = 0
    low_bankroll: float = 0

    @property
    def profit_loss(self) -> float:
        """Current profit/loss for session."""
        return self.current_bankroll - self.initial_bankroll

    @property
    def win_rate(self) -> float:
        """Win rate percentage."""
        total = self.hands_won + self.hands_lost
        if total == 0:
            return 0.0
        return self.hands_won / total * 100

    def __post_init__(self):
        if self.peak_bankroll == 0:
            self.peak_bankroll = self.initial_bankroll
        if self.low_bankroll == 0:
            self.low_bankroll = self.initial_bankroll


class SessionManager:
    """Manages session state and goal tracking."""

    def __init__(self):
        self._state: Optional[SessionState] = None
        self._goals: Optional[SessionGoals] = None
        self._callbacks: List[Callable[[SessionStatus], None]] = []

    @property
    def is_active(self) -> bool:
        """Check if a session is active."""
        return self._state is not None

    @property
    def state(self) -> Optional[SessionState]:
        """Get current session state."""
        return self._state

    @property
    def goals(self) -> SessionGoals:
        """Get session goals (from settings or default)."""
        if self._goals is None:
            self._goals = get_settings_manager().session_goals
        return self._goals

    def start_session(self, initial_bankroll: float, goals: Optional[SessionGoals] = None) -> None:
        """Start a new session.

        Args:
            initial_bankroll: Starting bankroll
            goals: Optional session goals (uses saved settings if None)
        """
        self._state = SessionState(
            initial_bankroll=initial_bankroll,
            current_bankroll=initial_bankroll,
        )
        if goals is not None:
            self._goals = goals

    def end_session(self) -> Optional[SessionState]:
        """End the current session and return final state."""
        state = self._state
        self._state = None
        return state

    def update_bankroll(self, new_bankroll: float) -> SessionStatus:
        """Update bankroll and check against goals.

        Args:
            new_bankroll: Updated bankroll value

        Returns:
            Current session status
        """
        if self._state is None:
            return SessionStatus.ACTIVE

        self._state.current_bankroll = new_bankroll
        self._state.peak_bankroll = max(self._state.peak_bankroll, new_bankroll)
        self._state.low_bankroll = min(self._state.low_bankroll, new_bankroll)

        status = self._check_status()

        # Notify callbacks
        for callback in self._callbacks:
            callback(status)

        return status

    def record_hand(self, won: bool, pushed: bool = False) -> None:
        """Record a hand result."""
        if self._state is None:
            return

        self._state.hands_played += 1
        if pushed:
            self._state.hands_pushed += 1
        elif won:
            self._state.hands_won += 1
        else:
            self._state.hands_lost += 1

    def _check_status(self) -> SessionStatus:
        """Check current status against goals."""
        if self._state is None:
            return SessionStatus.ACTIVE

        profit = self._state.profit_loss
        goals = self.goals

        # Check win goal
        if goals.win_goal > 0:
            if profit >= goals.win_goal:
                return SessionStatus.WIN_GOAL_REACHED
            elif profit >= goals.win_goal * 0.8:
                return SessionStatus.APPROACHING_WIN

        # Check loss limit
        if goals.loss_limit > 0:
            if profit <= -goals.loss_limit:
                return SessionStatus.LOSS_LIMIT_REACHED
            elif profit <= -goals.loss_limit * 0.8:
                return SessionStatus.APPROACHING_LOSS

        return SessionStatus.ACTIVE

    def get_progress(self) -> tuple[float, float]:
        """Get progress toward goals as percentages.

        Returns:
            (win_progress, loss_progress) as 0-1 values
        """
        if self._state is None:
            return (0.0, 0.0)

        profit = self._state.profit_loss
        goals = self.goals

        win_progress = 0.0
        loss_progress = 0.0

        if goals.win_goal > 0 and profit > 0:
            win_progress = min(1.0, profit / goals.win_goal)

        if goals.loss_limit > 0 and profit < 0:
            loss_progress = min(1.0, abs(profit) / goals.loss_limit)

        return (win_progress, loss_progress)

    def add_callback(self, callback: Callable[[SessionStatus], None]) -> None:
        """Add a callback for status changes."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[SessionStatus], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def should_auto_stop(self) -> bool:
        """Check if session should auto-stop based on goals."""
        if not self.goals.auto_stop:
            return False

        status = self._check_status()
        return status in (SessionStatus.WIN_GOAL_REACHED, SessionStatus.LOSS_LIMIT_REACHED)


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the singleton session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
