"""Profile persistence on the session-store backend.

Profiles ride the same Redis-with-in-memory-fallback store as sessions but
with their own key prefix and an explicit long TTL — the store's default
TTL is one hour, which would wipe careers between sittings.
"""

import asyncio
from typing import Any

from api.session import get_session_store
from core.progression import PlayerProfile, apply_event, new_profile
from core.progression.profile import ProgressionDelta

PROFILE_TTL = 90 * 24 * 3600  # 90 days, refreshed on every save
_KEY_PREFIX = "profile:"

# Serialize each profile's read-modify-write: decision grading and round
# events interleave across await points (and across sockets sharing a
# profile), and the later save would silently drop the earlier event's XP.
# In-process only — a multi-worker deploy needs an atomic store transaction.
_profile_locks: dict[str, asyncio.Lock] = {}


def _profile_lock(profile_id: str) -> asyncio.Lock:
    lock = _profile_locks.get(profile_id)
    if lock is None:
        lock = _profile_locks.setdefault(profile_id, asyncio.Lock())
    return lock


def _key(profile_id: str) -> str:
    return f"{_KEY_PREFIX}{profile_id}"


async def load_profile(profile_id: str) -> PlayerProfile | None:
    store = await get_session_store()
    data = await store.get(_key(profile_id))
    if data is None:
        return None
    try:
        return PlayerProfile.model_validate(data)
    except Exception:
        return None  # corrupted payloads read as missing


async def save_profile(profile: PlayerProfile) -> None:
    store = await get_session_store()
    await store.set(
        _key(profile.profile_id),
        profile.model_dump(mode="json"),
        ttl=PROFILE_TTL,
    )


async def create_profile() -> PlayerProfile:
    profile = new_profile()
    await save_profile(profile)
    return profile


async def get_or_create_profile(profile_id: str) -> PlayerProfile:
    profile = await load_profile(profile_id)
    if profile is None:
        profile = new_profile(profile_id)
        await save_profile(profile)
    return profile


async def progress(
    profile_id: str | None,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> ProgressionDelta | None:
    """Apply one progression event to a stored profile and persist it.

    Returns the delta, or None when no profile is attached. Never raises —
    progression must not break gameplay.
    """
    if not profile_id:
        return None
    try:
        async with _profile_lock(profile_id):
            profile = await get_or_create_profile(profile_id)
            delta = apply_event(profile, event_type, payload)
            await save_profile(profile)
            return delta
    except Exception:
        return None
