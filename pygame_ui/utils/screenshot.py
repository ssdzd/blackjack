"""Screenshot utility for visual testing."""

import os
import time
from typing import Optional

import pyautogui


def take_screenshot(path: str = "/tmp/game_screenshot.png") -> str:
    """Take a screenshot and save it.

    Args:
        path: Where to save the screenshot

    Returns:
        Path to saved screenshot
    """
    screenshot = pyautogui.screenshot()
    screenshot.save(path)
    return path


def take_window_screenshot(
    window_title: str = "Blackjack",
    path: str = "/tmp/game_screenshot.png",
) -> Optional[str]:
    """Take a screenshot of a specific window (macOS).

    Args:
        window_title: Title of window to capture
        path: Where to save the screenshot

    Returns:
        Path to saved screenshot, or None if window not found
    """
    import subprocess

    # Use screencapture with window selection
    # -l flag captures a specific window by ID
    # First, find the window ID
    script = f'''
    tell application "System Events"
        set windowList to every window of every process
        repeat with proc in every process
            repeat with win in every window of proc
                if name of win contains "{window_title}" then
                    return id of win
                end if
            end repeat
        end repeat
    end tell
    return ""
    '''

    try:
        # Use screencapture for the whole screen as fallback
        result = subprocess.run(
            ["screencapture", "-x", path],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0 and os.path.exists(path):
            return path
    except Exception:
        pass

    # Fallback to pyautogui
    return take_screenshot(path)


if __name__ == "__main__":
    path = take_screenshot()
    print(f"Screenshot saved to: {path}")
