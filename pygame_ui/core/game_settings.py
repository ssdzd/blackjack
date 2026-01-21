"""Game settings manager for table rules and preferences."""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional


@dataclass
class TableRules:
    """Table rules configuration (matches core.strategy.rules.RuleSet)."""

    # Deck configuration
    num_decks: int = 6
    penetration: float = 0.75  # 75% of shoe dealt before shuffle

    # Dealer rules
    dealer_hits_soft_17: bool = True  # H17 vs S17

    # Blackjack payout (3:2 = 1.5, 6:5 = 1.2)
    blackjack_payout: float = 1.5

    # Double down rules
    double_after_split: bool = True  # DAS
    double_on: Literal["any", "9-11", "10-11"] = "any"

    # Split rules
    resplit_aces: bool = False  # RSA
    max_splits: int = 4

    # Surrender rules
    surrender: Literal["none", "early", "late"] = "late"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TableRules":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SessionGoals:
    """Session bankroll goals."""

    win_goal: int = 0  # 0 = disabled
    loss_limit: int = 0  # 0 = disabled
    auto_stop: bool = False  # Auto-stop when limit reached

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionGoals":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class GameSettings:
    """All game settings combined."""

    table_rules: TableRules = field(default_factory=TableRules)
    session_goals: SessionGoals = field(default_factory=SessionGoals)
    num_hands: int = 1  # Multi-hand mode: 1-3 hands

    def to_dict(self) -> dict:
        return {
            "table_rules": self.table_rules.to_dict(),
            "session_goals": self.session_goals.to_dict(),
            "num_hands": self.num_hands,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameSettings":
        return cls(
            table_rules=TableRules.from_dict(data.get("table_rules", {})),
            session_goals=SessionGoals.from_dict(data.get("session_goals", {})),
            num_hands=data.get("num_hands", 1),
        )


class GameSettingsManager:
    """Manager for game settings persistence."""

    DEFAULT_PATH = os.path.expanduser("~/.blackjack_trainer_settings.json")

    def __init__(self, path: Optional[str] = None):
        self.path = path or self.DEFAULT_PATH
        self._settings: Optional[GameSettings] = None

    @property
    def settings(self) -> GameSettings:
        """Get current settings, loading from disk if needed."""
        if self._settings is None:
            self._settings = self._load()
        return self._settings

    def _load(self) -> GameSettings:
        """Load settings from disk."""
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    data = json.load(f)
                return GameSettings.from_dict(data)
        except (json.JSONDecodeError, IOError, KeyError):
            pass
        return GameSettings()

    def save(self) -> None:
        """Save settings to disk."""
        if self._settings is None:
            return
        try:
            with open(self.path, "w") as f:
                json.dump(self._settings.to_dict(), f, indent=2)
        except IOError:
            pass

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self._settings = GameSettings()
        self.save()

    # Convenience accessors
    @property
    def table_rules(self) -> TableRules:
        return self.settings.table_rules

    @property
    def session_goals(self) -> SessionGoals:
        return self.settings.session_goals

    @property
    def num_hands(self) -> int:
        return self.settings.num_hands

    @num_hands.setter
    def num_hands(self, value: int) -> None:
        self.settings.num_hands = max(1, min(3, value))
        self.save()


# Singleton instance
_settings_manager: Optional[GameSettingsManager] = None


def get_settings_manager() -> GameSettingsManager:
    """Get the singleton settings manager."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = GameSettingsManager()
    return _settings_manager
