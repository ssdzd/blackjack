"""Interactive button component with hover and press states."""

from enum import Enum, auto
from typing import Callable, Optional, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.utils.math_utils import lerp


class ButtonState(Enum):
    """Visual state of a button."""

    NORMAL = auto()
    HOVERED = auto()
    PRESSED = auto()
    DISABLED = auto()


class Button:
    """An interactive button with hover/press animations.

    Features:
    - Smooth hover scale animation
    - Press depression effect
    - Customizable colors and text
    - Click callback
    """

    def __init__(
        self,
        x: float,
        y: float,
        width: float = None,
        height: float = None,
        text: str = "Button",
        font_size: int = 28,
        on_click: Optional[Callable[[], None]] = None,
        centered: bool = True,
        bg_color: Tuple[int, int, int] = None,
        hover_color: Tuple[int, int, int] = None,
        pressed_color: Tuple[int, int, int] = None,
        text_color: Tuple[int, int, int] = COLORS.TEXT_WHITE,
        border_color: Tuple[int, int, int] = None,
        corner_radius: int = None,
        enabled: bool = True,
    ):
        """Initialize a button.

        Args:
            x: X position (center if centered=True)
            y: Y position (center if centered=True)
            width: Button width (auto-sized if None)
            height: Button height (default if None)
            text: Button text
            font_size: Text font size
            on_click: Callback function when clicked
            centered: If True, x/y is center position
            bg_color: Normal background color
            hover_color: Hovered background color
            pressed_color: Pressed background color
            text_color: Text color
            border_color: Border color (None for no border)
            corner_radius: Corner radius (default if None)
            enabled: Whether button is interactive
        """
        self.text = text
        self.font_size = font_size
        self.on_click = on_click
        self.centered = centered
        self.enabled = enabled

        # Colors
        self.bg_color = bg_color or COLORS.BUTTON_DEFAULT
        self.hover_color = hover_color or COLORS.BUTTON_HOVER
        self.pressed_color = pressed_color or COLORS.BUTTON_PRESSED
        self.disabled_color = COLORS.BUTTON_DISABLED
        self.text_color = text_color
        self.border_color = border_color
        self.corner_radius = corner_radius or DIMENSIONS.BUTTON_CORNER_RADIUS

        # Font
        self._font: Optional[pygame.font.Font] = None

        # Calculate size (estimate if pygame not initialized)
        if width is None or height is None:
            try:
                font = self.font
                text_surface = font.render(text, True, text_color)
                auto_width = text_surface.get_width() + 40
                auto_height = text_surface.get_height() + 16
            except pygame.error:
                # Pygame not initialized, estimate size
                auto_width = len(text) * (font_size // 2) + 40
                auto_height = font_size + 16

        self.width = width if width is not None else auto_width
        self.height = height if height is not None else auto_height

        # Position
        if centered:
            self.x = x - self.width / 2
            self.y = y - self.height / 2
            self.center_x = x
            self.center_y = y
        else:
            self.x = x
            self.y = y
            self.center_x = x + self.width / 2
            self.center_y = y + self.height / 2

        # State
        self.state = ButtonState.NORMAL
        self._is_pressed = False

        # Animation
        self.scale = 1.0
        self.target_scale = 1.0
        self.y_offset = 0.0  # For press depression
        self.target_y_offset = 0.0

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, self.font_size)
        return self._font

    @property
    def rect(self) -> pygame.Rect:
        """Get the button's rectangle."""
        return pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))

    def set_text(self, text: str) -> None:
        """Change button text.

        Args:
            text: New button text
        """
        self.text = text

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the button.

        Args:
            enabled: Whether button should be enabled
        """
        self.enabled = enabled
        if not enabled:
            self.state = ButtonState.DISABLED
        else:
            self.state = ButtonState.NORMAL

    def contains_point(self, point: Tuple[float, float]) -> bool:
        """Check if a point is inside the button.

        Args:
            point: (x, y) position to check

        Returns:
            True if point is inside
        """
        return self.rect.collidepoint(point)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle a pygame event.

        Args:
            event: The pygame event

        Returns:
            True if event was consumed (clicked)
        """
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            if self.contains_point(event.pos):
                if not self._is_pressed:
                    self.state = ButtonState.HOVERED
                    self.target_scale = 1.05
            else:
                if not self._is_pressed:
                    self.state = ButtonState.NORMAL
                    self.target_scale = 1.0

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.contains_point(event.pos):
                self.state = ButtonState.PRESSED
                self._is_pressed = True
                self.target_scale = 0.95
                self.target_y_offset = 2
                return False  # Don't consume yet, wait for release

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self._is_pressed:
                self._is_pressed = False
                self.target_y_offset = 0

                if self.contains_point(event.pos):
                    self.state = ButtonState.HOVERED
                    self.target_scale = 1.05
                    if self.on_click:
                        self.on_click()
                    return True
                else:
                    self.state = ButtonState.NORMAL
                    self.target_scale = 1.0

        return False

    def update(self, dt: float) -> None:
        """Update button animations.

        Args:
            dt: Delta time in seconds
        """
        # Smooth scale
        scale_speed = 15.0
        self.scale += (self.target_scale - self.scale) * min(1.0, scale_speed * dt)

        # Smooth y offset
        offset_speed = 20.0
        self.y_offset += (self.target_y_offset - self.y_offset) * min(1.0, offset_speed * dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the button.

        Args:
            surface: Pygame surface to draw on
        """
        # Determine color based on state
        if not self.enabled:
            bg_color = self.disabled_color
            text_color = COLORS.TEXT_MUTED
        elif self.state == ButtonState.PRESSED:
            bg_color = self.pressed_color
            text_color = self.text_color
        elif self.state == ButtonState.HOVERED:
            bg_color = self.hover_color
            text_color = self.text_color
        else:
            bg_color = self.bg_color
            text_color = self.text_color

        # Calculate scaled dimensions
        scaled_width = int(self.width * self.scale)
        scaled_height = int(self.height * self.scale)
        draw_x = self.center_x - scaled_width / 2
        draw_y = self.center_y - scaled_height / 2 + self.y_offset

        # Create button surface
        button_surface = pygame.Surface((scaled_width, scaled_height), pygame.SRCALPHA)

        # Draw background
        rect = pygame.Rect(0, 0, scaled_width, scaled_height)
        pygame.draw.rect(button_surface, bg_color, rect, border_radius=self.corner_radius)

        # Draw border
        if self.border_color:
            pygame.draw.rect(
                button_surface,
                self.border_color,
                rect,
                width=2,
                border_radius=self.corner_radius,
            )

        # Draw text
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=(scaled_width // 2, scaled_height // 2))
        button_surface.blit(text_surface, text_rect)

        # Blit to main surface
        surface.blit(button_surface, (int(draw_x), int(draw_y)))


class ActionButton(Button):
    """Specialized button for game actions (Hit, Stand, etc.)."""

    def __init__(
        self,
        x: float,
        y: float,
        text: str,
        action: str,
        on_click: Optional[Callable[[], None]] = None,
        hotkey: Optional[str] = None,
        **kwargs,
    ):
        """Initialize an action button.

        Args:
            x: X position
            y: Y position
            text: Button text
            action: Action identifier
            on_click: Click callback
            hotkey: Keyboard shortcut hint
        """
        super().__init__(
            x=x,
            y=y,
            text=text,
            on_click=on_click,
            width=DIMENSIONS.BUTTON_WIDTH,
            height=DIMENSIONS.BUTTON_HEIGHT,
            **kwargs,
        )
        self.action = action
        self.hotkey = hotkey

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the action button with optional hotkey hint."""
        super().draw(surface)

        # Draw hotkey hint if present
        if self.hotkey and self.enabled:
            hint_font = pygame.font.Font(None, 18)
            hint_text = hint_font.render(f"[{self.hotkey}]", True, COLORS.TEXT_MUTED)
            hint_rect = hint_text.get_rect(
                centerx=int(self.center_x),
                top=int(self.y + self.height + 4 + self.y_offset),
            )
            surface.blit(hint_text, hint_rect)
