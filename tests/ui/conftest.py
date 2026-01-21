"""Pytest fixtures for UI tests."""

import subprocess
import time

import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="session")
def server():
    """Start the FastAPI server for UI tests."""
    proc = subprocess.Popen(
        ["uvicorn", "api.main:app", "--port", "8765"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)  # Wait for server startup
    yield proc
    proc.terminate()
    proc.wait()


@pytest.fixture
def base_url():
    """Base URL for the test server."""
    return "http://localhost:8765"


@pytest.fixture
def game_page(page: Page, server, base_url):
    """A page navigated to the game."""
    page.goto(base_url)
    page.wait_for_selector("#game-area")
    return page
