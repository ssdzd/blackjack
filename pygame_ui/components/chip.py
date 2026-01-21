"""Chip sprite and betting animation components."""

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Optional, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.core.animation import EaseType, TweenManager


class ChipValue(Enum):
    """Chip denominations with their colors."""

    WHITE = (1, (240, 240, 240), (200, 200, 200))      # $1
    RED = (5, (200, 50, 50), (160, 30, 30))            # $5
    BLUE = (10, (50, 100, 200), (30, 70, 160))         # $10
    GREEN = (25, (50, 160, 80), (30, 120, 50))         # $25
    BLACK = (100, (30, 30, 35), (20, 20, 25))          # $100
    PURPLE = (500, (130, 50, 160), (100, 30, 130))     # $500
    GOLD = (1000, (255, 200, 50), (200, 150, 30))      # $1000

    @property
    def amount(self) -> int:
        return self.value[0]

    @property
    def color(self) -> Tuple[int, int, int]:
        return self.value[1]

    @property
    def edge_color(self) -> Tuple[int, int, int]:
        return self.value[2]


@dataclass
class ChipAnimation:
    """Animation data for a chip."""

    target_x: float
    target_y: float
    duration: float
    delay: float = 0.0
    ease_type: EaseType = EaseType.EASE_OUT_BACK
    on_complete: Optional[Callable[[], None]] = None


class ChipSprite:
    """A single chip with animations."""

    RADIUS = 20
    THICKNESS = 6

    def __init__(
        self,
        x: float,
        y: float,
        chip_value: ChipValue = ChipValue.RED,
    ):
        self.x = x
        self.y = y
        self.chip_value = chip_value

        self.scale = 1.0
        self.rotation = 0.0
        self.alpha = 255

        # Animation
        self.tween_manager = TweenManager()
        self._cached_surface: Optional[pygame.Surface] = None

    def _render_chip(self) -> pygame.Surface:
        """Render a single chip."""
        if self._cached_surface is not None:
            return self._cached_surface

        size = self.RADIUS * 2 + 4
        surface = pygame.Surface((size, size), pygame.SRCALPHA)

        cx, cy = size // 2, size // 2

        # Shadow
        shadow_color = (0, 0, 0, 60)
        pygame.draw.circle(surface, shadow_color, (cx + 2, cy + 2), self.RADIUS)

        # Main chip body
        pygame.draw.circle(surface, self.chip_value.color, (cx, cy), self.RADIUS)

        # Edge ring
        pygame.draw.circle(surface, self.chip_value.edge_color, (cx, cy), self.RADIUS, 3)

        # Inner decorative ring
        inner_color = tuple(min(255, c + 30) for c in self.chip_value.color)
        pygame.draw.circle(surface, inner_color, (cx, cy), self.RADIUS - 6, 2)

        # Edge notches (like real casino chips)
        notch_count = 8
        for i in range(notch_count):
            angle = i * (2 * math.pi / notch_count)
            nx = cx + math.cos(angle) * (self.RADIUS - 2)
            ny = cy + math.sin(angle) * (self.RADIUS - 2)
            pygame.draw.circle(surface, (255, 255, 255, 150), (int(nx), int(ny)), 3)

        # Center value text
        font = pygame.font.Font(None, 16)
        value_text = f"${self.chip_value.amount}"
        if self.chip_value.amount >= 1000:
            value_text = f"${self.chip_value.amount // 1000}K"
        text_surface = font.render(value_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(cx, cy))
        surface.blit(text_surface, text_rect)

        self._cached_surface = surface
        return surface

    def animate_to(
        self,
        x: float,
        y: float,
        duration: float = 0.3,
        ease_type: EaseType = EaseType.EASE_OUT_BACK,
        delay: float = 0.0,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> None:
        """Animate chip to a position."""
        self.tween_manager.create(self, "x", x, duration, ease_type, delay=delay)
        self.tween_manager.create(self, "y", y, duration, ease_type, delay=delay, on_complete=on_complete)

    def update(self, dt: float) -> None:
        """Update chip animations."""
        self.tween_manager.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the chip."""
        chip_surface = self._render_chip()

        # Apply scale
        if self.scale != 1.0:
            new_size = int(chip_surface.get_width() * self.scale)
            chip_surface = pygame.transform.scale(chip_surface, (new_size, new_size))

        # Apply alpha
        if self.alpha < 255:
            chip_surface.set_alpha(int(self.alpha))

        # Draw
        rect = chip_surface.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(chip_surface, rect)


class ChipStack:
    """A stack of chips representing a bet amount."""

    CHIP_OFFSET_Y = 4  # Vertical offset between stacked chips

    def __init__(self, x: float, y: float, amount: int = 0):
        self.x = x
        self.y = y
        self._amount = amount
        self.chips: List[ChipSprite] = []

        if amount > 0:
            self._create_chips_for_amount(amount)

    @property
    def amount(self) -> int:
        return self._amount

    @amount.setter
    def amount(self, value: int) -> None:
        if value != self._amount:
            self._amount = value
            self._create_chips_for_amount(value)

    def _create_chips_for_amount(self, amount: int) -> None:
        """Create chip sprites for an amount."""
        self.chips.clear()

        if amount <= 0:
            return

        # Break down into chip denominations (greedy)
        remaining = amount
        chip_values = sorted(ChipValue, key=lambda c: c.amount, reverse=True)

        chip_list = []
        for cv in chip_values:
            while remaining >= cv.amount and len(chip_list) < 20:  # Max 20 chips
                chip_list.append(cv)
                remaining -= cv.amount

        # Create chip sprites stacked
        for i, cv in enumerate(reversed(chip_list)):
            chip = ChipSprite(
                x=self.x,
                y=self.y - i * self.CHIP_OFFSET_Y,
                chip_value=cv,
            )
            self.chips.append(chip)

    def set_position(self, x: float, y: float) -> None:
        """Set stack position."""
        dx = x - self.x
        dy = y - self.y
        self.x = x
        self.y = y
        for i, chip in enumerate(self.chips):
            chip.x += dx
            chip.y = y - i * self.CHIP_OFFSET_Y

    def animate_to(
        self,
        x: float,
        y: float,
        duration: float = 0.3,
        stagger: float = 0.02,
    ) -> None:
        """Animate entire stack to a new position."""
        for i, chip in enumerate(self.chips):
            target_y = y - i * self.CHIP_OFFSET_Y
            chip.animate_to(x, target_y, duration=duration, delay=i * stagger)

        self.x = x
        self.y = y

    def update(self, dt: float) -> None:
        """Update all chips."""
        for chip in self.chips:
            chip.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw all chips in stack (bottom to top)."""
        for chip in self.chips:
            chip.draw(surface)


class BettingArea:
    """Interactive betting area with chip animations."""

    def __init__(
        self,
        x: float,
        y: float,
        initial_bet: int = 0,
        on_bet_change: Optional[Callable[[int], None]] = None,
    ):
        self.x = x
        self.y = y
        self.on_bet_change = on_bet_change

        # Current bet stack
        self.bet_stack = ChipStack(x, y, initial_bet)

        # Available chip denominations for selection
        self.chip_buttons: List[Tuple[ChipValue, pygame.Rect]] = []
        self._setup_chip_buttons()

        # Animation state
        self._flying_chips: List[ChipSprite] = []

    def _setup_chip_buttons(self) -> None:
        """Create chip selection buttons."""
        button_chips = [
            ChipValue.WHITE,
            ChipValue.RED,
            ChipValue.GREEN,
            ChipValue.BLACK,
        ]

        start_x = self.x - len(button_chips) * 25
        for i, cv in enumerate(button_chips):
            rect = pygame.Rect(
                int(start_x + i * 50) - 20,
                int(self.y + 60) - 20,
                40,
                40,
            )
            self.chip_buttons.append((cv, rect))

    def add_chip(self, chip_value: ChipValue, from_pos: Tuple[float, float] = None) -> None:
        """Add a chip to the bet with animation."""
        from pygame_ui.core.sound_manager import play_sound

        new_amount = self.bet_stack.amount + chip_value.amount

        # Create flying chip
        start_x, start_y = from_pos or (self.x, self.y + 80)
        flying = ChipSprite(start_x, start_y, chip_value)

        target_y = self.y - len(self.bet_stack.chips) * ChipStack.CHIP_OFFSET_Y
        flying.animate_to(
            self.x,
            target_y,
            duration=0.25,
            on_complete=lambda: self._on_chip_landed(chip_value),
        )
        self._flying_chips.append(flying)

        play_sound("chip_single")

    def _on_chip_landed(self, chip_value: ChipValue) -> None:
        """Called when a flying chip lands."""
        self.bet_stack.amount = self.bet_stack.amount + chip_value.amount
        if self.on_bet_change:
            self.on_bet_change(self.bet_stack.amount)

    def clear_bet(self) -> None:
        """Clear all chips from bet."""
        self.bet_stack.amount = 0
        self._flying_chips.clear()
        if self.on_bet_change:
            self.on_bet_change(0)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for chip_value, rect in self.chip_buttons:
                if rect.collidepoint(event.pos):
                    self.add_chip(chip_value, from_pos=(rect.centerx, rect.centery))
                    return True
        return False

    def update(self, dt: float) -> None:
        """Update animations."""
        self.bet_stack.update(dt)

        # Update and clean up flying chips
        for chip in self._flying_chips[:]:
            chip.update(dt)
            if not chip.tween_manager.is_animating:
                self._flying_chips.remove(chip)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw betting area."""
        # Draw bet stack
        self.bet_stack.draw(surface)

        # Draw flying chips
        for chip in self._flying_chips:
            chip.draw(surface)

        # Draw chip selection buttons
        for chip_value, rect in self.chip_buttons:
            # Draw chip button
            chip = ChipSprite(rect.centerx, rect.centery, chip_value)
            chip.draw(surface)

        # Draw current bet amount
        font = pygame.font.Font(None, 32)
        bet_text = f"${self.bet_stack.amount}"
        text_surface = font.render(bet_text, True, COLORS.GOLD)
        text_rect = text_surface.get_rect(center=(int(self.x), int(self.y - len(self.bet_stack.chips) * ChipStack.CHIP_OFFSET_Y - 30)))
        surface.blit(text_surface, text_rect)
