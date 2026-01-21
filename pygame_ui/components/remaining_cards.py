"""Remaining cards display component showing card counts by suit and rank."""

from collections import Counter
from typing import Optional, List

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from core.cards import Card, Suit, Rank


# Ordered ranks for display columns (A through K)
RANK_ORDER = [
    Rank.ACE, Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX,
    Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING,
]

# Ordered suits for display rows
SUIT_ORDER = [Suit.SPADES, Suit.HEARTS, Suit.DIAMONDS, Suit.CLUBS]

# Suit symbols and colors
SUIT_SYMBOLS = {
    Suit.SPADES: "♠",
    Suit.HEARTS: "♥",
    Suit.DIAMONDS: "♦",
    Suit.CLUBS: "♣",
}

SUIT_COLORS = {
    Suit.SPADES: COLORS.TEXT_WHITE,
    Suit.HEARTS: COLORS.CARD_RED,
    Suit.DIAMONDS: COLORS.CARD_RED,
    Suit.CLUBS: COLORS.TEXT_WHITE,
}


class RemainingCardsDisplay:
    """Displays remaining cards in the shoe organized by suit and rank.

    Shows a grid with suits as rows and ranks as columns.
    Color codes cells based on card depletion level.
    """

    # Cell dimensions
    CELL_WIDTH = 22
    CELL_HEIGHT = 20
    HEADER_HEIGHT = 24
    SUIT_COL_WIDTH = 24
    TITLE_HEIGHT = 24

    # Color coding thresholds (for 6-deck shoe where max per card is 6)
    COLOR_DEPLETED = (80, 80, 80)      # 0 cards - dark gray
    COLOR_LOW = (220, 180, 60)          # 1-2 cards - amber warning
    COLOR_MEDIUM = (180, 180, 180)      # 3-4 cards - light gray
    COLOR_FULL = COLORS.TEXT_WHITE      # 5-6 cards - white

    BG_DEPLETED = (40, 40, 45)          # Darker background for depleted

    def __init__(
        self,
        x: float,
        y: float,
        num_decks: int = 6,
    ):
        """Initialize the remaining cards display.

        Args:
            x: X position (top-left corner)
            y: Y position (top-left corner)
            num_decks: Number of decks in the shoe
        """
        self.x = x
        self.y = y
        self.num_decks = num_decks

        # Calculate dimensions
        self.width = self.SUIT_COL_WIDTH + (len(RANK_ORDER) * self.CELL_WIDTH) + 8
        self.height = self.TITLE_HEIGHT + self.HEADER_HEIGHT + (len(SUIT_ORDER) * self.CELL_HEIGHT) + 8

        # Card counts: (Suit, Rank) -> count
        self._counts: Counter = Counter()
        self._reset_counts()

        # Visibility
        self._visible = False

        # Cached fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._header_font: Optional[pygame.font.Font] = None
        self._cell_font: Optional[pygame.font.Font] = None
        self._suit_font: Optional[pygame.font.Font] = None

        # Cached surface for performance
        self._surface: Optional[pygame.Surface] = None
        self._needs_redraw = True

    def _reset_counts(self) -> None:
        """Reset counts to full shoe values."""
        self._counts.clear()
        for suit in Suit:
            for rank in Rank:
                self._counts[(suit, rank)] = self.num_decks
        self._needs_redraw = True

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 20)
        return self._title_font

    @property
    def header_font(self) -> pygame.font.Font:
        if self._header_font is None:
            self._header_font = pygame.font.Font(None, 18)
        return self._header_font

    @property
    def cell_font(self) -> pygame.font.Font:
        if self._cell_font is None:
            self._cell_font = pygame.font.Font(None, 18)
        return self._cell_font

    @property
    def suit_font(self) -> pygame.font.Font:
        if self._suit_font is None:
            self._suit_font = pygame.font.Font(None, 22)
        return self._suit_font

    def show(self) -> None:
        """Show the display."""
        self._visible = True

    def hide(self) -> None:
        """Hide the display."""
        self._visible = False

    def toggle(self) -> bool:
        """Toggle visibility, returns new state."""
        self._visible = not self._visible
        return self._visible

    def update_from_shoe(self, shoe_cards: List[Card]) -> None:
        """Update counts from shoe's remaining cards.

        Args:
            shoe_cards: List of Card objects remaining in the shoe
        """
        self._counts.clear()
        for card in shoe_cards:
            self._counts[(card.suit, card.rank)] += 1
        self._needs_redraw = True

    def _get_count_color(self, count: int) -> tuple:
        """Get the text color based on card count."""
        if count == 0:
            return self.COLOR_DEPLETED
        elif count <= 2:
            return self.COLOR_LOW
        elif count <= 4:
            return self.COLOR_MEDIUM
        else:
            return self.COLOR_FULL

    def _render(self) -> pygame.Surface:
        """Render the display to a surface."""
        surface = pygame.Surface((int(self.width), int(self.height)), pygame.SRCALPHA)

        # Background panel
        bg_rect = pygame.Rect(0, 0, int(self.width), int(self.height))
        pygame.draw.rect(surface, (30, 30, 40, 220), bg_rect, border_radius=8)
        pygame.draw.rect(surface, COLORS.SILVER, bg_rect, width=1, border_radius=8)

        # Title
        title_text = self.title_font.render("REMAINING CARDS", True, COLORS.GOLD)
        title_rect = title_text.get_rect(centerx=self.width // 2, top=4)
        surface.blit(title_text, title_rect)

        # Header row (rank labels)
        header_y = self.TITLE_HEIGHT
        x_offset = self.SUIT_COL_WIDTH + 4

        for rank in RANK_ORDER:
            rank_str = str(rank)
            text = self.header_font.render(rank_str, True, COLORS.TEXT_MUTED)
            rect = text.get_rect(
                centerx=x_offset + self.CELL_WIDTH // 2,
                centery=header_y + self.HEADER_HEIGHT // 2,
            )
            surface.blit(text, rect)
            x_offset += self.CELL_WIDTH

        # Data rows (suit + counts)
        row_y = self.TITLE_HEIGHT + self.HEADER_HEIGHT

        for suit in SUIT_ORDER:
            # Suit symbol
            suit_text = self.suit_font.render(SUIT_SYMBOLS[suit], True, SUIT_COLORS[suit])
            suit_rect = suit_text.get_rect(
                centerx=4 + self.SUIT_COL_WIDTH // 2,
                centery=row_y + self.CELL_HEIGHT // 2,
            )
            surface.blit(suit_text, suit_rect)

            # Count cells
            x_offset = self.SUIT_COL_WIDTH + 4
            for rank in RANK_ORDER:
                count = self._counts.get((suit, rank), 0)

                cell_rect = pygame.Rect(
                    x_offset, row_y,
                    self.CELL_WIDTH - 1, self.CELL_HEIGHT - 1,
                )

                # Draw darker background for depleted cards
                if count == 0:
                    pygame.draw.rect(surface, self.BG_DEPLETED, cell_rect, border_radius=2)

                # Draw count
                color = self._get_count_color(count)
                count_text = self.cell_font.render(str(count), True, color)
                count_rect = count_text.get_rect(
                    centerx=x_offset + self.CELL_WIDTH // 2,
                    centery=row_y + self.CELL_HEIGHT // 2,
                )
                surface.blit(count_text, count_rect)

                x_offset += self.CELL_WIDTH

            row_y += self.CELL_HEIGHT

        return surface

    def update(self, dt: float) -> None:
        """Update the display (no-op for now, but allows for future animations)."""
        pass

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the display to the surface."""
        if not self._visible:
            return

        if self._needs_redraw or self._surface is None:
            self._surface = self._render()
            self._needs_redraw = False

        surface.blit(self._surface, (int(self.x), int(self.y)))
