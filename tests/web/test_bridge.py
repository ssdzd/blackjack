"""The browser build's bridge and storage, run under CPython against the real app.

In the browser, web/boot.js calls these same methods from JavaScript; here
the tests stand in for it.
"""

import asyncio
import concurrent.futures
import functools
import json
import time

import api.session
from api.main import app
from web.bridge import Bridge, start
from web.storage import WebStorageSessionStore


def own_loop(test):
    """Run an async test on a fresh event loop in a worker thread.

    Once a browser test has run, pytest-playwright's sync API keeps an event
    loop running on the main thread, so pytest-asyncio can't start one there.
    """

    @functools.wraps(test)
    def run(*args, **kwargs):
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, test(*args, **kwargs)).result()

    return run


class FakeStorage:
    """The slice of the Web Storage API the store uses."""

    def __init__(self, fail_writes: bool = False) -> None:
        self.items: dict[str, str] = {}
        self.fail_writes = fail_writes

    def getItem(self, key):  # noqa: N802 - Web Storage spelling
        return self.items.get(key)

    def setItem(self, key, value):  # noqa: N802
        if self.fail_writes:
            raise RuntimeError("QuotaExceededError")
        self.items[key] = value

    def removeItem(self, key):  # noqa: N802
        self.items.pop(key, None)


class Page:
    """Receives what the bridge emits, as boot.js does."""

    def __init__(self) -> None:
        self.events: asyncio.Queue = asyncio.Queue()

    def emit(self, conn_id, kind, payload=None):
        self.events.put_nowait((conn_id, kind, payload))

    async def next(self, kind: str, timeout: float = 5.0):
        while True:
            conn_id, got, payload = await asyncio.wait_for(self.events.get(), timeout)
            if got == kind:
                return conn_id, payload


class TestHttp:
    @own_loop
    async def test_requests_reach_the_real_app(self):
        bridge = Bridge(app, Page().emit)
        headers = json.dumps([["Content-Type", "application/json"]])

        reply = json.loads(await bridge.http("POST", "/api/progression/profile", "", headers, "{}"))
        assert reply["status"] == 200
        created = json.loads(reply["body"])
        assert created["xp"] == 0

        reply = json.loads(await bridge.http("GET", f"/api/progression/profile/{created['profile_id']}"))
        assert json.loads(reply["body"])["profile_id"] == created["profile_id"]
        assert ["content-type", "application/json"] in reply["headers"]

    @own_loop
    async def test_unknown_route_is_a_404_not_a_crash(self):
        reply = json.loads(await Bridge(app, Page().emit).http("GET", "/api/no-such-route"))
        assert reply["status"] == 404


class TestWebSocket:
    @own_loop
    async def test_plays_a_round_then_closes(self):
        page = Page()
        bridge = Bridge(app, page.emit)
        bridge.ws_open(7, "/ws/game/bridge-test")

        conn_id, _ = await page.next("open")
        assert conn_id == 7
        _, first = await page.next("message")
        assert json.loads(first)["type"] == "state_update"

        bridge.ws_send(7, json.dumps({"type": "bet", "amount": 10}))
        acted = False
        while True:
            message = json.loads((await page.next("message"))[1])
            state = (message.get("state") or {}).get("state")
            if state == "OFFERING_INSURANCE" and not acted:
                bridge.ws_send(7, json.dumps({"type": "insurance", "take": False}))
            elif state == "PLAYER_TURN" and not acted:
                acted = True
                bridge.ws_send(7, json.dumps({"type": "action", "action": "stand"}))
            if message.get("event_type") == "ROUND_ENDED":
                break

        bridge.ws_close(7)
        _, code = await page.next("close")
        assert code == 1000


class TestStart:
    @own_loop
    async def test_start_puts_sessions_in_web_storage(self, monkeypatch):
        monkeypatch.setattr(api.session, "_session_store", api.session._session_store)
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        storage = FakeStorage()

        bridge = start(Page().emit, storage)
        reply = json.loads(await bridge.http("POST", "/api/progression/profile", "", "[]", "{}"))

        profile_id = json.loads(reply["body"])["profile_id"]
        assert isinstance(api.session._session_store, WebStorageSessionStore)
        assert f"bjt-store:profile:{profile_id}" in storage.items


class TestWebStorageStore:
    @own_loop
    async def test_round_trip(self):
        store = WebStorageSessionStore(FakeStorage())
        await store.set("abc", {"xp": 12})
        assert await store.get("abc") == {"xp": 12}
        assert await store.exists("abc")
        await store.delete("abc")
        assert await store.get("abc") is None

    @own_loop
    async def test_expired_entries_read_as_missing(self):
        storage = FakeStorage()
        storage.items["bjt-store:abc"] = json.dumps({"expires": time.time() - 1, "data": {"xp": 1}})
        assert await WebStorageSessionStore(storage).get("abc") is None
        assert storage.items == {}

    @own_loop
    async def test_corrupted_entries_read_as_missing(self):
        storage = FakeStorage()
        storage.items["bjt-store:abc"] = "{not json"
        assert await WebStorageSessionStore(storage).get("abc") is None

    @own_loop
    async def test_refused_writes_keep_the_game_going(self):
        store = WebStorageSessionStore(FakeStorage(fail_writes=True))
        await store.set("abc", {"xp": 3})
        assert await store.get("abc") == {"xp": 3}
