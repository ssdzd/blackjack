"""Animated counter components with spring physics."""

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from pygame_ui.config import ANIMATION, COLORS, DIMENSIONS
from pygame_ui.utils.math_utils import lerp, clamp


@dataclass
class SpringState:
    """State for spring physics simulation."""

    value: float = 0.0
    velocity: float = 0.0
    target: float = 0.0


class AnimatedCounter:
    """A number counter with spring-based animation.

    Features:
    - Smooth spring interpolation to target value
    - Scale pop on value change
    - Color flash effect
    """

    def __init__(
        self,
        x: float,
        y: float,
        initial_value: float = 0,
        font_size: int = 48,
        color: Tuple[int, int, int] = COLORS.TEXT_WHITE,
        prefix: str = "",
        suffix: str = "",
    ):
        self.x = x
        self.y = y
        self.font_size = font_size
        self.base_color = color
        self.current_color = color
        self.prefix = prefix
        self.suffix = suffix

        # Spring physics for value
        self.spring = SpringState(
            value=float(initial_value),
            target=float(initial_value),
        )

        # Visual effects
        self.scale = 1.0
        self.target_scale = 1.0
        self.flash_intensity = 0.0  # 0-1, for color flash
        self.flash_color: Optional[Tuple[int, int, int]] = None

        # Configuration
        self.stiffness = ANIMATION.SPRING_STIFFNESS
        self.damping = ANIMATION.SPRING_DAMPING
        self.show_decimals = False
        self.decimal_places = 0

        # Font
        self._font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, self.font_size)
        return self._font

    @property
    def value(self) -> float:
        return self.spring.target

    @value.setter
    def value(self, new_value: float) -> None:
        self.set_value(new_value)

    @property
    def display_value(self) -> float:
        """The current animated display value."""
        return self.spring.value

    def set_value(
        self,
        new_value: float,
        animate: bool = True,
        flash_color: Optional[Tuple[int, int, int]] = None,
    ) -> None:
        """Set the counter's target value.

        Args:
            new_value: The new target value
            animate: Whether to animate the transition
            flash_color: Optional color to flash on change
        """
        old_value = self.spring.target
        self.spring.target = float(new_value)

        if not animate:
            self.spring.value = float(new_value)
            self.spring.velocity = 0.0
            return

        # Trigger scale pop if value changed significantly
        if abs(new_value - old_value) > 0.01:
            self.target_scale = 1.3
            if flash_color:
                self.flash_color = flash_color
                self.flash_intensity = 1.0

    def increment(self, amount: float = 1, flash_color: Optional[Tuple[int, int, int]] = None) -> None:
        """Increment the counter value."""
        self.set_value(self.spring.target + amount, flash_color=flash_color)

    def decrement(self, amount: float = 1, flash_color: Optional[Tuple[int, int, int]] = None) -> None:
        """Decrement the counter value."""
        self.set_value(self.spring.target - amount, flash_color=flash_color)

    def update(self, dt: float) -> None:
        """Update spring physics and effects.

        Args:
            dt: Delta time in seconds
        """
        # Spring physics for value
        spring = self.spring
        force = (spring.target - spring.value) * self.stiffness
        spring.velocity += force * dt
        spring.velocity *= (1.0 - self.damping * dt)
        spring.value += spring.velocity * dt

        # Snap to target if close enough
        if abs(spring.target - spring.value) < 0.01 and abs(spring.velocity) < 0.1:
            spring.value = spring.target
            spring.velocity = 0.0

        # Scale animation (quick snap back)
        scale_speed = 12.0
        self.scale += (self.target_scale - self.scale) * min(1.0, scale_speed * dt)
        if self.target_scale > 1.0:
            self.target_scale = lerp(self.target_scale, 1.0, min(1.0, 8.0 * dt))

        # Flash decay
        if self.flash_intensity > 0:
            self.flash_intensity = max(0, self.flash_intensity - dt * 4.0)
            if self.flash_color:
                self.current_color = tuple(
                    int(lerp(b, f, self.flash_intensity))
                    for b, f in zip(self.base_color, self.flash_color)
                )
        else:
            self.current_color = self.base_color

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the counter.

        Args:
            surface: Pygame surface to draw on
        """
        # Format value
        if self.show_decimals:
            value_str = f"{self.spring.value:.{self.decimal_places}f}"
        else:
            value_str = str(int(round(self.spring.value)))

        text = f"{self.prefix}{value_str}{self.suffix}"

        # Render text
        rendered = self.font.render(text, True, self.current_color)

        # Apply scale
        if self.scale != 1.0:
            new_size = (
                int(rendered.get_width() * self.scale),
                int(rendered.get_height() * self.scale),
            )
            rendered = pygame.transform.scale(rendered, new_size)

        # Center on position
        rect = rendered.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rendered, rect)


class CountDisplay(AnimatedCounter):
    """Specialized counter for card counting display.

    Changes color based on positive/negative/neutral value.
    """

    def __init__(
        self,
        x: float,
        y: float,
        initial_value: float = 0,
        font_size: int = 56,
        label: str = "COUNT",
    ):
        super().__init__(
            x=x,
            y=y,
            initial_value=initial_value,
            font_size=font_size,
            color=COLORS.COUNT_NEUTRAL,
        )
        self.label = label
        self.label_font_size = font_size // 2
        self._label_font: Optional[pygame.font.Font] = None

        # Color thresholds
        self.positive_color = COLORS.COUNT_POSITIVE
        self.negative_color = COLORS.COUNT_NEGATIVE
        self.neutral_color = COLORS.COUNT_NEUTRAL

        # Show + sign for positive
        self.show_sign = True

    @property
    def label_font(self) -> pygame.font.Font:
        if self._label_font is None:
            self._label_font = pygame.font.Font(None, self.label_font_size)
        return self._label_font

    def update(self, dt: float) -> None:
        """Update with color based on value."""
        super().update(dt)

        # Update base color based on target value
        if self.spring.target > 0.5:
            self.base_color = self.positive_color
        elif self.spring.target < -0.5:
            self.base_color = self.negative_color
        else:
            self.base_color = self.neutral_color

        # Apply to current color if not flashing
        if self.flash_intensity <= 0:
            self.current_color = self.base_color

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the count display with label."""
        # Draw label above
        label_rendered = self.label_font.render(self.label, True, COLORS.TEXT_MUTED)
        label_rect = label_rendered.get_rect(center=(int(self.x), int(self.y) - 35))
        surface.blit(label_rendered, label_rect)

        # Format value with sign
        value = self.spring.value
        if self.show_sign and value > 0:
            prefix = "+"
        else:
            prefix = ""

        # Store original prefix, render, restore
        original_prefix = self.prefix
        self.prefix = prefix
        super().draw(surface)
        self.prefix = original_prefix


class BankrollDisplay(AnimatedCounter):
    """Specialized counter for money/bankroll display."""

    def __init__(
        self,
        x: float,
        y: float,
        initial_value: float = 1000,
        font_size: int = 42,
    ):
        super().__init__(
            x=x,
            y=y,
            initial_value=initial_value,
            font_size=font_size,
            color=COLORS.GOLD,
            prefix="$",
        )
        self.label = "BANKROLL"
        self.label_font_size = font_size // 2
        self._label_font: Optional[pygame.font.Font] = None

        # Flash green on win, red on loss
        self.win_color = COLORS.COUNT_POSITIVE
        self.lose_color = COLORS.COUNT_NEGATIVE

    @property
    def label_font(self) -> pygame.font.Font:
        if self._label_font is None:
            self._label_font = pygame.font.Font(None, self.label_font_size)
        return self._label_font

    def add_winnings(self, amount: float) -> None:
        """Add winnings with green flash."""
        self.set_value(self.spring.target + amount, flash_color=self.win_color)

    def subtract_loss(self, amount: float) -> None:
        """Subtract loss with red flash."""
        self.set_value(self.spring.target - amount, flash_color=self.lose_color)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw bankroll with label."""
        # Draw label above
        label_rendered = self.label_font.render(self.label, True, COLORS.TEXT_MUTED)
        label_rect = label_rendered.get_rect(center=(int(self.x), int(self.y) - 30))
        surface.blit(label_rendered, label_rect)

        super().draw(surface)
