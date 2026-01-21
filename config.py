"""Configuration management with environment variable support."""

import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class RedisConfig:
    """Redis connection configuration."""

    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    password: str | None = field(default_factory=lambda: os.getenv("REDIS_PASSWORD"))

    @property
    def url(self) -> str:
        """Build Redis connection URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


@dataclass(frozen=True)
class GameConfig:
    """Default game configuration."""

    num_decks: int = 6
    penetration: float = 0.75
    min_bet: int = 10
    max_bet: int = 1000
    blackjack_payout: float = 1.5
    dealer_hits_soft_17: bool = True
    double_after_split: bool = True
    resplit_aces: bool = False
    surrender_allowed: Literal["none", "early", "late"] = "late"
    max_splits: int = 4


@dataclass(frozen=True)
class AppConfig:
    """Application configuration."""

    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    session_ttl: int = 3600  # Session timeout in seconds

    redis: RedisConfig = field(default_factory=RedisConfig)
    game: GameConfig = field(default_factory=GameConfig)


# Global configuration instance
config = AppConfig()
