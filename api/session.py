"""Session management with Redis backend and in-memory fallback."""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from config import config


class SessionStore(ABC):
    """Abstract session store."""

    @abstractmethod
    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Get session data."""
        ...

    @abstractmethod
    async def set(self, session_id: str, data: dict[str, Any], ttl: int | None = None) -> None:
        """Set session data."""
        ...

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete session."""
        ...

    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        ...

    def create_session_id(self) -> str:
        """Create a new session ID."""
        return str(uuid4())


class InMemorySessionStore(SessionStore):
    """In-memory session store for local development."""

    def __init__(self) -> None:
        self._sessions: dict[str, tuple[dict[str, Any], datetime]] = {}

    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Get session data."""
        if session_id not in self._sessions:
            return None

        data, expiry = self._sessions[session_id]
        if expiry < datetime.now():
            await self.delete(session_id)
            return None

        return data

    async def set(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Set session data."""
        ttl = ttl or config.session_ttl
        expiry = datetime.now() + timedelta(seconds=ttl)
        self._sessions[session_id] = (data, expiry)

    async def delete(self, session_id: str) -> None:
        """Delete session."""
        self._sessions.pop(session_id, None)

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return await self.get(session_id) is not None

    async def cleanup_expired(self) -> int:
        """Remove expired sessions."""
        now = datetime.now()
        expired = [
            sid for sid, (_, expiry) in self._sessions.items() if expiry < now
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)


class RedisSessionStore(SessionStore):
    """Redis-backed session store."""

    def __init__(self, redis_client: "redis.Redis") -> None:  # type: ignore
        self._redis = redis_client
        self._prefix = "blackjack:session:"

    def _key(self, session_id: str) -> str:
        """Get Redis key for session."""
        return f"{self._prefix}{session_id}"

    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Get session data."""
        data = await self._redis.get(self._key(session_id))
        if data is None:
            return None
        return json.loads(data)

    async def set(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Set session data."""
        ttl = ttl or config.session_ttl
        await self._redis.setex(
            self._key(session_id),
            ttl,
            json.dumps(data),
        )

    async def delete(self, session_id: str) -> None:
        """Delete session."""
        await self._redis.delete(self._key(session_id))

    async def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return await self._redis.exists(self._key(session_id)) > 0


# Global session store instance
_session_store: SessionStore | None = None


async def get_session_store() -> SessionStore:
    """Get or create the session store."""
    global _session_store

    if _session_store is not None:
        return _session_store

    if REDIS_AVAILABLE:
        try:
            redis_client = redis.from_url(config.redis.url)
            await redis_client.ping()
            _session_store = RedisSessionStore(redis_client)
            return _session_store
        except Exception:
            pass  # Fall through to in-memory

    _session_store = InMemorySessionStore()
    return _session_store


async def create_session(data: dict[str, Any] | None = None) -> str:
    """Create a new session."""
    store = await get_session_store()
    session_id = store.create_session_id()
    await store.set(session_id, data or {})
    return session_id


async def get_session(session_id: str) -> dict[str, Any] | None:
    """Get session data."""
    store = await get_session_store()
    return await store.get(session_id)


async def update_session(session_id: str, data: dict[str, Any]) -> None:
    """Update session data."""
    store = await get_session_store()
    await store.set(session_id, data)


async def delete_session(session_id: str) -> None:
    """Delete a session."""
    store = await get_session_store()
    await store.delete(session_id)
