"""Configuration constants for PyGame Balatro-Style UI."""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Colors:
    """Color palette for the blackjack UI."""

    # Felt and background
    FELT_GREEN: Tuple[int, int, int] = (34, 87, 59)
    FELT_DARK: Tuple[int, int, int] = (25, 65, 44)
    BACKGROUND: Tuple[int, int, int] = (18, 18, 24)

    # Card colors
    CARD_WHITE: Tuple[int, int, int] = (245, 243, 238)
    CARD_RED: Tuple[int, int, int] = (192, 57, 57)
    CARD_BLACK: Tuple[int, int, int] = (28, 28, 32)
    CARD_BACK: Tuple[int, int, int] = (65, 85, 130)
    CARD_BACK_PATTERN: Tuple[int, int, int] = (85, 105, 150)

    # UI accents
    GOLD: Tuple[int, int, int] = (255, 200, 87)
    GOLD_DARK: Tuple[int, int, int] = (200, 150, 50)
    SILVER: Tuple[int, int, int] = (180, 180, 195)

    # Count colors
    COUNT_POSITIVE: Tuple[int, int, int] = (100, 200, 100)
    COUNT_NEGATIVE: Tuple[int, int, int] = (200, 100, 100)
    COUNT_NEUTRAL: Tuple[int, int, int] = (200, 200, 200)

    # Effects
    SHADOW: Tuple[int, int, int, int] = (0, 0, 0, 100)
    GLOW_HIGHLIGHT: Tuple[int, int, int] = (255, 255, 200)

    # Text
    TEXT_WHITE: Tuple[int, int, int] = (240, 240, 240)
    TEXT_MUTED: Tuple[int, int, int] = (150, 150, 160)

    # Buttons
    BUTTON_DEFAULT: Tuple[int, int, int] = (60, 70, 90)
    BUTTON_HOVER: Tuple[int, int, int] = (80, 95, 120)
    BUTTON_PRESSED: Tuple[int, int, int] = (45, 55, 70)
    BUTTON_DISABLED: Tuple[int, int, int] = (50, 50, 55)

    # Panels
    PANEL_BG: Tuple[int, int, int] = (35, 38, 48)
    PANEL_BORDER: Tuple[int, int, int] = (60, 65, 80)


@dataclass(frozen=True)
class Dimensions:
    """Dimension constants for layout and sizing."""

    # Screen
    SCREEN_WIDTH: int = 1280
    SCREEN_HEIGHT: int = 720
    TARGET_FPS: int = 60

    # Cards
    CARD_WIDTH: int = 90
    CARD_HEIGHT: int = 126
    CARD_CORNER_RADIUS: int = 8
    CARD_SHADOW_OFFSET: int = 4

    # Layout
    HAND_SPACING: int = 30
    DECK_POSITION: Tuple[int, int] = (100, 200)
    PLAYER_HAND_Y: int = 480
    DEALER_HAND_Y: int = 150
    CENTER_X: int = SCREEN_WIDTH // 2
    CENTER_Y: int = SCREEN_HEIGHT // 2

    # UI Elements
    BUTTON_WIDTH: int = 120
    BUTTON_HEIGHT: int = 45
    BUTTON_CORNER_RADIUS: int = 6
    PANEL_PADDING: int = 16
    PANEL_CORNER_RADIUS: int = 12

    # Counter display
    COUNTER_SIZE: int = 48
    COUNTER_POSITION: Tuple[int, int] = (SCREEN_WIDTH - 100, 50)

    # Toast notifications
    TOAST_WIDTH: int = 200
    TOAST_HEIGHT: int = 40


@dataclass(frozen=True)
class AnimationConfig:
    """Animation timing and physics constants."""

    # Durations (in seconds)
    CARD_DEAL_DURATION: float = 0.35
    CARD_FLIP_DURATION: float = 0.25
    COUNTER_DURATION: float = 0.4
    TOAST_DURATION: float = 1.5
    BUTTON_HOVER_DURATION: float = 0.1

    # Physics
    SPRING_STIFFNESS: float = 180.0
    SPRING_DAMPING: float = 12.0

    # Screen shake
    SHAKE_DECAY: float = 0.9
    MAX_SHAKE_OFFSET: float = 10.0
    MAX_SHAKE_ROTATION: float = 2.0


# Global instances for easy import
COLORS = Colors()
DIMENSIONS = Dimensions()
ANIMATION = AnimationConfig()
