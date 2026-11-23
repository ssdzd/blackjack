"""Serve the trainer's FastAPI app to the page it runs in, with no network.

The browser build (scripts/build_web.py) runs this module under Pyodide,
CPython compiled to WebAssembly, so the game can ship to static hosts such as
itch.io. web/boot.js routes the frontend's ``/api/...`` fetches and its game
WebSocket to a :class:`Bridge`, which drives the real ASGI app in-process:
the same code a uvicorn server runs, minus the sockets.

Nothing here imports the app at module level, because :func:`start` has to
adapt the runtime before ``api`` is first imported.
"""

import asyncio
import json
import os
import sys
import traceback
from typing import Any, Callable

IN_BROWSER = sys.platform == "emscripten"

# emit(connection_id, kind, payload): kind is "open", "message" or "close".
Emit = Callable[[int, str, Any], None]


def prepare_runtime() -> None:
    """Adapt the process to WebAssembly before the app is imported.

    The browser has no threads for Python, and slowapi's in-memory limiter
    store starts a ``threading.Timer`` as soon as ``api.main`` is imported.
    A rate limit on a server that only its own tab can reach protects
    nothing, so it is switched off and the timer made inert.
    """
    os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
    if IN_BROWSER:
        import threading

        threading.Timer.start = lambda self: None  # type: ignore[method-assign]


def start(emit: Emit, storage: Any = None) -> "Bridge":
    """Boot the app for the page. Called once by web/boot.js.

    ``storage`` is the page's ``localStorage``; with it, sessions and career
    profiles survive a reload instead of living in process memory.
    """
    prepare_runtime()

    import api.session
    from api.main import app
    from web.storage import WebStorageSessionStore

    if storage is not None:
        api.session._session_store = WebStorageSessionStore(storage)
    return Bridge(app, emit)


def _scope(kind: str, path: str, query: str, headers: list[tuple[bytes, bytes]]) -> dict[str, Any]:
    return {
        "type": kind,
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "http" if kind == "http" else "ws",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query.encode("latin-1"),
        "root_path": "",
        "headers": [(b"host", b"localhost"), *headers],
        "client": ("127.0.0.1", 0),
        "server": ("localhost", 80),
    }


class Bridge:
    """The page's in-process stand-in for the server's HTTP and WebSocket ports."""

    def __init__(self, app: Any, emit: Emit) -> None:
        self.app = app
        self._emit = emit
        self._sockets: dict[int, "_Socket"] = {}

    def emit(self, conn_id: int, kind: str, payload: Any = None) -> None:
        try:
            self._emit(conn_id, kind, payload)
        except Exception:
            traceback.print_exc()  # a page-side failure must not take down the app

    # ---- HTTP ----

    def request(
        self, method: str, path: str, query: str, headers_json: str, body: str
    ) -> "asyncio.Future[str]":
        """Schedule one HTTP request; resolves to its JSON-encoded response."""
        return asyncio.ensure_future(self.http(method, path, query, headers_json, body))

    async def http(
        self,
        method: str,
        path: str,
        query: str = "",
        headers_json: str = "[]",
        body: str = "",
    ) -> str:
        """Run one HTTP exchange through the app.

        Returns ``{"status", "headers", "body"}`` as JSON text: one string is
        the cheapest thing to hand back across the JavaScript boundary.
        """
        headers = [
            (name.lower().encode("latin-1"), value.encode("latin-1"))
            for name, value in json.loads(headers_json or "[]")
        ]
        scope = _scope("http", path, query, headers)
        scope["method"] = method.upper()
        payload = body.encode("utf-8")
        body_sent = False
        finished = asyncio.Event()
        start: dict[str, Any] | None = None
        chunks: list[bytes] = []

        async def receive() -> dict[str, Any]:
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {"type": "http.request", "body": payload, "more_body": False}
            await finished.wait()  # like a server: "disconnect" once the reply is out
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    finished.set()

        try:
            await self.app(scope, receive, send)
        except Exception:
            # Starlette answers 500 and then re-raises for the server to log.
            traceback.print_exc()
        finally:
            finished.set()

        if start is None:
            return json.dumps({
                "status": 500,
                "headers": [["content-type", "application/json"]],
                "body": '{"detail": "Internal Server Error"}',
            })
        return json.dumps({
            "status": start["status"],
            # content-length counts bytes; the page rebuilds the body from text.
            "headers": [
                [name.decode("latin-1"), value.decode("latin-1")]
                for name, value in start.get("headers", [])
                if name.lower() != b"content-length"
            ],
            "body": b"".join(chunks).decode("utf-8", "replace"),
        })

    # ---- WebSocket ----

    def ws_open(self, conn_id: int, path: str, query: str = "") -> None:
        self._sockets[conn_id] = _Socket(self, conn_id, path, query)

    def ws_send(self, conn_id: int, text: str) -> None:
        socket = self._sockets.get(conn_id)
        if socket is not None:
            socket.inbox.put_nowait({"type": "websocket.receive", "text": text})

    def ws_close(self, conn_id: int, code: int = 1000) -> None:
        socket = self._sockets.get(conn_id)
        if socket is not None:
            socket.inbox.put_nowait({"type": "websocket.disconnect", "code": code})


class _Socket:
    """One page WebSocket, served by the app's websocket route."""

    def __init__(self, bridge: Bridge, conn_id: int, path: str, query: str) -> None:
        self._bridge = bridge
        self.conn_id = conn_id
        self.closed = False
        self.inbox: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.inbox.put_nowait({"type": "websocket.connect"})
        scope = _scope("websocket", path, query, [])
        scope["subprotocols"] = []
        self.task = asyncio.ensure_future(bridge.app(scope, self.inbox.get, self._send))
        self.task.add_done_callback(self._finished)

    async def _send(self, message: dict[str, Any]) -> None:
        kind = message["type"]
        if kind == "websocket.accept":
            self._bridge.emit(self.conn_id, "open")
        elif kind == "websocket.send":
            text = message.get("text")
            if text is None:
                text = (message.get("bytes") or b"").decode("utf-8", "replace")
            self._bridge.emit(self.conn_id, "message", text)
        elif kind == "websocket.close":
            self._close(message.get("code", 1000))

    def _close(self, code: int) -> None:
        if self.closed:
            return
        self.closed = True
        self._bridge._sockets.pop(self.conn_id, None)
        self._bridge.emit(self.conn_id, "close", code)

    def _finished(self, task: "asyncio.Task[Any]") -> None:
        if task.cancelled():
            self._close(1001)
        elif task.exception() is not None:
            traceback.print_exception(task.exception())
            self._close(1011)
        else:
            self._close(1000)
