"""Panel component with rounded borders and semi-transparent background."""

from typing import Optional, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS


class Panel:
    """A rounded rectangle panel with border and optional transparency.

    Use for containing UI elements, info displays, etc.
    """

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        bg_color: Tuple[int, int, int] = (30, 30, 40),
        bg_alpha: int = 200,
        border_color: Tuple[int, int, int] = COLORS.SILVER,
        border_width: int = 2,
        corner_radius: int = None,
        centered: bool = True,
    ):
        """Initialize a panel.

        Args:
            x: X position (center if centered=True, else top-left)
            y: Y position (center if centered=True, else top-left)
            width: Panel width
            height: Panel height
            bg_color: Background color (RGB)
            bg_alpha: Background transparency (0-255)
            border_color: Border color (RGB)
            border_width: Border thickness (0 for no border)
            corner_radius: Rounded corner radius (None for default)
            centered: If True, x/y is center; if False, top-left
        """
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.bg_alpha = bg_alpha
        self.border_color = border_color
        self.border_width = border_width
        self.corner_radius = corner_radius or DIMENSIONS.PANEL_CORNER_RADIUS
        self.centered = centered

        # Calculate position
        if centered:
            self.x = x - width / 2
            self.y = y - height / 2
            self.center_x = x
            self.center_y = y
        else:
            self.x = x
            self.y = y
            self.center_x = x + width / 2
            self.center_y = y + height / 2

        # Cached surface
        self._surface: Optional[pygame.Surface] = None
        self._needs_redraw = True

    @property
    def rect(self) -> pygame.Rect:
        """Get the panel's rectangle."""
        return pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))

    def set_position(self, x: float, y: float) -> None:
        """Set panel position.

        Args:
            x: New x position
            y: New y position
        """
        if self.centered:
            self.x = x - self.width / 2
            self.y = y - self.height / 2
            self.center_x = x
            self.center_y = y
        else:
            self.x = x
            self.y = y
            self.center_x = x + self.width / 2
            self.center_y = y + self.height / 2

    def set_size(self, width: float, height: float) -> None:
        """Set panel size.

        Args:
            width: New width
            height: New height
        """
        self.width = width
        self.height = height
        self._needs_redraw = True

        # Recalculate center
        if self.centered:
            self.x = self.center_x - width / 2
            self.y = self.center_y - height / 2
        else:
            self.center_x = self.x + width / 2
            self.center_y = self.y + height / 2

    def contains_point(self, point: Tuple[float, float]) -> bool:
        """Check if a point is inside the panel.

        Args:
            point: (x, y) position to check

        Returns:
            True if point is inside
        """
        return self.rect.collidepoint(point)

    def _render(self) -> pygame.Surface:
        """Render the panel surface."""
        surface = pygame.Surface((int(self.width), int(self.height)), pygame.SRCALPHA)

        # Background
        bg_rect = pygame.Rect(0, 0, int(self.width), int(self.height))
        bg_color_with_alpha = (*self.bg_color, self.bg_alpha)
        pygame.draw.rect(
            surface, bg_color_with_alpha, bg_rect, border_radius=self.corner_radius
        )

        # Border
        if self.border_width > 0:
            pygame.draw.rect(
                surface,
                self.border_color,
                bg_rect,
                width=self.border_width,
                border_radius=self.corner_radius,
            )

        return surface

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the panel.

        Args:
            surface: Pygame surface to draw on
        """
        if self._needs_redraw or self._surface is None:
            self._surface = self._render()
            self._needs_redraw = False

        surface.blit(self._surface, (int(self.x), int(self.y)))


class InfoPanel(Panel):
    """A panel that displays labeled information."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float = 200,
        title: str = "",
        **kwargs,
    ):
        super().__init__(x, y, width, 80, **kwargs)
        self.title = title
        self.content_lines: list[Tuple[str, str]] = []  # (label, value) pairs

        self._title_font: Optional[pygame.font.Font] = None
        self._content_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 28)
        return self._title_font

    @property
    def content_font(self) -> pygame.font.Font:
        if self._content_font is None:
            self._content_font = pygame.font.Font(None, 24)
        return self._content_font

    def set_content(self, lines: list[Tuple[str, str]]) -> None:
        """Set content lines.

        Args:
            lines: List of (label, value) tuples
        """
        self.content_lines = lines
        # Adjust height based on content
        line_height = 22
        title_height = 30 if self.title else 0
        padding = DIMENSIONS.PANEL_PADDING * 2
        self.set_size(self.width, title_height + len(lines) * line_height + padding)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the info panel with content."""
        super().draw(surface)

        y_offset = int(self.y) + DIMENSIONS.PANEL_PADDING

        # Draw title
        if self.title:
            title_rendered = self.title_font.render(self.title, True, COLORS.GOLD)
            title_rect = title_rendered.get_rect(
                centerx=int(self.center_x), top=y_offset
            )
            surface.blit(title_rendered, title_rect)
            y_offset += 28

        # Draw content lines
        for label, value in self.content_lines:
            # Label on left
            label_rendered = self.content_font.render(label, True, COLORS.TEXT_MUTED)
            surface.blit(label_rendered, (int(self.x) + DIMENSIONS.PANEL_PADDING, y_offset))

            # Value on right
            value_rendered = self.content_font.render(value, True, COLORS.TEXT_WHITE)
            value_rect = value_rendered.get_rect(
                right=int(self.x + self.width) - DIMENSIONS.PANEL_PADDING,
                top=y_offset,
            )
            surface.blit(value_rendered, value_rect)

            y_offset += 22
