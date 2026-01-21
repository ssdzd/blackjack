"""Screen shake effect using trauma-based system."""

import math
import random
from dataclasses import dataclass
from typing import Tuple

from pygame_ui.config import ANIMATION


@dataclass
class ShakeConfig:
    """Configuration for screen shake behavior."""

    max_offset: float = ANIMATION.MAX_SHAKE_OFFSET
    max_rotation: float = ANIMATION.MAX_SHAKE_ROTATION
    decay: float = ANIMATION.SHAKE_DECAY
    frequency: float = 15.0  # Noise frequency


class ScreenShake:
    """Trauma-based screen shake effect.

    Based on the GDC talk "Math for Game Programmers: Juicing Your Cameras With Math"
    by Squirrel Eiserloh.

    Trauma is accumulated and decays over time. The shake intensity is trauma^2,
    giving a nice falloff curve. Random noise provides the actual offset values.
    """

    def __init__(self, config: ShakeConfig = None):
        self.config = config or ShakeConfig()

        # Current trauma level (0-1)
        self._trauma = 0.0

        # Time accumulator for noise
        self._time = 0.0

        # Current offset values
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._rotation = 0.0

        # Noise seeds for consistent randomness
        self._seed_x = random.random() * 1000
        self._seed_y = random.random() * 1000
        self._seed_rot = random.random() * 1000

    @property
    def trauma(self) -> float:
        """Current trauma level (0-1)."""
        return self._trauma

    @property
    def shake_intensity(self) -> float:
        """Current shake intensity (trauma squared)."""
        return self._trauma * self._trauma

    @property
    def offset(self) -> Tuple[float, float]:
        """Current (x, y) offset to apply to rendering."""
        return (self._offset_x, self._offset_y)

    @property
    def rotation(self) -> float:
        """Current rotation offset in degrees."""
        return self._rotation

    @property
    def is_shaking(self) -> bool:
        """Check if shake is currently active."""
        return self._trauma > 0.001

    def add_trauma(self, amount: float) -> None:
        """Add trauma to trigger/intensify shake.

        Args:
            amount: Trauma to add (0-1 range, will be clamped)
        """
        self._trauma = min(1.0, self._trauma + amount)

    def set_trauma(self, amount: float) -> None:
        """Set trauma to a specific value.

        Args:
            amount: Trauma value (0-1 range, will be clamped)
        """
        self._trauma = max(0.0, min(1.0, amount))

    def clear(self) -> None:
        """Immediately stop all shake."""
        self._trauma = 0.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._rotation = 0.0

    def _perlin_noise_1d(self, x: float, seed: float) -> float:
        """Simple 1D noise function using sine waves.

        Not true Perlin noise, but gives smooth random-ish values.
        """
        return (
            math.sin(x * 1.0 + seed) * 0.5 +
            math.sin(x * 2.3 + seed * 1.3) * 0.3 +
            math.sin(x * 4.1 + seed * 0.7) * 0.2
        )

    def update(self, dt: float) -> None:
        """Update shake state.

        Args:
            dt: Delta time in seconds
        """
        # Decay trauma over time
        self._trauma = max(0.0, self._trauma - self.config.decay * dt)

        if self._trauma <= 0.001:
            self._offset_x = 0.0
            self._offset_y = 0.0
            self._rotation = 0.0
            return

        # Update time for noise
        self._time += dt * self.config.frequency

        # Calculate shake intensity (trauma squared for nice falloff)
        intensity = self._trauma * self._trauma

        # Generate offset using noise
        self._offset_x = self.config.max_offset * intensity * self._perlin_noise_1d(self._time, self._seed_x)
        self._offset_y = self.config.max_offset * intensity * self._perlin_noise_1d(self._time, self._seed_y)
        self._rotation = self.config.max_rotation * intensity * self._perlin_noise_1d(self._time, self._seed_rot)

    def apply_to_position(self, x: float, y: float) -> Tuple[float, float]:
        """Apply shake offset to a position.

        Args:
            x: Original x position
            y: Original y position

        Returns:
            Tuple of (shaken_x, shaken_y)
        """
        return (x + self._offset_x, y + self._offset_y)


# Preset shake configurations
SHAKE_LIGHT = ShakeConfig(max_offset=3.0, max_rotation=0.5, decay=3.0)
SHAKE_MEDIUM = ShakeConfig(max_offset=8.0, max_rotation=1.5, decay=2.0)
SHAKE_HEAVY = ShakeConfig(max_offset=15.0, max_rotation=3.0, decay=1.5)
SHAKE_IMPACT = ShakeConfig(max_offset=12.0, max_rotation=2.0, decay=4.0)
