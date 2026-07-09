"""Pytest fixtures for UI tests."""

import subprocess
import time

import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="session")
def server():
    """Start the FastAPI server for UI tests.

    Output goes to DEVNULL: an unread PIPE fills the OS pipe buffer with
    access logs after a few dozen page loads, blocking uvicorn mid-write
    and hanging every subsequent test.
    """
    proc = subprocess.Popen(
        ["uvicorn", "api.main:app", "--port", "8765"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)  # Wait for server startup
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the test server."""
    return "http://localhost:8765"


@pytest.fixture
def game_page(page: Page, server, base_url):
    """A page navigated to the game."""
    page.goto(base_url)
    page.wait_for_selector("#game-area")
    return page


ANY_POST_BET_CONTROLS = (
    "#action-controls:not(.hidden), "
    "#insurance-controls:not(.hidden), "
    "#result-controls:not(.hidden)"
)


@pytest.fixture
def reach_player_turn():
    """Deal hands until one reaches the player-turn state.

    A fresh deal can skip the player turn entirely (instant blackjack
    resolution) or detour through the insurance offer (dealer ace), so a
    single bet-and-wait is inherently flaky. Decline insurance and re-deal
    until action controls appear.
    """

    def _reach(page: Page, attempts: int = 8) -> None:
        for _ in range(attempts):
            if page.locator("#betting-controls:not(.hidden)").count():
                page.click("#btn-bet")
            page.wait_for_selector(ANY_POST_BET_CONTROLS, timeout=5000)
            if page.locator("#action-controls:not(.hidden)").count():
                return
            if page.locator("#insurance-controls:not(.hidden)").count():
                page.click("#btn-decline-insurance")
                page.wait_for_selector(
                    "#action-controls:not(.hidden), #result-controls:not(.hidden)",
                    timeout=5000,
                )
                if page.locator("#action-controls:not(.hidden)").count():
                    return
            # Instant resolution -- start the next round and try again
            page.click("#btn-new-round")
            page.wait_for_selector("#betting-controls:not(.hidden)", timeout=5000)
        raise AssertionError("Could not reach player turn after several deals")

    return _reach
