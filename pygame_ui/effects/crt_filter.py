"""CRT post-processing filter for retro visual effects."""

import math
from typing import Optional, Tuple

import pygame

from pygame_ui.config import DIMENSIONS


class CRTFilter:
    """CRT-style post-processing filter.

    Features:
    - Scanlines overlay
    - Vignette (darkened edges)
    - Optional chromatic aberration
    - Optional screen curvature simulation
    - Performance toggle
    """

    def __init__(
        self,
        width: int = DIMENSIONS.SCREEN_WIDTH,
        height: int = DIMENSIONS.SCREEN_HEIGHT,
        scanline_alpha: int = 30,
        scanline_spacing: int = 2,
        vignette_strength: float = 0.3,
        chromatic_aberration: float = 0.0,
        curvature: float = 0.0,
        enabled: bool = True,
    ):
        """Initialize CRT filter.

        Args:
            width: Screen width
            height: Screen height
            scanline_alpha: Opacity of scanlines (0-255)
            scanline_spacing: Pixels between scanlines
            vignette_strength: How dark edges get (0-1)
            chromatic_aberration: RGB split amount in pixels (0 = disabled)
            curvature: Screen curvature amount (0 = flat, not implemented)
            enabled: Whether filter is active
        """
        self.width = width
        self.height = height
        self.scanline_alpha = scanline_alpha
        self.scanline_spacing = scanline_spacing
        self.vignette_strength = vignette_strength
        self.chromatic_aberration = chromatic_aberration
        self.curvature = curvature
        self.enabled = enabled

        # Pre-rendered overlay surfaces
        self._scanline_surface: Optional[pygame.Surface] = None
        self._vignette_surface: Optional[pygame.Surface] = None
        self._needs_rebuild = True

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the filter."""
        self.enabled = enabled

    def toggle(self) -> bool:
        """Toggle filter on/off. Returns new state."""
        self.enabled = not self.enabled
        return self.enabled

    def set_scanline_alpha(self, alpha: int) -> None:
        """Set scanline opacity (0-255)."""
        self.scanline_alpha = max(0, min(255, alpha))
        self._needs_rebuild = True

    def set_vignette_strength(self, strength: float) -> None:
        """Set vignette strength (0-1)."""
        self.vignette_strength = max(0.0, min(1.0, strength))
        self._needs_rebuild = True

    def _build_scanline_surface(self) -> pygame.Surface:
        """Create the scanline overlay."""
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Draw horizontal scanlines
        for y in range(0, self.height, self.scanline_spacing):
            pygame.draw.line(
                surface,
                (0, 0, 0, self.scanline_alpha),
                (0, y),
                (self.width, y),
                1,
            )

        return surface

    def _build_vignette_surface(self) -> pygame.Surface:
        """Create the vignette overlay."""
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Calculate center and max distance
        center_x = self.width / 2
        center_y = self.height / 2
        max_dist = math.sqrt(center_x ** 2 + center_y ** 2)

        # Draw radial gradient vignette
        # Using concentric rectangles for performance (approximation)
        steps = 20
        for i in range(steps):
            progress = i / steps
            # Ease in for smoother falloff
            alpha = int(255 * self.vignette_strength * (progress ** 2))

            # Calculate rectangle size (shrinking toward center)
            margin_x = int(center_x * (1 - progress))
            margin_y = int(center_y * (1 - progress))

            rect = pygame.Rect(
                margin_x,
                margin_y,
                self.width - margin_x * 2,
                self.height - margin_y * 2,
            )

            # Draw with rounded corners for smoother look
            if rect.width > 0 and rect.height > 0:
                pygame.draw.rect(
                    surface,
                    (0, 0, 0, alpha),
                    rect,
                    width=max(1, int((1 - progress) * 50)),
                    border_radius=int(100 * progress),
                )

        return surface

    def _rebuild_surfaces(self) -> None:
        """Rebuild all overlay surfaces."""
        self._scanline_surface = self._build_scanline_surface()
        self._vignette_surface = self._build_vignette_surface()
        self._needs_rebuild = False

    def _apply_chromatic_aberration(
        self, surface: pygame.Surface
    ) -> pygame.Surface:
        """Apply RGB channel separation.

        Args:
            surface: Input surface

        Returns:
            Surface with chromatic aberration applied
        """
        if self.chromatic_aberration <= 0:
            return surface

        offset = int(self.chromatic_aberration)
        result = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

        # Extract and offset color channels
        # This is a simplified version - true CA would separate RGB properly
        # For performance, we'll just do a subtle color fringe

        # Red channel shifted left
        red_surface = surface.copy()
        red_surface.fill((255, 0, 0), special_flags=pygame.BLEND_MULT)
        result.blit(red_surface, (-offset, 0))

        # Green channel centered (use BLEND_ADD)
        green_surface = surface.copy()
        green_surface.fill((0, 255, 0), special_flags=pygame.BLEND_MULT)
        result.blit(green_surface, (0, 0), special_flags=pygame.BLEND_ADD)

        # Blue channel shifted right
        blue_surface = surface.copy()
        blue_surface.fill((0, 0, 255), special_flags=pygame.BLEND_MULT)
        result.blit(blue_surface, (offset, 0), special_flags=pygame.BLEND_ADD)

        return result

    def apply(self, surface: pygame.Surface) -> pygame.Surface:
        """Apply CRT filter to a surface.

        Args:
            surface: The game surface to filter

        Returns:
            Filtered surface (may be same surface if disabled)
        """
        if not self.enabled:
            return surface

        # Rebuild overlays if needed
        if self._needs_rebuild:
            self._rebuild_surfaces()

        # Apply chromatic aberration first (if enabled)
        if self.chromatic_aberration > 0:
            surface = self._apply_chromatic_aberration(surface)

        # Apply scanlines
        if self._scanline_surface and self.scanline_alpha > 0:
            surface.blit(self._scanline_surface, (0, 0))

        # Apply vignette
        if self._vignette_surface and self.vignette_strength > 0:
            surface.blit(self._vignette_surface, (0, 0))

        return surface

    def resize(self, width: int, height: int) -> None:
        """Handle screen resize.

        Args:
            width: New width
            height: New height
        """
        self.width = width
        self.height = height
        self._needs_rebuild = True


class CRTFilterLite:
    """Lightweight CRT filter with just scanlines.

    Use this for better performance on slower systems.
    """

    def __init__(
        self,
        width: int = DIMENSIONS.SCREEN_WIDTH,
        height: int = DIMENSIONS.SCREEN_HEIGHT,
        scanline_alpha: int = 25,
        enabled: bool = True,
    ):
        self.width = width
        self.height = height
        self.scanline_alpha = scanline_alpha
        self.enabled = enabled
        self._surface: Optional[pygame.Surface] = None

    def _build_surface(self) -> pygame.Surface:
        """Create scanline overlay."""
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for y in range(0, self.height, 2):
            pygame.draw.line(
                surface,
                (0, 0, 0, self.scanline_alpha),
                (0, y),
                (self.width, y),
                1,
            )
        return surface

    def apply(self, surface: pygame.Surface) -> pygame.Surface:
        """Apply scanlines to surface."""
        if not self.enabled:
            return surface

        if self._surface is None:
            self._surface = self._build_surface()

        surface.blit(self._surface, (0, 0))
        return surface

    def toggle(self) -> bool:
        """Toggle filter. Returns new state."""
        self.enabled = not self.enabled
        return self.enabled
