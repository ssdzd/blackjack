"""Particle system for visual effects."""

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS


class ParticleType(Enum):
    """Types of particle effects."""

    CONFETTI = auto()
    SPARK = auto()
    COIN = auto()
    STAR = auto()
    SMOKE = auto()


@dataclass
class Particle:
    """A single particle with physics."""

    x: float
    y: float
    vx: float  # Velocity x
    vy: float  # Velocity y
    size: float
    color: Tuple[int, int, int]
    lifetime: float  # Time remaining
    max_lifetime: float
    particle_type: ParticleType = ParticleType.CONFETTI
    rotation: float = 0.0
    rotation_speed: float = 0.0
    gravity: float = 200.0  # Pixels per second^2
    drag: float = 0.98  # Velocity multiplier per frame
    alpha: float = 255.0

    @property
    def progress(self) -> float:
        """Get lifetime progress (0=new, 1=dead)."""
        return 1.0 - (self.lifetime / self.max_lifetime) if self.max_lifetime > 0 else 1.0

    def update(self, dt: float) -> bool:
        """Update particle physics. Returns False if particle is dead."""
        self.lifetime -= dt
        if self.lifetime <= 0:
            return False

        # Apply gravity
        self.vy += self.gravity * dt

        # Apply drag
        self.vx *= self.drag
        self.vy *= self.drag

        # Move
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Rotate
        self.rotation += self.rotation_speed * dt

        # Fade out near end of life
        if self.progress > 0.7:
            fade_progress = (self.progress - 0.7) / 0.3
            self.alpha = 255 * (1.0 - fade_progress)

        return True


class ParticleEmitter:
    """Emits particles with configurable properties."""

    def __init__(
        self,
        particle_type: ParticleType = ParticleType.CONFETTI,
        colors: List[Tuple[int, int, int]] = None,
        lifetime_range: Tuple[float, float] = (0.8, 1.5),
        size_range: Tuple[float, float] = (4, 8),
        speed_range: Tuple[float, float] = (100, 300),
        gravity: float = 200.0,
        drag: float = 0.98,
    ):
        self.particle_type = particle_type
        self.colors = colors or [
            (255, 200, 87),   # Gold
            (255, 100, 100),  # Red
            (100, 200, 255),  # Blue
            (100, 255, 100),  # Green
            (255, 150, 255),  # Pink
        ]
        self.lifetime_range = lifetime_range
        self.size_range = size_range
        self.speed_range = speed_range
        self.gravity = gravity
        self.drag = drag

    def emit(
        self,
        x: float,
        y: float,
        count: int = 10,
        direction: float = None,  # Angle in degrees, None for random
        spread: float = 360.0,  # Spread angle
    ) -> List[Particle]:
        """Emit particles at a position.

        Args:
            x: X position
            y: Y position
            count: Number of particles
            direction: Base direction angle (degrees), None for all around
            spread: Angular spread (degrees)
        """
        particles = []

        for _ in range(count):
            # Random color
            color = random.choice(self.colors)

            # Random lifetime
            lifetime = random.uniform(*self.lifetime_range)

            # Random size
            size = random.uniform(*self.size_range)

            # Random speed
            speed = random.uniform(*self.speed_range)

            # Calculate velocity direction
            if direction is not None:
                angle = math.radians(direction + random.uniform(-spread / 2, spread / 2))
            else:
                angle = random.uniform(0, 2 * math.pi)

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            # Create particle
            particle = Particle(
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                size=size,
                color=color,
                lifetime=lifetime,
                max_lifetime=lifetime,
                particle_type=self.particle_type,
                rotation=random.uniform(0, 360),
                rotation_speed=random.uniform(-360, 360),
                gravity=self.gravity,
                drag=self.drag,
            )
            particles.append(particle)

        return particles


class ParticleSystem:
    """Manages and renders particles."""

    def __init__(self):
        self.particles: List[Particle] = []
        self.emitters: dict[str, ParticleEmitter] = {}

        # Pre-create common emitters
        self._create_default_emitters()

    def _create_default_emitters(self) -> None:
        """Create default particle emitters."""
        # Win celebration confetti
        self.emitters["confetti"] = ParticleEmitter(
            particle_type=ParticleType.CONFETTI,
            colors=[
                (255, 200, 87),   # Gold
                (255, 100, 100),  # Red
                (100, 200, 255),  # Blue
                (100, 255, 100),  # Green
                (255, 150, 255),  # Pink
                (255, 255, 255),  # White
            ],
            lifetime_range=(1.0, 2.0),
            size_range=(4, 10),
            speed_range=(150, 400),
            gravity=150.0,
            drag=0.99,
        )

        # Sparkle effect
        self.emitters["sparks"] = ParticleEmitter(
            particle_type=ParticleType.SPARK,
            colors=[
                (255, 255, 200),
                (255, 220, 150),
                (255, 200, 100),
            ],
            lifetime_range=(0.3, 0.6),
            size_range=(2, 5),
            speed_range=(50, 150),
            gravity=50.0,
            drag=0.95,
        )

        # Coin burst
        self.emitters["coins"] = ParticleEmitter(
            particle_type=ParticleType.COIN,
            colors=[
                (255, 215, 0),    # Gold
                (255, 200, 50),
                (230, 180, 30),
            ],
            lifetime_range=(0.8, 1.2),
            size_range=(8, 12),
            speed_range=(200, 400),
            gravity=300.0,
            drag=0.98,
        )

        # Star burst (for blackjack)
        self.emitters["stars"] = ParticleEmitter(
            particle_type=ParticleType.STAR,
            colors=[
                (255, 255, 100),
                (255, 220, 100),
                (255, 200, 50),
            ],
            lifetime_range=(0.5, 1.0),
            size_range=(6, 12),
            speed_range=(100, 250),
            gravity=30.0,
            drag=0.97,
        )

    def emit(
        self,
        emitter_name: str,
        x: float,
        y: float,
        count: int = 20,
        direction: float = None,
        spread: float = 360.0,
    ) -> None:
        """Emit particles using a named emitter."""
        emitter = self.emitters.get(emitter_name)
        if emitter:
            new_particles = emitter.emit(x, y, count, direction, spread)
            self.particles.extend(new_particles)

    def emit_burst(self, x: float, y: float, emitter_name: str = "confetti", count: int = 30) -> None:
        """Emit a radial burst of particles."""
        self.emit(emitter_name, x, y, count, direction=None, spread=360.0)

    def emit_fountain(self, x: float, y: float, emitter_name: str = "confetti", count: int = 20) -> None:
        """Emit particles upward in a fountain pattern."""
        self.emit(emitter_name, x, y, count, direction=-90, spread=60.0)

    def clear(self) -> None:
        """Remove all particles."""
        self.particles.clear()

    def update(self, dt: float) -> None:
        """Update all particles."""
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface: pygame.Surface) -> None:
        """Draw all particles."""
        for particle in self.particles:
            self._draw_particle(surface, particle)

    def _draw_particle(self, surface: pygame.Surface, particle: Particle) -> None:
        """Draw a single particle."""
        alpha = int(particle.alpha)
        if alpha <= 0:
            return

        if particle.particle_type == ParticleType.CONFETTI:
            self._draw_confetti(surface, particle, alpha)
        elif particle.particle_type == ParticleType.SPARK:
            self._draw_spark(surface, particle, alpha)
        elif particle.particle_type == ParticleType.COIN:
            self._draw_coin(surface, particle, alpha)
        elif particle.particle_type == ParticleType.STAR:
            self._draw_star(surface, particle, alpha)
        else:
            self._draw_simple(surface, particle, alpha)

    def _draw_confetti(self, surface: pygame.Surface, p: Particle, alpha: int) -> None:
        """Draw confetti particle (rectangle that tumbles)."""
        # Create a small rectangle
        size = int(p.size)
        conf_surface = pygame.Surface((size, size // 2), pygame.SRCALPHA)
        color_with_alpha = (*p.color, alpha)
        pygame.draw.rect(conf_surface, color_with_alpha, (0, 0, size, size // 2))

        # Rotate
        rotated = pygame.transform.rotate(conf_surface, p.rotation)
        rect = rotated.get_rect(center=(int(p.x), int(p.y)))
        surface.blit(rotated, rect)

    def _draw_spark(self, surface: pygame.Surface, p: Particle, alpha: int) -> None:
        """Draw spark particle (bright point with trail)."""
        # Draw a small circle with glow
        for i in range(3):
            glow_alpha = alpha // (i + 1)
            glow_size = int(p.size * (1 + i * 0.5))
            glow_color = (*p.color, glow_alpha)
            glow_surface = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, glow_color, (glow_size, glow_size), glow_size)
            rect = glow_surface.get_rect(center=(int(p.x), int(p.y)))
            surface.blit(glow_surface, rect)

    def _draw_coin(self, surface: pygame.Surface, p: Particle, alpha: int) -> None:
        """Draw coin particle (circle with shine)."""
        size = int(p.size)

        # Draw main coin
        coin_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(coin_surface, (*p.color, alpha), (size, size), size)

        # Add shine (lighter spot)
        shine_color = (255, 255, 200, alpha // 2)
        pygame.draw.circle(coin_surface, shine_color, (size - 2, size - 2), size // 3)

        rect = coin_surface.get_rect(center=(int(p.x), int(p.y)))
        surface.blit(coin_surface, rect)

    def _draw_star(self, surface: pygame.Surface, p: Particle, alpha: int) -> None:
        """Draw star particle (4-pointed star)."""
        size = int(p.size)
        cx, cy = int(p.x), int(p.y)

        # Create points for a 4-pointed star
        angle = math.radians(p.rotation)
        points = []
        for i in range(8):
            a = angle + i * math.pi / 4
            r = size if i % 2 == 0 else size // 2
            px = cx + math.cos(a) * r
            py = cy + math.sin(a) * r
            points.append((px, py))

        # Draw with alpha
        star_surface = pygame.Surface((size * 3, size * 3), pygame.SRCALPHA)
        offset_points = [(px - cx + size * 1.5, py - cy + size * 1.5) for px, py in points]
        pygame.draw.polygon(star_surface, (*p.color, alpha), offset_points)

        rect = star_surface.get_rect(center=(cx, cy))
        surface.blit(star_surface, rect)

    def _draw_simple(self, surface: pygame.Surface, p: Particle, alpha: int) -> None:
        """Draw a simple circle particle."""
        size = int(p.size)
        particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(particle_surface, (*p.color, alpha), (size, size), size)
        rect = particle_surface.get_rect(center=(int(p.x), int(p.y)))
        surface.blit(particle_surface, rect)

    @property
    def particle_count(self) -> int:
        """Get current particle count."""
        return len(self.particles)


# Global particle system instance
_particle_system: Optional[ParticleSystem] = None


def get_particle_system() -> ParticleSystem:
    """Get the global particle system instance."""
    global _particle_system
    if _particle_system is None:
        _particle_system = ParticleSystem()
    return _particle_system
