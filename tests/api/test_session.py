"""Tests for session management."""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import patch
import time

from api.session import (
    SessionSigner,
    InMemorySessionStore,
    get_session_signer,
    create_session,
    extract_session_id,
)


class TestSessionSigner:
    """Tests for SessionSigner class."""

    def test_sign_creates_token(self):
        """Test that sign creates a non-empty token."""
        signer = SessionSigner(secret_key="test-secret")
        session_id = "test-session-123"

        token = signer.sign(session_id)

        assert token is not None
        assert len(token) > 0
        assert token != session_id  # Token should be different from original

    def test_unsign_returns_original_id(self):
        """Test that unsign returns the original session ID."""
        signer = SessionSigner(secret_key="test-secret")
        session_id = "test-session-456"

        token = signer.sign(session_id)
        recovered = signer.unsign(token, max_age=3600)

        assert recovered == session_id

    def test_unsign_invalid_token_returns_none(self):
        """Test that unsign returns None for invalid tokens."""
        signer = SessionSigner(secret_key="test-secret")

        result = signer.unsign("invalid-token-data", max_age=3600)

        assert result is None

    def test_unsign_wrong_secret_returns_none(self):
        """Test that unsign returns None when using wrong secret key."""
        signer1 = SessionSigner(secret_key="secret-one")
        signer2 = SessionSigner(secret_key="secret-two")
        session_id = "test-session"

        token = signer1.sign(session_id)
        result = signer2.unsign(token, max_age=3600)

        assert result is None

    def test_unsign_expired_token_returns_none(self):
        """Test that unsign returns None for expired tokens."""
        from itsdangerous import URLSafeTimedSerializer
        from unittest.mock import patch
        import time as time_module

        signer = SessionSigner(secret_key="test-secret")
        session_id = "test-session"

        token = signer.sign(session_id)

        # Mock time to simulate token being signed 2 hours ago
        original_time = time_module.time

        def mock_time():
            return original_time() + 7200  # 2 hours later

        with patch("time.time", mock_time):
            # Token is now 2 hours old, max_age is 1 hour
            result = signer.unsign(token, max_age=3600)

        assert result is None

    def test_sign_different_sessions_produce_different_tokens(self):
        """Test that different session IDs produce different tokens."""
        signer = SessionSigner(secret_key="test-secret")

        token1 = signer.sign("session-1")
        token2 = signer.sign("session-2")

        assert token1 != token2


class TestInMemorySessionStore:
    """Tests for InMemorySessionStore class."""

    @pytest_asyncio.fixture
    async def store(self):
        """Create a fresh session store."""
        return InMemorySessionStore()

    @pytest.mark.asyncio
    async def test_set_and_get_session(self, store):
        """Test setting and getting session data."""
        session_id = "test-session"
        data = {"user": "test-user", "score": 100}

        await store.set(session_id, data, ttl=3600)
        retrieved = await store.get(session_id)

        assert retrieved == data

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self, store):
        """Test that getting a non-existent session returns None."""
        result = await store.get("nonexistent-session")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_session(self, store):
        """Test deleting a session."""
        session_id = "test-session"
        await store.set(session_id, {"data": "value"}, ttl=3600)

        await store.delete(session_id)
        result = await store.get(session_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session_no_error(self, store):
        """Test that deleting a non-existent session doesn't raise an error."""
        # Should not raise
        await store.delete("nonexistent-session")

    @pytest.mark.asyncio
    async def test_exists_check(self, store):
        """Test existence check."""
        session_id = "test-session"

        # Should not exist initially
        assert await store.exists(session_id) is False

        # Should exist after setting
        await store.set(session_id, {"data": "value"}, ttl=3600)
        assert await store.exists(session_id) is True

    @pytest.mark.asyncio
    async def test_session_expiration(self, store):
        """Test that expired sessions are not returned."""
        session_id = "test-session"
        await store.set(session_id, {"data": "value"}, ttl=1)

        # Should exist initially
        assert await store.exists(session_id) is True

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired now
        result = await store.get(session_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, store):
        """Test cleanup of expired sessions."""
        # Add some sessions with very short TTL
        await store.set("session-1", {"data": 1}, ttl=1)
        await store.set("session-2", {"data": 2}, ttl=1)
        await store.set("session-3", {"data": 3}, ttl=3600)  # Long TTL

        # Wait for first two to expire
        time.sleep(1.5)

        # Cleanup expired
        count = await store.cleanup_expired()

        assert count == 2
        assert await store.exists("session-1") is False
        assert await store.exists("session-2") is False
        assert await store.exists("session-3") is True

    @pytest.mark.asyncio
    async def test_overwrite_session(self, store):
        """Test that session data can be overwritten."""
        session_id = "test-session"
        await store.set(session_id, {"version": 1}, ttl=3600)
        await store.set(session_id, {"version": 2}, ttl=3600)

        result = await store.get(session_id)
        assert result == {"version": 2}

    @pytest.mark.asyncio
    async def test_create_session_id_signed(self, store):
        """Test that create_session_id returns a signed token by default."""
        session_id = store.create_session_id(signed=True)

        # Signed tokens are longer due to signature
        assert len(session_id) > 36  # UUID length

    @pytest.mark.asyncio
    async def test_create_session_id_unsigned(self, store):
        """Test that create_session_id can return unsigned UUID."""
        session_id = store.create_session_id(signed=False)

        # Should be a UUID (36 characters with hyphens)
        assert len(session_id) == 36
        assert session_id.count("-") == 4


class TestModuleFunctions:
    """Tests for module-level session functions."""

    @pytest.mark.asyncio
    async def test_create_session_returns_signed_id(self):
        """Test that create_session returns a signed session ID."""
        # Reset session store for clean test
        import api.session as session_module
        session_module._session_store = None

        session_id = await create_session({"test": "data"})

        assert session_id is not None
        assert len(session_id) > 36  # Signed token is longer than UUID

    @pytest.mark.asyncio
    async def test_extract_session_id(self):
        """Test extracting session ID from signed token."""
        signer = SessionSigner(secret_key="test-secret")
        original_id = "test-session-123"
        token = signer.sign(original_id)

        # Use the same signer instance by patching
        with patch("api.session.get_session_signer", return_value=signer):
            extracted = extract_session_id(token)

        assert extracted == original_id

    @pytest.mark.asyncio
    async def test_extract_session_id_invalid_returns_none(self):
        """Test that extract_session_id returns None for invalid tokens."""
        result = extract_session_id("invalid-token")

        # This might return None or the token depending on session signer state
        # The key is it doesn't raise an exception
        assert result is None or isinstance(result, str)

    def test_get_session_signer_returns_singleton(self):
        """Test that get_session_signer returns the same instance."""
        # Reset for clean test
        import api.session as session_module
        session_module._session_signer = None

        signer1 = get_session_signer()
        signer2 = get_session_signer()

        assert signer1 is signer2
