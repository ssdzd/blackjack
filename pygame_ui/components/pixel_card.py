"""Pixel art card renderer for Balatro-style visuals."""

from typing import Dict, Optional, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS


class PixelCardRenderer:
    """Generates pixel-art style playing cards.

    Creates procedurally generated card faces with:
    - Pixel art suit symbols
    - Retro-style value text
    - Decorative card backs
    """

    # Card dimensions
    WIDTH = DIMENSIONS.CARD_WIDTH
    HEIGHT = DIMENSIONS.CARD_HEIGHT

    # Colors for card rendering
    CARD_BG = COLORS.CARD_WHITE
    CARD_RED = (200, 50, 50)
    CARD_BLACK = (30, 30, 35)
    CARD_BACK_PRIMARY = (65, 85, 130)
    CARD_BACK_SECONDARY = (85, 105, 150)
    CARD_BACK_ACCENT = (100, 120, 165)
    CARD_BORDER = (40, 40, 45)

    # Pixel art suit patterns (8x8)
    SUIT_PATTERNS = {
        "hearts": [
            "  oo  oo  ",
            " oooooooo ",
            "oooooooooo",
            "oooooooooo",
            "oooooooooo",
            " oooooooo ",
            "  oooooo  ",
            "   oooo   ",
            "    oo    ",
        ],
        "diamonds": [
            "    oo    ",
            "   oooo   ",
            "  oooooo  ",
            " oooooooo ",
            "oooooooooo",
            " oooooooo ",
            "  oooooo  ",
            "   oooo   ",
            "    oo    ",
        ],
        "clubs": [
            "    oo    ",
            "   oooo   ",
            "   oooo   ",
            " oo oo oo ",
            "oooooooooo",
            "oooooooooo",
            " oooooooo ",
            "    oo    ",
            "   oooo   ",
        ],
        "spades": [
            "    oo    ",
            "   oooo   ",
            "  oooooo  ",
            " oooooooo ",
            "oooooooooo",
            "oooooooooo",
            "    oo    ",
            "   oooo   ",
            "   oooo   ",
        ],
    }

    # Pixel art numbers (5x7 for most, larger for face cards)
    VALUE_PATTERNS = {
        "A": [
            "  o  ",
            " ooo ",
            "oo oo",
            "ooooo",
            "oo oo",
            "oo oo",
            "oo oo",
        ],
        "2": [
            " ooo ",
            "oo oo",
            "   oo",
            "  oo ",
            " oo  ",
            "oo   ",
            "ooooo",
        ],
        "3": [
            " ooo ",
            "oo oo",
            "   oo",
            "  oo ",
            "   oo",
            "oo oo",
            " ooo ",
        ],
        "4": [
            "   oo",
            "  ooo",
            " o oo",
            "o  oo",
            "ooooo",
            "   oo",
            "   oo",
        ],
        "5": [
            "ooooo",
            "oo   ",
            "oooo ",
            "   oo",
            "   oo",
            "oo oo",
            " ooo ",
        ],
        "6": [
            " ooo ",
            "oo   ",
            "oo   ",
            "oooo ",
            "oo oo",
            "oo oo",
            " ooo ",
        ],
        "7": [
            "ooooo",
            "   oo",
            "  oo ",
            "  oo ",
            " oo  ",
            " oo  ",
            " oo  ",
        ],
        "8": [
            " ooo ",
            "oo oo",
            "oo oo",
            " ooo ",
            "oo oo",
            "oo oo",
            " ooo ",
        ],
        "9": [
            " ooo ",
            "oo oo",
            "oo oo",
            " oooo",
            "   oo",
            "   oo",
            " ooo ",
        ],
        "10": [
            "o  ooo ",
            "o oo oo",
            "o oo oo",
            "o oo oo",
            "o oo oo",
            "o oo oo",
            "o  ooo ",
        ],
        "J": [
            "   oo",
            "   oo",
            "   oo",
            "   oo",
            "o  oo",
            "oo oo",
            " ooo ",
        ],
        "Q": [
            " ooo ",
            "oo oo",
            "oo oo",
            "oo oo",
            "oo oo",
            " ooo ",
            "   oo",
        ],
        "K": [
            "oo  o",
            "oo oo",
            "oooo ",
            "ooo  ",
            "oooo ",
            "oo oo",
            "oo  o",
        ],
    }

    def __init__(self):
        """Initialize the renderer with cached surfaces."""
        self._card_cache: Dict[str, pygame.Surface] = {}
        self._back_surface: Optional[pygame.Surface] = None

    def _get_suit_color(self, suit: str) -> Tuple[int, int, int]:
        """Get the color for a suit."""
        if suit in ("hearts", "diamonds"):
            return self.CARD_RED
        return self.CARD_BLACK

    def _draw_pattern(
        self,
        surface: pygame.Surface,
        pattern: list,
        x: int,
        y: int,
        color: Tuple[int, int, int],
        pixel_size: int = 2,
    ) -> None:
        """Draw a pixel pattern on a surface."""
        for row_idx, row in enumerate(pattern):
            for col_idx, char in enumerate(row):
                if char == "o":
                    rect = pygame.Rect(
                        x + col_idx * pixel_size,
                        y + row_idx * pixel_size,
                        pixel_size,
                        pixel_size,
                    )
                    pygame.draw.rect(surface, color, rect)

    def _draw_suit_symbol(
        self,
        surface: pygame.Surface,
        suit: str,
        x: int,
        y: int,
        size: int = 2,
    ) -> None:
        """Draw a suit symbol centered at position."""
        pattern = self.SUIT_PATTERNS.get(suit, self.SUIT_PATTERNS["spades"])
        color = self._get_suit_color(suit)

        # Calculate centering offset
        pattern_width = len(pattern[0]) * size
        pattern_height = len(pattern) * size
        draw_x = x - pattern_width // 2
        draw_y = y - pattern_height // 2

        self._draw_pattern(surface, pattern, draw_x, draw_y, color, size)

    def _draw_value(
        self,
        surface: pygame.Surface,
        value: str,
        x: int,
        y: int,
        color: Tuple[int, int, int],
        size: int = 2,
    ) -> None:
        """Draw a value (A, 2, K, etc) at position."""
        pattern = self.VALUE_PATTERNS.get(value, self.VALUE_PATTERNS["A"])

        # Calculate centering offset
        pattern_width = len(pattern[0]) * size
        pattern_height = len(pattern) * size
        draw_x = x - pattern_width // 2
        draw_y = y - pattern_height // 2

        self._draw_pattern(surface, pattern, draw_x, draw_y, color, size)

    def _draw_card_back_pattern(self, surface: pygame.Surface) -> None:
        """Draw a decorative card back pattern."""
        width, height = surface.get_size()

        # Fill with primary color
        surface.fill(self.CARD_BACK_PRIMARY)

        # Draw diamond pattern
        diamond_size = 12
        for y in range(0, height, diamond_size):
            offset = (y // diamond_size) % 2 * (diamond_size // 2)
            for x in range(-diamond_size, width + diamond_size, diamond_size):
                cx = x + offset
                cy = y

                # Draw small diamond
                points = [
                    (cx, cy - diamond_size // 3),
                    (cx + diamond_size // 3, cy),
                    (cx, cy + diamond_size // 3),
                    (cx - diamond_size // 3, cy),
                ]
                pygame.draw.polygon(surface, self.CARD_BACK_SECONDARY, points)

        # Draw border frame
        border_width = 6
        inner_rect = pygame.Rect(
            border_width, border_width,
            width - 2 * border_width, height - 2 * border_width
        )
        pygame.draw.rect(surface, self.CARD_BACK_ACCENT, inner_rect, width=2, border_radius=4)

        # Draw outer border
        pygame.draw.rect(surface, self.CARD_BORDER, (0, 0, width, height), width=2, border_radius=DIMENSIONS.CARD_CORNER_RADIUS)

    def render_card_back(self) -> pygame.Surface:
        """Render the card back design."""
        if self._back_surface is not None:
            return self._back_surface

        surface = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)

        # Round corners
        pygame.draw.rect(
            surface,
            self.CARD_BACK_PRIMARY,
            (0, 0, self.WIDTH, self.HEIGHT),
            border_radius=DIMENSIONS.CARD_CORNER_RADIUS,
        )

        self._draw_card_back_pattern(surface)

        self._back_surface = surface
        return surface

    def render_card_face(self, value: str, suit: str) -> pygame.Surface:
        """Render a card face.

        Args:
            value: Card value (A, 2-10, J, Q, K)
            suit: Card suit (hearts, diamonds, clubs, spades)
        """
        cache_key = f"{value}_{suit}"
        if cache_key in self._card_cache:
            return self._card_cache[cache_key]

        surface = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)

        # Card background with rounded corners
        pygame.draw.rect(
            surface,
            self.CARD_BG,
            (0, 0, self.WIDTH, self.HEIGHT),
            border_radius=DIMENSIONS.CARD_CORNER_RADIUS,
        )

        # Border
        pygame.draw.rect(
            surface,
            self.CARD_BORDER,
            (0, 0, self.WIDTH, self.HEIGHT),
            width=2,
            border_radius=DIMENSIONS.CARD_CORNER_RADIUS,
        )

        color = self._get_suit_color(suit)

        # Top-left corner value and suit
        self._draw_value(surface, value, 15, 18, color, size=2)
        self._draw_suit_symbol(surface, suit, 15, 40, size=1)

        # Bottom-right corner (rotated 180)
        self._draw_value(surface, value, self.WIDTH - 15, self.HEIGHT - 18, color, size=2)
        self._draw_suit_symbol(surface, suit, self.WIDTH - 15, self.HEIGHT - 40, size=1)

        # Center suit symbol (larger)
        self._draw_suit_symbol(surface, suit, self.WIDTH // 2, self.HEIGHT // 2, size=3)

        # Add pip patterns for number cards
        if value in ("2", "3", "4", "5", "6", "7", "8", "9", "10"):
            self._draw_pip_pattern(surface, value, suit)

        self._card_cache[cache_key] = surface
        return surface

    def _draw_pip_pattern(self, surface: pygame.Surface, value: str, suit: str) -> None:
        """Draw the pip pattern for number cards."""
        # Positions are relative to card center
        cx, cy = self.WIDTH // 2, self.HEIGHT // 2
        pip_size = 2

        # Define pip positions for each value
        pip_layouts = {
            "2": [(0, -35), (0, 35)],
            "3": [(0, -35), (0, 0), (0, 35)],
            "4": [(-15, -25), (15, -25), (-15, 25), (15, 25)],
            "5": [(-15, -25), (15, -25), (0, 0), (-15, 25), (15, 25)],
            "6": [(-15, -30), (15, -30), (-15, 0), (15, 0), (-15, 30), (15, 30)],
            "7": [(-15, -30), (15, -30), (0, -10), (-15, 10), (15, 10), (-15, 35), (15, 35)],
            "8": [(-15, -30), (15, -30), (-15, -10), (15, -10), (-15, 10), (15, 10), (-15, 30), (15, 30)],
            "9": [(-15, -32), (15, -32), (-15, -11), (15, -11), (0, 0), (-15, 11), (15, 11), (-15, 32), (15, 32)],
            "10": [(-15, -35), (15, -35), (0, -20), (-15, -5), (15, -5), (-15, 10), (15, 10), (0, 25), (-15, 40), (15, 40)],
        }

        positions = pip_layouts.get(value, [])
        for dx, dy in positions:
            self._draw_suit_symbol(surface, suit, cx + dx, cy + dy, size=pip_size)

    def get_card_surface(self, value: str = None, suit: str = None, face_up: bool = True) -> pygame.Surface:
        """Get a card surface.

        Args:
            value: Card value (A, 2-10, J, Q, K). Required if face_up=True.
            suit: Card suit. Required if face_up=True.
            face_up: If True, return card face; if False, return card back.
        """
        if not face_up:
            return self.render_card_back()
        return self.render_card_face(value or "A", suit or "spades")


# Global renderer instance
_renderer: Optional[PixelCardRenderer] = None


def get_card_renderer() -> PixelCardRenderer:
    """Get the global card renderer instance."""
    global _renderer
    if _renderer is None:
        _renderer = PixelCardRenderer()
    return _renderer
