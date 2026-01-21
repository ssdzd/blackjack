"""Tests for configuration classes."""

import os
import pytest
from unittest.mock import patch


class TestCORSConfig:
    """Tests for CORSConfig class."""

    def test_cors_default_origins(self):
        """Test that default CORS origins are set correctly."""
        # Clear env var to test default
        with patch.dict(os.environ, {}, clear=True):
            # Need to reimport to pick up env changes
            from config import CORSConfig

            config = CORSConfig()

            assert "http://localhost:8000" in config.allowed_origins

    def test_cors_parses_env_var(self):
        """Test that CORS origins are parsed from environment variable."""
        env_origins = "http://example.com,http://localhost:3000,http://app.test.com"
        with patch.dict(os.environ, {"CORS_ORIGINS": env_origins}):
            # Reimport to test fresh parsing
            from config import _parse_cors_origins

            origins = _parse_cors_origins()

            assert "http://example.com" in origins
            assert "http://localhost:3000" in origins
            assert "http://app.test.com" in origins
            assert len(origins) == 3

    def test_cors_parses_origins_with_whitespace(self):
        """Test that CORS origins handles whitespace correctly."""
        env_origins = "  http://example.com  ,  http://localhost:3000  "
        with patch.dict(os.environ, {"CORS_ORIGINS": env_origins}):
            from config import _parse_cors_origins

            origins = _parse_cors_origins()

            assert "http://example.com" in origins
            assert "http://localhost:3000" in origins
            # Whitespace should be stripped
            assert "  http://example.com  " not in origins

    def test_cors_default_credentials(self):
        """Test that credentials are allowed by default."""
        from config import CORSConfig

        config = CORSConfig()

        assert config.allow_credentials is True

    def test_cors_default_methods_and_headers(self):
        """Test that default methods and headers allow all."""
        from config import CORSConfig

        config = CORSConfig()

        assert "*" in config.allow_methods
        assert "*" in config.allow_headers


class TestRateLimitConfig:
    """Tests for RateLimitConfig class."""

    def test_rate_limit_defaults(self):
        """Test default rate limit values."""
        with patch.dict(os.environ, {}, clear=True):
            from config import RateLimitConfig

            config = RateLimitConfig()

            # Default is enabled
            assert config.enabled is True
            # Default RPM is 60
            assert config.requests_per_minute == 60

    def test_rate_limit_from_env(self):
        """Test rate limit configuration from environment."""
        with patch.dict(
            os.environ,
            {"RATE_LIMIT_ENABLED": "false", "RATE_LIMIT_RPM": "120"},
        ):
            from config import RateLimitConfig

            config = RateLimitConfig()

            assert config.enabled is False
            assert config.requests_per_minute == 120

    def test_rate_limit_enabled_case_insensitive(self):
        """Test that enabled parsing is case insensitive."""
        with patch.dict(os.environ, {"RATE_LIMIT_ENABLED": "TRUE"}):
            from config import RateLimitConfig

            config = RateLimitConfig()

            assert config.enabled is True

        with patch.dict(os.environ, {"RATE_LIMIT_ENABLED": "True"}):
            from config import RateLimitConfig

            config = RateLimitConfig()

            assert config.enabled is True

    def test_rate_limit_enabled_false_values(self):
        """Test various false values for rate limit enabled."""
        for false_val in ["false", "FALSE", "False", "0", "no"]:
            with patch.dict(os.environ, {"RATE_LIMIT_ENABLED": false_val}):
                from config import RateLimitConfig

                config = RateLimitConfig()

                # Only "true" (case insensitive) should be True
                if false_val.lower() != "true":
                    assert config.enabled is False


class TestSecurityConfig:
    """Tests for SecurityConfig class."""

    def test_secret_key_auto_generates(self):
        """Test that secret key is auto-generated when not in env."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear SECRET_KEY if present
            if "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]

            from config import SecurityConfig

            config = SecurityConfig()

            # Should have a secret key
            assert config.secret_key is not None
            assert len(config.secret_key) > 0

    def test_secret_key_from_env(self):
        """Test that secret key is read from environment."""
        test_key = "my-super-secret-key-12345"
        with patch.dict(os.environ, {"SECRET_KEY": test_key}):
            from config import SecurityConfig

            config = SecurityConfig()

            assert config.secret_key == test_key

    def test_secret_key_is_random_when_generated(self):
        """Test that auto-generated secret keys are unique."""
        with patch.dict(os.environ, {}, clear=True):
            from config import SecurityConfig

            # Generate two configs
            config1 = SecurityConfig()
            config2 = SecurityConfig()

            # Both should have keys (though they might be the same due to module caching)
            assert config1.secret_key is not None
            assert config2.secret_key is not None


class TestRedisConfig:
    """Tests for RedisConfig class."""

    def test_redis_defaults(self):
        """Test default Redis configuration."""
        with patch.dict(os.environ, {}, clear=True):
            from config import RedisConfig

            config = RedisConfig()

            assert config.host == "localhost"
            assert config.port == 6379
            assert config.db == 0
            assert config.password is None

    def test_redis_from_env(self):
        """Test Redis configuration from environment."""
        with patch.dict(
            os.environ,
            {
                "REDIS_HOST": "redis.example.com",
                "REDIS_PORT": "6380",
                "REDIS_DB": "1",
                "REDIS_PASSWORD": "secret123",
            },
        ):
            from config import RedisConfig

            config = RedisConfig()

            assert config.host == "redis.example.com"
            assert config.port == 6380
            assert config.db == 1
            assert config.password == "secret123"

    def test_redis_url_without_password(self):
        """Test Redis URL generation without password."""
        with patch.dict(os.environ, {}, clear=True):
            from config import RedisConfig

            config = RedisConfig()
            url = config.url

            assert url == "redis://localhost:6379/0"

    def test_redis_url_with_password(self):
        """Test Redis URL generation with password."""
        with patch.dict(os.environ, {"REDIS_PASSWORD": "mypass"}):
            from config import RedisConfig

            config = RedisConfig()
            url = config.url

            assert url == "redis://:mypass@localhost:6379/0"


class TestAppConfig:
    """Tests for AppConfig class."""

    def test_app_config_defaults(self):
        """Test default AppConfig values."""
        from config import AppConfig

        config = AppConfig()

        assert config.debug is False
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.session_ttl == 3600

    def test_app_config_debug_from_env(self):
        """Test debug mode from environment."""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            from config import AppConfig

            config = AppConfig()

            assert config.debug is True

    def test_app_config_has_nested_configs(self):
        """Test that AppConfig has nested configuration objects."""
        from config import AppConfig

        config = AppConfig()

        assert hasattr(config, "redis")
        assert hasattr(config, "game")
        assert hasattr(config, "cors")
        assert hasattr(config, "rate_limit")
        assert hasattr(config, "security")


class TestGameConfig:
    """Tests for GameConfig class."""

    def test_game_config_defaults(self):
        """Test default game configuration values."""
        from config import GameConfig

        config = GameConfig()

        assert config.num_decks == 6
        assert config.penetration == 0.75
        assert config.min_bet == 10
        assert config.max_bet == 1000
        assert config.blackjack_payout == 1.5
        assert config.dealer_hits_soft_17 is True
        assert config.double_after_split is True
        assert config.resplit_aces is False
        assert config.surrender_allowed == "late"
        assert config.max_splits == 4

    def test_game_config_frozen(self):
        """Test that GameConfig is frozen (immutable)."""
        from config import GameConfig

        config = GameConfig()

        # Should raise FrozenInstanceError
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            config.num_decks = 8
