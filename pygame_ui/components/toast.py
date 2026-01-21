"""Floating toast notification system."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

import pygame

from pygame_ui.config import ANIMATION, COLORS, DIMENSIONS
from pygame_ui.utils.math_utils import lerp


class ToastType(Enum):
    """Types of toast notifications."""

    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    COUNT_UP = auto()
    COUNT_DOWN = auto()
    WIN = auto()
    LOSE = auto()
    PUSH = auto()


# Color mapping for toast types
TOAST_COLORS = {
    ToastType.INFO: COLORS.TEXT_WHITE,
    ToastType.SUCCESS: COLORS.COUNT_POSITIVE,
    ToastType.WARNING: COLORS.GOLD,
    ToastType.ERROR: COLORS.COUNT_NEGATIVE,
    ToastType.COUNT_UP: COLORS.COUNT_POSITIVE,
    ToastType.COUNT_DOWN: COLORS.COUNT_NEGATIVE,
    ToastType.WIN: COLORS.GOLD,
    ToastType.LOSE: COLORS.COUNT_NEGATIVE,
    ToastType.PUSH: COLORS.TEXT_MUTED,
}


@dataclass
class Toast:
    """A single floating toast notification."""

    text: str
    x: float
    y: float
    toast_type: ToastType = ToastType.INFO
    duration: float = ANIMATION.TOAST_DURATION
    font_size: int = 32

    # Animation state
    elapsed: float = field(default=0.0, init=False)
    alpha: float = field(default=255.0, init=False)
    offset_y: float = field(default=0.0, init=False)
    scale: float = field(default=0.5, init=False)
    completed: bool = field(default=False, init=False)

    # Cached font
    _font: Optional[pygame.font.Font] = field(default=None, init=False)

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, self.font_size)
        return self._font

    @property
    def color(self) -> Tuple[int, int, int]:
        return TOAST_COLORS.get(self.toast_type, COLORS.TEXT_WHITE)

    def update(self, dt: float) -> bool:
        """Update toast animation.

        Args:
            dt: Delta time in seconds

        Returns:
            True if still active, False if completed
        """
        self.elapsed += dt
        progress = self.elapsed / self.duration

        if progress >= 1.0:
            self.completed = True
            return False

        # Ease in scale at start
        if progress < 0.1:
            self.scale = lerp(0.5, 1.2, progress / 0.1)
        elif progress < 0.2:
            self.scale = lerp(1.2, 1.0, (progress - 0.1) / 0.1)
        else:
            self.scale = 1.0

        # Float upward
        self.offset_y = -progress * 60

        # Fade out in last 30%
        if progress > 0.7:
            fade_progress = (progress - 0.7) / 0.3
            self.alpha = lerp(255, 0, fade_progress)
        else:
            self.alpha = 255

        return True

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the toast.

        Args:
            surface: Pygame surface to draw on
        """
        if self.completed:
            return

        # Render text
        rendered = self.font.render(self.text, True, self.color)

        # Apply scale
        if self.scale != 1.0:
            new_size = (
                max(1, int(rendered.get_width() * self.scale)),
                max(1, int(rendered.get_height() * self.scale)),
            )
            rendered = pygame.transform.scale(rendered, new_size)

        # Apply alpha
        rendered.set_alpha(int(self.alpha))

        # Position with offset
        rect = rendered.get_rect(center=(int(self.x), int(self.y + self.offset_y)))
        surface.blit(rendered, rect)


class ToastManager:
    """Manages multiple toast notifications."""

    def __init__(self, max_toasts: int = 10):
        self.toasts: List[Toast] = []
        self.max_toasts = max_toasts

    def spawn(
        self,
        text: str,
        x: float,
        y: float,
        toast_type: ToastType = ToastType.INFO,
        duration: float = None,
        font_size: int = 32,
    ) -> Toast:
        """Spawn a new toast notification.

        Args:
            text: Text to display
            x: X position
            y: Y position
            toast_type: Type of toast (affects color)
            duration: How long to show (default from config)
            font_size: Font size

        Returns:
            The created toast
        """
        if duration is None:
            duration = ANIMATION.TOAST_DURATION

        toast = Toast(
            text=text,
            x=x,
            y=y,
            toast_type=toast_type,
            duration=duration,
            font_size=font_size,
        )

        self.toasts.append(toast)

        # Remove oldest if over limit
        while len(self.toasts) > self.max_toasts:
            self.toasts.pop(0)

        return toast

    def spawn_count_change(
        self,
        amount: int,
        x: float,
        y: float,
    ) -> Toast:
        """Spawn a toast for count change (+1, -1, etc).

        Args:
            amount: The count change amount
            x: X position
            y: Y position

        Returns:
            The created toast
        """
        if amount > 0:
            text = f"+{amount}"
            toast_type = ToastType.COUNT_UP
        elif amount < 0:
            text = str(amount)
            toast_type = ToastType.COUNT_DOWN
        else:
            text = "0"
            toast_type = ToastType.INFO

        return self.spawn(
            text=text,
            x=x,
            y=y,
            toast_type=toast_type,
            font_size=28,
            duration=1.0,
        )

    def spawn_result(
        self,
        result: str,
        x: float,
        y: float,
        amount: Optional[float] = None,
    ) -> Toast:
        """Spawn a toast for game result.

        Args:
            result: "win", "lose", or "push"
            x: X position
            y: Y position
            amount: Optional money amount

        Returns:
            The created toast
        """
        result_lower = result.lower()

        if result_lower == "win":
            text = f"WIN! +${amount:.0f}" if amount else "WIN!"
            toast_type = ToastType.WIN
        elif result_lower == "lose":
            text = f"LOSE -${abs(amount):.0f}" if amount else "LOSE"
            toast_type = ToastType.LOSE
        elif result_lower == "push":
            text = "PUSH"
            toast_type = ToastType.PUSH
        elif result_lower == "blackjack":
            text = f"BLACKJACK! +${amount:.0f}" if amount else "BLACKJACK!"
            toast_type = ToastType.WIN
        else:
            text = result
            toast_type = ToastType.INFO

        return self.spawn(
            text=text,
            x=x,
            y=y,
            toast_type=toast_type,
            font_size=40,
            duration=2.0,
        )

    def update(self, dt: float) -> None:
        """Update all toasts.

        Args:
            dt: Delta time in seconds
        """
        self.toasts = [toast for toast in self.toasts if toast.update(dt)]

    def draw(self, surface: pygame.Surface) -> None:
        """Draw all toasts.

        Args:
            surface: Pygame surface to draw on
        """
        for toast in self.toasts:
            toast.draw(surface)

    def clear(self) -> None:
        """Remove all toasts."""
        self.toasts.clear()
