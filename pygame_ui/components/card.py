"""Card sprite with full transform support and animations."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, List, Optional, Tuple

import pygame

from pygame_ui.config import ANIMATION, COLORS, DIMENSIONS
from pygame_ui.core.animation import EaseType, TweenManager
from pygame_ui.utils.math_utils import clamp, lerp


class CardState(Enum):
    """Visual state of a card."""

    IDLE = auto()
    HOVERED = auto()
    SELECTED = auto()
    DEALING = auto()
    FLIPPING = auto()


@dataclass
class CardAnimation:
    """Queued animation for a card."""

    animation_type: str  # 'move', 'flip', 'scale', 'rotate'
    target_value: any
    duration: float
    ease_type: EaseType = EaseType.EASE_OUT
    delay: float = 0.0
    on_complete: Optional[Callable[[], None]] = None


class CardSprite:
    """A card sprite with full transform support and animations.

    Supports position, rotation, scale, flip progress, shadows, and glow effects.
    Uses an animation queue for chaining multiple animations.
    """

    def __init__(
        self,
        x: float = 0,
        y: float = 0,
        face_up: bool = False,
        card_value: Optional[str] = None,
        card_suit: Optional[str] = None,
    ):
        # Position and transform
        self._x = x
        self._y = y
        self._rotation = 0.0  # Degrees
        self._scale = 1.0
        self._flip_progress = 1.0 if face_up else 0.0  # 0=face down, 1=face up

        # Card identity
        self.card_value = card_value  # 'A', '2'-'10', 'J', 'Q', 'K'
        self.card_suit = card_suit  # 'hearts', 'diamonds', 'clubs', 'spades'

        # Visual state
        self.state = CardState.IDLE
        self.alpha = 255
        self.z_index = 0  # For rendering order

        # Shadow properties
        self.shadow_offset = DIMENSIONS.CARD_SHADOW_OFFSET
        self.shadow_alpha = 80

        # Glow properties
        self.glow_intensity = 0.0  # 0-1
        self.glow_color = COLORS.GLOW_HIGHLIGHT

        # Hover effect
        self._hover_offset = 0.0  # Vertical lift on hover
        self._target_hover_offset = 0.0

        # Animation system
        self.tween_manager = TweenManager()
        self.animation_queue: List[CardAnimation] = []
        self._is_animating = False

        # Cached surfaces
        self._card_surface: Optional[pygame.Surface] = None
        self._needs_redraw = True

    # Properties with change detection for caching
    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, value: float) -> None:
        if self._x != value:
            self._x = value

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, value: float) -> None:
        if self._y != value:
            self._y = value

    @property
    def position(self) -> Tuple[float, float]:
        return (self._x, self._y)

    @position.setter
    def position(self, value: Tuple[float, float]) -> None:
        self._x, self._y = value

    @property
    def rotation(self) -> float:
        return self._rotation

    @rotation.setter
    def rotation(self, value: float) -> None:
        if self._rotation != value:
            self._rotation = value
            self._needs_redraw = True

    @property
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def scale(self, value: float) -> None:
        if self._scale != value:
            self._scale = value
            self._needs_redraw = True

    @property
    def flip_progress(self) -> float:
        return self._flip_progress

    @flip_progress.setter
    def flip_progress(self, value: float) -> None:
        value = clamp(value, 0.0, 1.0)
        if self._flip_progress != value:
            self._flip_progress = value
            self._needs_redraw = True

    @property
    def is_face_up(self) -> bool:
        return self._flip_progress > 0.5

    @property
    def is_animating(self) -> bool:
        return self.tween_manager.is_animating or len(self.animation_queue) > 0

    def _render_card_face(self, width: int, height: int) -> pygame.Surface:
        """Render the face-up side of the card."""
        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        # Card background
        rect = pygame.Rect(0, 0, width, height)
        pygame.draw.rect(surface, COLORS.CARD_WHITE, rect, border_radius=8)
        pygame.draw.rect(surface, COLORS.CARD_BLACK, rect, width=2, border_radius=8)

        # Draw card value and suit if available
        if self.card_value and self.card_suit:
            is_red = self.card_suit in ("hearts", "diamonds")
            color = COLORS.CARD_RED if is_red else COLORS.CARD_BLACK

            # Suit symbols
            suit_symbols = {
                "hearts": "♥",
                "diamonds": "♦",
                "clubs": "♣",
                "spades": "♠",
            }
            suit_symbol = suit_symbols.get(self.card_suit, "?")

            # Render value in corner
            font_size = max(16, int(height * 0.18))
            font = pygame.font.Font(None, font_size)

            value_text = font.render(self.card_value, True, color)
            surface.blit(value_text, (8, 6))

            suit_text = font.render(suit_symbol, True, color)
            surface.blit(suit_text, (8, 6 + font_size - 6))

            # Large center suit
            center_font = pygame.font.Font(None, int(height * 0.45))
            center_suit = center_font.render(suit_symbol, True, color)
            center_rect = center_suit.get_rect(center=(width // 2, height // 2))
            surface.blit(center_suit, center_rect)

            # Bottom right (inverted)
            value_text_br = font.render(self.card_value, True, color)
            value_text_br = pygame.transform.rotate(value_text_br, 180)
            surface.blit(value_text_br, (width - 8 - value_text_br.get_width(), height - 6 - font_size))

            suit_text_br = font.render(suit_symbol, True, color)
            suit_text_br = pygame.transform.rotate(suit_text_br, 180)
            surface.blit(suit_text_br, (width - 8 - suit_text_br.get_width(), height - 6 - font_size * 2 + 6))
        else:
            # Placeholder face - simple design
            inner_rect = rect.inflate(-16, -16)
            pygame.draw.rect(surface, (220, 220, 215), inner_rect, border_radius=4)

        return surface

    def _render_card_back(self, width: int, height: int) -> pygame.Surface:
        """Render the face-down (back) side of the card."""
        surface = pygame.Surface((width, height), pygame.SRCALPHA)

        # Card background
        rect = pygame.Rect(0, 0, width, height)
        pygame.draw.rect(surface, COLORS.CARD_BACK, rect, border_radius=8)
        pygame.draw.rect(surface, COLORS.CARD_BLACK, rect, width=2, border_radius=8)

        # Inner pattern
        inner_rect = rect.inflate(-12, -12)
        pygame.draw.rect(surface, COLORS.CARD_BACK_PATTERN, inner_rect, border_radius=4)

        # Decorative pattern (diamond grid)
        pattern_color = (*COLORS.CARD_BACK[:3], 60)
        for i in range(-height, width + height, 16):
            pygame.draw.line(
                surface,
                pattern_color,
                (i, 6),
                (i + height, height - 6),
                1,
            )
            pygame.draw.line(
                surface,
                pattern_color,
                (i + height, 6),
                (i, height - 6),
                1,
            )

        return surface

    def _render_card(self) -> pygame.Surface:
        """Render the card at current flip progress."""
        base_width = DIMENSIONS.CARD_WIDTH
        base_height = DIMENSIONS.CARD_HEIGHT

        # Calculate apparent width based on flip progress (3D effect)
        # At flip_progress 0 or 1, full width. At 0.5, zero width (edge-on)
        flip_factor = abs(self._flip_progress - 0.5) * 2  # 0 at middle, 1 at ends
        apparent_width = max(4, int(base_width * flip_factor))

        # Determine which side to show
        show_face = self._flip_progress > 0.5

        # Render the appropriate side at full size, then scale horizontally
        if show_face:
            full_surface = self._render_card_face(base_width, base_height)
        else:
            full_surface = self._render_card_back(base_width, base_height)

        # Scale horizontally for flip effect
        if apparent_width != base_width:
            scaled = pygame.transform.scale(full_surface, (apparent_width, base_height))
        else:
            scaled = full_surface

        return scaled

    def _render_shadow(self, card_width: int, card_height: int) -> pygame.Surface:
        """Render the card's drop shadow."""
        shadow_surface = pygame.Surface(
            (card_width + self.shadow_offset * 2, card_height + self.shadow_offset * 2),
            pygame.SRCALPHA,
        )

        shadow_rect = pygame.Rect(
            self.shadow_offset,
            self.shadow_offset,
            card_width,
            card_height,
        )
        shadow_color = (0, 0, 0, self.shadow_alpha)
        pygame.draw.rect(shadow_surface, shadow_color, shadow_rect, border_radius=8)

        return shadow_surface

    def _render_glow(self, card_width: int, card_height: int) -> pygame.Surface:
        """Render the card's glow effect."""
        glow_padding = 8
        glow_surface = pygame.Surface(
            (card_width + glow_padding * 2, card_height + glow_padding * 2),
            pygame.SRCALPHA,
        )

        if self.glow_intensity <= 0:
            return glow_surface

        # Draw multiple expanding rectangles for glow
        for i in range(4):
            alpha = int(60 * self.glow_intensity * (1 - i / 4))
            expand = i * 2
            glow_rect = pygame.Rect(
                glow_padding - expand,
                glow_padding - expand,
                card_width + expand * 2,
                card_height + expand * 2,
            )
            glow_color = (*self.glow_color[:3], alpha)
            pygame.draw.rect(glow_surface, glow_color, glow_rect, border_radius=10 + i)

        return glow_surface

    def update(self, dt: float) -> None:
        """Update card animations and state.

        Args:
            dt: Delta time in seconds
        """
        # Update active tweens
        self.tween_manager.update(dt)

        # Process animation queue if no active tweens
        if not self.tween_manager.is_animating and self.animation_queue:
            self._process_next_animation()

        # Smooth hover offset
        hover_speed = 15.0
        if self._hover_offset != self._target_hover_offset:
            diff = self._target_hover_offset - self._hover_offset
            self._hover_offset += diff * min(1.0, hover_speed * dt)
            if abs(diff) < 0.1:
                self._hover_offset = self._target_hover_offset

        # Update glow based on state
        target_glow = 0.0
        if self.state == CardState.HOVERED:
            target_glow = 0.5
        elif self.state == CardState.SELECTED:
            target_glow = 1.0

        glow_speed = 8.0
        self.glow_intensity += (target_glow - self.glow_intensity) * min(1.0, glow_speed * dt)

    def _process_next_animation(self) -> None:
        """Start the next animation in the queue."""
        if not self.animation_queue:
            return

        anim = self.animation_queue.pop(0)

        if anim.animation_type == "move":
            target_x, target_y = anim.target_value
            self.tween_manager.create(
                self, "x", target_x, anim.duration, anim.ease_type, delay=anim.delay
            )
            self.tween_manager.create(
                self,
                "y",
                target_y,
                anim.duration,
                anim.ease_type,
                delay=anim.delay,
                on_complete=anim.on_complete,
            )
        elif anim.animation_type == "flip":
            self.tween_manager.create(
                self,
                "flip_progress",
                anim.target_value,
                anim.duration,
                anim.ease_type,
                delay=anim.delay,
                on_complete=anim.on_complete,
            )
        elif anim.animation_type == "scale":
            self.tween_manager.create(
                self,
                "scale",
                anim.target_value,
                anim.duration,
                anim.ease_type,
                delay=anim.delay,
                on_complete=anim.on_complete,
            )
        elif anim.animation_type == "rotate":
            self.tween_manager.create(
                self,
                "rotation",
                anim.target_value,
                anim.duration,
                anim.ease_type,
                delay=anim.delay,
                on_complete=anim.on_complete,
            )

    def animate_to(
        self,
        x: float,
        y: float,
        duration: float = None,
        ease_type: EaseType = EaseType.EASE_OUT_BACK,
        delay: float = 0.0,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> "CardSprite":
        """Queue a move animation.

        Args:
            x: Target x position
            y: Target y position
            duration: Animation duration (default from config)
            ease_type: Easing function
            delay: Delay before starting
            on_complete: Callback when done

        Returns:
            Self for chaining
        """
        if duration is None:
            duration = ANIMATION.CARD_DEAL_DURATION

        self.animation_queue.append(
            CardAnimation(
                animation_type="move",
                target_value=(x, y),
                duration=duration,
                ease_type=ease_type,
                delay=delay,
                on_complete=on_complete,
            )
        )
        return self

    def flip(
        self,
        to_face_up: bool = True,
        duration: float = None,
        ease_type: EaseType = EaseType.EASE_OUT,
        delay: float = 0.0,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> "CardSprite":
        """Queue a flip animation.

        Args:
            to_face_up: True to flip face up, False for face down
            duration: Animation duration (default from config)
            ease_type: Easing function
            delay: Delay before starting
            on_complete: Callback when done

        Returns:
            Self for chaining
        """
        if duration is None:
            duration = ANIMATION.CARD_FLIP_DURATION

        target = 1.0 if to_face_up else 0.0
        self.animation_queue.append(
            CardAnimation(
                animation_type="flip",
                target_value=target,
                duration=duration,
                ease_type=ease_type,
                delay=delay,
                on_complete=on_complete,
            )
        )
        return self

    def scale_to(
        self,
        target_scale: float,
        duration: float = 0.2,
        ease_type: EaseType = EaseType.EASE_OUT_BACK,
        delay: float = 0.0,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> "CardSprite":
        """Queue a scale animation.

        Args:
            target_scale: Target scale value
            duration: Animation duration
            ease_type: Easing function
            delay: Delay before starting
            on_complete: Callback when done

        Returns:
            Self for chaining
        """
        self.animation_queue.append(
            CardAnimation(
                animation_type="scale",
                target_value=target_scale,
                duration=duration,
                ease_type=ease_type,
                delay=delay,
                on_complete=on_complete,
            )
        )
        return self

    def rotate_to(
        self,
        angle: float,
        duration: float = 0.3,
        ease_type: EaseType = EaseType.EASE_OUT,
        delay: float = 0.0,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> "CardSprite":
        """Queue a rotation animation.

        Args:
            angle: Target rotation in degrees
            duration: Animation duration
            ease_type: Easing function
            delay: Delay before starting
            on_complete: Callback when done

        Returns:
            Self for chaining
        """
        self.animation_queue.append(
            CardAnimation(
                animation_type="rotate",
                target_value=angle,
                duration=duration,
                ease_type=ease_type,
                delay=delay,
                on_complete=on_complete,
            )
        )
        return self

    def set_hover(self, hovered: bool) -> None:
        """Set hover state with animation.

        Args:
            hovered: Whether card is being hovered
        """
        if hovered:
            self.state = CardState.HOVERED
            self._target_hover_offset = -10
        else:
            if self.state == CardState.HOVERED:
                self.state = CardState.IDLE
            self._target_hover_offset = 0

    def set_selected(self, selected: bool) -> None:
        """Set selected state.

        Args:
            selected: Whether card is selected
        """
        self.state = CardState.SELECTED if selected else CardState.IDLE
        self._target_hover_offset = -15 if selected else 0

    def contains_point(self, point: Tuple[float, float]) -> bool:
        """Check if a point is within the card bounds.

        Args:
            point: (x, y) position to check

        Returns:
            True if point is inside card
        """
        half_width = (DIMENSIONS.CARD_WIDTH * self._scale) / 2
        half_height = (DIMENSIONS.CARD_HEIGHT * self._scale) / 2

        return (
            self._x - half_width <= point[0] <= self._x + half_width
            and self._y - half_height <= point[1] <= self._y + half_height
        )

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the card to the surface.

        Args:
            surface: Pygame surface to draw on
        """
        # Render card
        card_surface = self._render_card()
        card_width = card_surface.get_width()
        card_height = card_surface.get_height()

        # Apply scale
        if self._scale != 1.0:
            scaled_width = int(card_width * self._scale)
            scaled_height = int(card_height * self._scale)
            card_surface = pygame.transform.scale(
                card_surface, (scaled_width, scaled_height)
            )
            card_width, card_height = scaled_width, scaled_height

        # Apply rotation
        if self._rotation != 0:
            card_surface = pygame.transform.rotate(card_surface, self._rotation)

        # Calculate position with hover offset
        draw_y = self._y + self._hover_offset

        # Draw glow (behind shadow)
        if self.glow_intensity > 0:
            glow = self._render_glow(card_width, card_height)
            glow_rect = glow.get_rect(center=(int(self._x), int(draw_y)))
            surface.blit(glow, glow_rect)

        # Draw shadow
        shadow = self._render_shadow(card_width, card_height)
        shadow_rect = shadow.get_rect(
            center=(int(self._x) + self.shadow_offset // 2, int(draw_y) + self.shadow_offset)
        )
        surface.blit(shadow, shadow_rect)

        # Apply alpha
        if self.alpha < 255:
            card_surface.set_alpha(self.alpha)

        # Draw card
        card_rect = card_surface.get_rect(center=(int(self._x), int(draw_y)))
        surface.blit(card_surface, card_rect)


class CardGroup:
    """Manages a collection of cards (e.g., a hand)."""

    def __init__(self):
        self.cards: List[CardSprite] = []

    def add(self, card: CardSprite) -> None:
        """Add a card to the group."""
        self.cards.append(card)
        self._update_z_indices()

    def remove(self, card: CardSprite) -> None:
        """Remove a card from the group."""
        if card in self.cards:
            self.cards.remove(card)
            self._update_z_indices()

    def clear(self) -> None:
        """Remove all cards."""
        self.cards.clear()

    def _update_z_indices(self) -> None:
        """Update z-indices for proper layering."""
        for i, card in enumerate(self.cards):
            card.z_index = i

    def update(self, dt: float) -> None:
        """Update all cards."""
        for card in self.cards:
            card.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw all cards in z-order."""
        for card in sorted(self.cards, key=lambda c: c.z_index):
            card.draw(surface)

    def get_card_at(self, point: Tuple[float, float]) -> Optional[CardSprite]:
        """Get the topmost card at a point.

        Args:
            point: (x, y) position to check

        Returns:
            Card at point or None
        """
        # Check in reverse z-order (top to bottom)
        for card in sorted(self.cards, key=lambda c: -c.z_index):
            if card.contains_point(point):
                return card
        return None

    def arrange_fan(
        self,
        center_x: float,
        y: float,
        spacing: float = None,
        animate: bool = True,
        stagger_delay: float = 0.05,
    ) -> None:
        """Arrange cards in a fan pattern.

        Args:
            center_x: Center x position
            y: Y position for all cards
            spacing: Space between cards (default from config)
            animate: Whether to animate the arrangement
            stagger_delay: Delay between each card's animation
        """
        if spacing is None:
            spacing = DIMENSIONS.HAND_SPACING

        if not self.cards:
            return

        total_width = (len(self.cards) - 1) * spacing
        start_x = center_x - total_width / 2

        for i, card in enumerate(self.cards):
            target_x = start_x + i * spacing
            if animate:
                card.animate_to(target_x, y, delay=i * stagger_delay)
            else:
                card.x = target_x
                card.y = y
