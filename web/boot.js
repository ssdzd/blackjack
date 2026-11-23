/**
 * Browser-build loader: runs the trainer's Python server inside the page.
 *
 * Static hosts such as itch.io serve files but run no server, so this build
 * starts the real FastAPI app under Pyodide (CPython compiled to
 * WebAssembly) and routes the frontend's `/api/...` fetches and its game
 * WebSocket to it through web/bridge.py. The frontend itself is unchanged.
 *
 * scripts/build_web.py loads this module ahead of js/main.js. The shims are
 * in place before the frontend runs, and anything it sends while Python is
 * still starting waits for the engine.
 */

const BASE = new URL('./', import.meta.url);
const realFetch = window.fetch.bind(window);
const RealWebSocket = window.WebSocket;

const CONNECTING = 0;
const OPEN = 1;
const CLOSING = 2;
const CLOSED = 3;

const sockets = new Map();
let nextSocketId = 1;
let bridge = null;
let overlay;
let engine;

// ---- Engine ----

async function getFile(path) {
    const url = new URL(path, BASE);
    const response = await realFetch(url);
    if (!response.ok) {
        throw new Error(`Couldn't load ${url.pathname} (HTTP ${response.status}).`);
    }
    return response;
}

/**
 * Fail fast where WebAssembly can't run. Pyodide only logs a warning when a
 * security policy blocks compilation and then never settles, which would
 * leave the loading screen up forever.
 */
async function assertWebAssembly() {
    if (typeof WebAssembly !== 'object') {
        throw new Error('This browser has no WebAssembly support.');
    }
    try {
        await WebAssembly.compile(new Uint8Array([0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00]));
    } catch (error) {
        throw new Error(`WebAssembly is blocked on this page: ${error.message}`);
    }
}

async function boot() {
    await assertWebAssembly();
    const manifest = await (await getFile('bundle.json')).json();

    overlay.step('Downloading the Python engine…', 0.12);
    const runtime = new URL(manifest.runtime, BASE).href;
    const { loadPyodide } = await import(`${runtime}pyodide.mjs`);
    const pyodide = await loadPyodide({ indexURL: runtime });

    overlay.step('Installing the trainer’s libraries…', 0.55);
    await pyodide.loadPackage(
        manifest.wheels.map((name) => new URL(manifest.wheelDir + name, BASE).href),
        { messageCallback: () => {}, errorCallback: (message) => console.warn(message) },
    );

    overlay.step('Starting the card-counting engine…', 0.85);
    const app = await (await getFile(manifest.app)).arrayBuffer();
    pyodide.unpackArchive(app, 'zip', { extractDir: '/app' });
    pyodide.runPython("import sys; sys.path.insert(0, '/app')");
    bridge = pyodide.pyimport('web.bridge').start(deliver, window.localStorage);

    overlay.step('Ready', 1);
    return bridge;
}

// ---- Storage ----

/** Swap in a per-tab store where Web Storage is blocked, so the game still runs. */
function guardStorage() {
    try {
        const probe = '__bjt_probe__';
        window.localStorage.setItem(probe, '1');
        window.localStorage.removeItem(probe);
    } catch {
        const data = new Map();
        const memory = {
            getItem: (key) => (data.has(key) ? data.get(key) : null),
            setItem: (key, value) => void data.set(key, String(value)),
            removeItem: (key) => void data.delete(key),
            clear: () => data.clear(),
            key: (index) => [...data.keys()][index] ?? null,
            get length() { return data.size; },
        };
        try {
            Object.defineProperty(window, 'localStorage', { value: memory, configurable: true });
        } catch {
            /* nothing more we can do: the frontend guards its own reads */
        }
    }
}

// ---- Network shims ----

function isLocalRoute(url, prefix) {
    return url.host === location.host && url.pathname.startsWith(prefix);
}

function installFetchShim() {
    window.fetch = async function fetch(input, init = {}) {
        const request = input instanceof Request ? input : null;
        const url = new URL(request ? request.url : String(input), location.href);
        if (!isLocalRoute(url, '/api/')) return realFetch(input, init);

        const method = init.method ?? request?.method ?? 'GET';
        const headers = [...new Headers(init.headers ?? request?.headers ?? undefined)];
        let body = '';
        if (init.body != null) {
            body = typeof init.body === 'string' ? init.body : await new Response(init.body).text();
        } else if (request) {
            body = await request.text();
        }

        let server;
        try {
            server = await engine;
        } catch {
            throw new TypeError('Failed to fetch: the game engine did not start.');
        }
        const pending = server.request(method, url.pathname, url.search.slice(1), JSON.stringify(headers), body);
        let raw;
        try {
            raw = await pending;
        } finally {
            try { pending.destroy(); } catch { /* already released */ }
        }
        const reply = JSON.parse(raw);
        const nullBody = reply.status === 204 || reply.status === 205 || reply.status === 304;
        return new Response(nullBody ? null : reply.body, { status: reply.status, headers: reply.headers });
    };
}

/** Called from Python; handlers run on a fresh task, never inside Python's call. */
function deliver(id, kind, payload) {
    setTimeout(() => sockets.get(id)?.deliver(kind, payload), 0);
}

class BridgedWebSocket extends EventTarget {
    static CONNECTING = CONNECTING;
    static OPEN = OPEN;
    static CLOSING = CLOSING;
    static CLOSED = CLOSED;

    constructor(url, protocols) {
        const target = new URL(url, location.href);
        if (!isLocalRoute(target, '/ws/')) {
            return new RealWebSocket(url, protocols);
        }
        super();
        this.url = target.href;
        this.protocol = '';
        this.extensions = '';
        this.binaryType = 'blob';
        this.bufferedAmount = 0;
        this.readyState = CONNECTING;
        this.onopen = this.onmessage = this.onclose = this.onerror = null;
        this.id = nextSocketId++;
        sockets.set(this.id, this);
        engine.then(
            (server) => {
                if (this.readyState === CONNECTING) {
                    server.ws_open(this.id, target.pathname, target.search.slice(1));
                }
            },
            () => { deliver(this.id, 'error'); deliver(this.id, 'close', 1006); },
        );
    }

    send(data) {
        if (this.readyState === CONNECTING) {
            throw new DOMException("Failed to execute 'send' on 'WebSocket': Still in CONNECTING state.", 'InvalidStateError');
        }
        if (this.readyState === OPEN) bridge.ws_send(this.id, String(data));
    }

    close(code = 1000) {
        if (this.readyState >= CLOSING) return;
        const wasOpen = this.readyState === OPEN;
        this.readyState = CLOSING;
        if (wasOpen) bridge.ws_close(this.id, code);
        else deliver(this.id, 'close', code);
    }

    deliver(kind, payload) {
        if (kind === 'open' && this.readyState === CONNECTING) {
            this.readyState = OPEN;
            this.fire(new Event('open'));
        } else if (kind === 'message' && this.readyState === OPEN) {
            this.fire(new MessageEvent('message', { data: payload }));
        } else if (kind === 'error') {
            this.fire(new Event('error'));
        } else if (kind === 'close' && this.readyState !== CLOSED) {
            this.readyState = CLOSED;
            sockets.delete(this.id);
            const code = payload ?? 1000;
            this.fire(new CloseEvent('close', { code, wasClean: code === 1000 }));
        }
    }

    fire(event) {
        this.dispatchEvent(event);
        const handler = this[`on${event.type}`];
        if (typeof handler === 'function') handler.call(this, event);
    }
}

function installWebSocketShim() {
    window.WebSocket = BridgedWebSocket;
}

// ---- Loading screen ----

function showOverlay() {
    const style = document.createElement('style');
    style.textContent = `
        #engine-overlay {
            position: fixed; inset: 0; z-index: 1000;
            display: grid; place-items: center;
            padding-block: 24px;
            padding-left: max(16px, env(safe-area-inset-left, 0px));
            padding-right: max(16px, env(safe-area-inset-right, 0px));
            background: radial-gradient(ellipse at 50% 38%, var(--felt-mid, #142f22), var(--room, #0a0c0b) 72%);
            color: var(--ivory, #f3ecdd);
            transition: opacity 420ms ease;
        }
        #engine-overlay.engine-ready { opacity: 0; pointer-events: none; }
        #engine-overlay .engine-card { width: min(430px, 100%); display: grid; gap: 14px; text-align: center; }
        #engine-overlay .engine-suits { font-size: 15px; letter-spacing: 0.6em; color: var(--gold, #d4af37); }
        #engine-overlay .engine-title {
            margin: 0; font-family: var(--font-display, Georgia, serif); font-weight: 600;
            font-size: clamp(32px, 8vw, 46px); letter-spacing: 0.04em; text-wrap: balance;
        }
        #engine-overlay .engine-step {
            margin: 0; min-height: 1.4em; font-family: var(--font-mono, monospace);
            font-size: 13px; letter-spacing: 0.04em; color: var(--ivory-soft, #d9d1bd);
        }
        #engine-overlay .engine-bar { height: 3px; border-radius: 3px; overflow: hidden; background: var(--ivory-faint, rgba(243, 236, 221, 0.08)); }
        #engine-overlay .engine-bar span {
            display: block; height: 100%; width: 0;
            background: linear-gradient(90deg, var(--gold-deep, #96762a), var(--gold-bright, #ecd489));
            transition: width 500ms ease;
        }
        #engine-overlay .engine-note { margin: 0; font-size: 13px; line-height: 1.55; color: var(--ivory-mute, #a29b88); text-wrap: pretty; }
        #engine-overlay.engine-failed .engine-step { color: var(--loss, #cf5f6d); }
        #engine-overlay.engine-failed .engine-bar { display: none; }
        #engine-overlay .engine-error {
            margin: 0; padding: 10px 12px; max-height: 30vh; overflow: auto;
            text-align: left; white-space: pre-wrap; overflow-wrap: anywhere;
            font-family: var(--font-mono, monospace); font-size: 11.5px; color: var(--ivory-mute, #a29b88);
            background: var(--panel-solid, #101412); border: 1px solid var(--panel-hairline, rgba(243, 236, 221, 0.06)); border-radius: 6px;
        }
        @media (prefers-reduced-motion: reduce) {
            #engine-overlay, #engine-overlay .engine-bar span { transition: none; }
        }
    `;
    document.head.appendChild(style);

    const root = document.createElement('div');
    root.id = 'engine-overlay';
    root.setAttribute('role', 'status');
    root.setAttribute('aria-live', 'polite');
    root.innerHTML = `
        <div class="engine-card">
            <div class="engine-suits" aria-hidden="true">♠ ♥ ♦ ♣</div>
            <h1 class="engine-title">Blackjack Noir</h1>
            <p class="engine-step">Loading…</p>
            <div class="engine-bar" aria-hidden="true"><span></span></div>
            <p class="engine-note">The trainer’s statistics engine is Python, running in your browser.
                The first visit downloads about 9&nbsp;MB; after that it starts from cache.</p>
        </div>`;
    document.body.appendChild(root);

    const card = root.querySelector('.engine-card');
    const step = root.querySelector('.engine-step');
    const bar = root.querySelector('.engine-bar span');
    const note = root.querySelector('.engine-note');
    const slow = setTimeout(() => {
        note.textContent = 'Still loading. On a slow connection the first visit can take a minute or two.';
    }, 30000);

    return {
        step(text, fraction) {
            step.textContent = text;
            bar.style.width = `${Math.round(fraction * 100)}%`;
        },
        done() {
            clearTimeout(slow);
            root.classList.add('engine-ready');
            setTimeout(() => root.remove(), 450);
        },
        fail(error) {
            clearTimeout(slow);
            console.error('Game engine failed to start:', error);
            root.classList.add('engine-failed');
            step.textContent = 'The game engine couldn’t start in this browser.';
            note.textContent = 'This build runs Python through WebAssembly. Open it in a current '
                + 'Chrome, Edge, Firefox or Safari; some embedded viewers and strict security '
                + 'settings block WebAssembly.';
            const detail = document.createElement('pre');
            detail.className = 'engine-error';
            detail.textContent = String(error?.message ?? error).slice(0, 800);
            card.append(detail);
        },
    };
}

// ---- Start (last, so every declaration above is initialized) ----

guardStorage();
overlay = showOverlay();
engine = boot();
engine.then(() => overlay.done(), (error) => overlay.fail(error));
installFetchShim();
installWebSocketShim();
