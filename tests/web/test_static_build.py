"""Smoke-test the built static site in Chromium: Python boots in the page and plays.

Needs `python scripts/build_web.py` first (CI's browser-build job runs it);
skipped when dist/web is absent or playwright isn't installed.
"""

import functools
import http.server
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")

DIST = Path(__file__).resolve().parents[2] / "dist"
if not (DIST / "web" / "index.html").exists():
    pytest.skip("dist/web not built (python scripts/build_web.py)", allow_module_level=True)

POST_BET = "#action-controls:not(.hidden), #insurance-controls:not(.hidden), #result-controls:not(.hidden)"


class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".mjs": "text/javascript",
        ".js": "text/javascript",
        ".wasm": "application/wasm",
        ".whl": "application/zip",
    }

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def site_url():
    """dist/ over HTTP; the game sits in a sub-folder, as on itch.io."""
    handler = functools.partial(_Handler, directory=str(DIST))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/web/index.html"
    server.shutdown()


def test_python_boots_in_the_page_and_plays_a_round(page, site_url):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.add_init_script("localStorage.setItem('bjt-onboarded', '1')")
    page.goto(site_url)

    page.wait_for_selector("#engine-overlay.engine-failed, body:not(:has(#engine-overlay))",
                           state="attached", timeout=120_000)
    assert page.locator("#engine-overlay.engine-failed").count() == 0, page.inner_text("#engine-overlay")

    page.click("#btn-bet")
    page.wait_for_selector(POST_BET, timeout=15_000)
    if page.locator("#insurance-controls:not(.hidden)").count():
        page.click("#btn-decline-insurance")
        page.wait_for_selector("#action-controls:not(.hidden), #result-controls:not(.hidden)", timeout=15_000)
    if page.locator("#action-controls:not(.hidden)").count():
        page.click("#btn-stand")
    page.wait_for_selector("#result-controls:not(.hidden)", timeout=15_000)

    page.click("#nav-career")
    page.wait_for_selector(".venue-card", timeout=15_000)
    assert errors == []
