"""Session store on Web Storage, for the browser build.

The server keeps sessions and career profiles in Redis or process memory. In
the browser build the "server" is the player's own tab, so process memory
would wipe a career on every reload; this store keeps it in the page's
``localStorage`` instead.
"""

import json
import time
from typing import Any

from api.session import InMemorySessionStore, SessionStore
from config import config


class WebStorageSessionStore(SessionStore):
    """Persist session data in a Web Storage object.

    ``storage`` is anything with the Web Storage ``getItem`` / ``setItem`` /
    ``removeItem`` methods: the page's ``localStorage`` under Pyodide, a fake
    in tests. Writes that storage refuses (quota, revoked site data) land in
    process memory, so play continues and only persistence is lost.
    """

    def __init__(self, storage: Any, prefix: str = "bjt-store:") -> None:
        self._storage = storage
        self._prefix = prefix
        self._fallback = InMemorySessionStore()

    def _key(self, session_id: str) -> str:
        return f"{self._prefix}{session_id}"

    async def get(self, session_id: str) -> dict[str, Any] | None:
        try:
            raw = self._storage.getItem(self._key(session_id))
        except Exception:
            raw = None
        if raw is None:
            return await self._fallback.get(session_id)
        try:
            record = json.loads(raw)
            expires = float(record["expires"])
            data = record["data"]
        except (ValueError, KeyError, TypeError):
            await self.delete(session_id)  # corrupted entries read as missing
            return None
        if expires < time.time():
            await self.delete(session_id)
            return None
        return data

    async def set(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        ttl = ttl or config.session_ttl
        record = json.dumps({"expires": time.time() + ttl, "data": data})
        try:
            self._storage.setItem(self._key(session_id), record)
        except Exception:
            await self._fallback.set(session_id, data, ttl)

    async def delete(self, session_id: str) -> None:
        try:
            self._storage.removeItem(self._key(session_id))
        except Exception:
            pass
        await self._fallback.delete(session_id)

    async def exists(self, session_id: str) -> bool:
        return await self.get(session_id) is not None
