"""Configuration management with environment variable support."""

import os
import secrets
from dataclasses import dataclass, field
from typing import Literal


def _parse_cors_origins() -> list[str]:
    """Parse CORS_ORIGINS environment variable."""
    origins = os.getenv("CORS_ORIGINS", "http://localhost:8000")
    return [o.strip() for o in origins.split(",") if o.strip()]


@dataclass(frozen=True)
class CORSConfig:
    """CORS configuration."""

    allowed_origins: list[str] = field(default_factory=_parse_cors_origins)
    allow_credentials: bool = True
    allow_methods: list[str] = field(default_factory=lambda: ["*"])
    allow_headers: list[str] = field(default_factory=lambda: ["*"])


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limiting configuration."""

    enabled: bool = field(
        default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    )
    requests_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_RPM", "60"))
    )


@dataclass(frozen=True)
class SecurityConfig:
    """Security configuration."""

    secret_key: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    )


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
    cors: CORSConfig = field(default_factory=CORSConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)


# Global configuration instance
config = AppConfig()
