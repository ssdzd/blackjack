"""Scene transition effects."""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Optional, Tuple

import pygame

from pygame_ui.config import COLORS
from pygame_ui.utils.math_utils import lerp


class TransitionState(Enum):
    """State of a transition."""

    IDLE = auto()
    TRANSITIONING_OUT = auto()  # Fading out current scene
    TRANSITIONING_IN = auto()   # Fading in new scene
    COMPLETE = auto()


class Transition(ABC):
    """Base class for scene transitions."""

    def __init__(self, duration: float = 0.5):
        """Initialize transition.

        Args:
            duration: Total transition time (half out, half in)
        """
        self.duration = duration
        self.half_duration = duration / 2
        self.elapsed = 0.0
        self.state = TransitionState.IDLE
        self.progress = 0.0  # 0-1 progress through current phase

    @property
    def is_active(self) -> bool:
        """Check if transition is currently running."""
        return self.state not in (TransitionState.IDLE, TransitionState.COMPLETE)

    @property
    def is_at_midpoint(self) -> bool:
        """Check if transition is at the midpoint (time to switch scenes)."""
        return self.state == TransitionState.TRANSITIONING_IN and self.elapsed <= 0.016

    def start(self) -> None:
        """Start the transition."""
        self.elapsed = 0.0
        self.state = TransitionState.TRANSITIONING_OUT
        self.progress = 0.0

    def reset(self) -> None:
        """Reset transition to idle state."""
        self.elapsed = 0.0
        self.state = TransitionState.IDLE
        self.progress = 0.0

    def update(self, dt: float) -> None:
        """Update transition state.

        Args:
            dt: Delta time in seconds
        """
        if self.state == TransitionState.IDLE or self.state == TransitionState.COMPLETE:
            return

        self.elapsed += dt

        if self.state == TransitionState.TRANSITIONING_OUT:
            self.progress = min(1.0, self.elapsed / self.half_duration)
            if self.elapsed >= self.half_duration:
                self.state = TransitionState.TRANSITIONING_IN
                self.elapsed = 0.0
                self.progress = 0.0

        elif self.state == TransitionState.TRANSITIONING_IN:
            self.progress = min(1.0, self.elapsed / self.half_duration)
            if self.elapsed >= self.half_duration:
                self.state = TransitionState.COMPLETE
                self.progress = 1.0

    @abstractmethod
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the transition effect.

        Args:
            surface: Surface to draw on
        """
        pass


class FadeTransition(Transition):
    """Simple fade to black transition."""

    def __init__(
        self,
        duration: float = 0.5,
        color: Tuple[int, int, int] = (0, 0, 0),
    ):
        super().__init__(duration)
        self.color = color
        self._overlay: Optional[pygame.Surface] = None

    def draw(self, surface: pygame.Surface) -> None:
        """Draw fade overlay."""
        if self.state == TransitionState.IDLE or self.state == TransitionState.COMPLETE:
            return

        # Create overlay if needed
        if self._overlay is None or self._overlay.get_size() != surface.get_size():
            self._overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        # Calculate alpha based on state
        if self.state == TransitionState.TRANSITIONING_OUT:
            # Fading out: alpha goes from 0 to 255
            alpha = int(255 * self.progress)
        else:
            # Fading in: alpha goes from 255 to 0
            alpha = int(255 * (1.0 - self.progress))

        self._overlay.fill((*self.color, alpha))
        surface.blit(self._overlay, (0, 0))


class WipeTransition(Transition):
    """Horizontal wipe transition."""

    def __init__(
        self,
        duration: float = 0.5,
        color: Tuple[int, int, int] = (0, 0, 0),
        direction: str = "left",  # "left" or "right"
    ):
        super().__init__(duration)
        self.color = color
        self.direction = direction

    def draw(self, surface: pygame.Surface) -> None:
        """Draw wipe overlay."""
        if self.state == TransitionState.IDLE or self.state == TransitionState.COMPLETE:
            return

        width, height = surface.get_size()

        if self.state == TransitionState.TRANSITIONING_OUT:
            # Wipe covers screen
            cover_width = int(width * self.progress)
        else:
            # Wipe reveals screen
            cover_width = int(width * (1.0 - self.progress))

        if self.direction == "left":
            rect = pygame.Rect(0, 0, cover_width, height)
        else:
            rect = pygame.Rect(width - cover_width, 0, cover_width, height)

        pygame.draw.rect(surface, self.color, rect)


class CircleTransition(Transition):
    """Circle iris transition (like old cartoons)."""

    def __init__(
        self,
        duration: float = 0.6,
        color: Tuple[int, int, int] = (0, 0, 0),
        center: Optional[Tuple[int, int]] = None,
    ):
        super().__init__(duration)
        self.color = color
        self.center = center  # None = screen center
        self._mask: Optional[pygame.Surface] = None

    def draw(self, surface: pygame.Surface) -> None:
        """Draw circle iris effect."""
        if self.state == TransitionState.IDLE or self.state == TransitionState.COMPLETE:
            return

        width, height = surface.get_size()
        center = self.center or (width // 2, height // 2)

        # Max radius to cover entire screen from center
        max_radius = int(((width ** 2 + height ** 2) ** 0.5) / 2) + 10

        if self.state == TransitionState.TRANSITIONING_OUT:
            # Circle shrinks (iris closing)
            radius = int(max_radius * (1.0 - self.progress))
        else:
            # Circle grows (iris opening)
            radius = int(max_radius * self.progress)

        # Create mask surface
        if self._mask is None or self._mask.get_size() != (width, height):
            self._mask = pygame.Surface((width, height), pygame.SRCALPHA)

        # Fill with color, then cut out circle
        self._mask.fill((*self.color, 255))

        if radius > 0:
            pygame.draw.circle(self._mask, (0, 0, 0, 0), center, radius)

        surface.blit(self._mask, (0, 0))


class SlideTransition(Transition):
    """Slide transition - old scene slides out, new slides in."""

    def __init__(
        self,
        duration: float = 0.5,
        direction: str = "left",  # "left", "right", "up", "down"
    ):
        super().__init__(duration)
        self.direction = direction
        self._old_surface: Optional[pygame.Surface] = None
        self._new_surface: Optional[pygame.Surface] = None

    def start_with_surfaces(
        self,
        old_surface: pygame.Surface,
        new_surface: pygame.Surface,
    ) -> None:
        """Start transition with captured surfaces.

        Args:
            old_surface: The outgoing scene
            new_surface: The incoming scene
        """
        self._old_surface = old_surface.copy()
        self._new_surface = new_surface.copy()
        self.start()

    def draw(self, surface: pygame.Surface) -> None:
        """Draw sliding surfaces."""
        if self.state == TransitionState.IDLE or self.state == TransitionState.COMPLETE:
            return

        if not self._old_surface or not self._new_surface:
            return

        width, height = surface.get_size()

        # Calculate offset based on direction and progress
        total_progress = (
            self.progress if self.state == TransitionState.TRANSITIONING_OUT
            else 1.0 + self.progress
        ) / 2.0

        if self.direction == "left":
            old_x = int(-width * total_progress)
            new_x = old_x + width
            old_y = new_y = 0
        elif self.direction == "right":
            old_x = int(width * total_progress)
            new_x = old_x - width
            old_y = new_y = 0
        elif self.direction == "up":
            old_y = int(-height * total_progress)
            new_y = old_y + height
            old_x = new_x = 0
        else:  # down
            old_y = int(height * total_progress)
            new_y = old_y - height
            old_x = new_x = 0

        surface.blit(self._old_surface, (old_x, old_y))
        surface.blit(self._new_surface, (new_x, new_y))


class TransitionManager:
    """Manages scene transitions."""

    def __init__(self):
        self.current_transition: Optional[Transition] = None

    def start_fade(
        self,
        duration: float = 0.5,
        color: Tuple[int, int, int] = (0, 0, 0),
    ) -> FadeTransition:
        """Start a fade transition."""
        self.current_transition = FadeTransition(duration, color)
        self.current_transition.start()
        return self.current_transition

    def start_wipe(
        self,
        duration: float = 0.5,
        direction: str = "left",
    ) -> WipeTransition:
        """Start a wipe transition."""
        self.current_transition = WipeTransition(duration, direction=direction)
        self.current_transition.start()
        return self.current_transition

    def start_circle(
        self,
        duration: float = 0.6,
        center: Optional[Tuple[int, int]] = None,
    ) -> CircleTransition:
        """Start a circle iris transition."""
        self.current_transition = CircleTransition(duration, center=center)
        self.current_transition.start()
        return self.current_transition

    @property
    def is_active(self) -> bool:
        """Check if a transition is active."""
        return self.current_transition is not None and self.current_transition.is_active

    @property
    def is_at_midpoint(self) -> bool:
        """Check if transition is at midpoint (time to switch scenes)."""
        return (
            self.current_transition is not None
            and self.current_transition.is_at_midpoint
        )

    def update(self, dt: float) -> None:
        """Update current transition."""
        if self.current_transition:
            self.current_transition.update(dt)
            if self.current_transition.state == TransitionState.COMPLETE:
                self.current_transition = None

    def draw(self, surface: pygame.Surface) -> None:
        """Draw current transition."""
        if self.current_transition:
            self.current_transition.draw(surface)
