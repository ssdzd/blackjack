# PyGame Presentation Layer: Balatro-Style Blackjack Trainer

## Visual Design Analysis

### What Makes Balatro's Aesthetic Work

1. **Pixel Art with Purpose**: Not low-res for nostalgia alone—every pixel is intentional, readable, satisfying
2. **Juice Everywhere**: Cards don't just appear, they *arrive*. Numbers don't just change, they *celebrate*
3. **CRT Nostalgia**: Scanlines, slight bloom, warm color grading
4. **Tactile Feedback**: Everything feels like it has weight and physicality
5. **Clear Hierarchy**: You always know what's important (score multipliers POP)

---

## Project Structure

```
blackjack_trainer/
├── pygame_ui/
│   ├── __init__.py
│   ├── main.py                 # Game loop, event handling
│   ├── config.py               # Colors, dimensions, settings
│   │
│   ├── assets/
│   │   ├── fonts/
│   │   │   ├── pixel_bold.ttf      # Main UI font
│   │   │   └── pixel_numbers.ttf   # Score/count display
│   │   ├── sprites/
│   │   │   ├── cards/              # Card face sprites (52 + backs)
│   │   │   ├── chips/              # Betting chips
│   │   │   ├── ui/                 # Buttons, panels, icons
│   │   │   └── effects/            # Particles, glows
│   │   └── sounds/
│   │       ├── card_deal.wav
│   │       ├── card_flip.wav
│   │       ├── chip_stack.wav
│   │       ├── win_ding.wav
│   │       └── count_tick.wav
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scene_manager.py    # Scene transitions
│   │   ├── camera.py           # Screen shake, zoom
│   │   ├── animation.py        # Tweening, easing functions
│   │   └── particles.py        # Particle system
│   │
│   ├── components/
│   │   ├── __init__.py
│   │   ├── card.py             # Card sprite with animations
│   │   ├── hand.py             # Hand display (fan, stack)
│   │   ├── chip_stack.py       # Animated chip betting
│   │   ├── button.py           # Juicy buttons
│   │   ├── panel.py            # Info panels (count, stats)
│   │   ├── counter.py          # Animated number displays
│   │   ├── toast.py            # Floating notifications
│   │   └── progress_bar.py     # Shoe penetration, etc.
│   │
│   ├── scenes/
│   │   ├── __init__.py
│   │   ├── base_scene.py       # Abstract scene class
│   │   ├── title_scene.py      # Main menu
│   │   ├── game_scene.py       # Main blackjack table
│   │   ├── training_scene.py   # Drill modes
│   │   ├── stats_scene.py      # Session statistics
│   │   └── settings_scene.py   # Configuration
│   │
│   ├── effects/
│   │   ├── __init__.py
│   │   ├── crt_filter.py       # Scanlines, bloom, curvature
│   │   ├── screen_shake.py     # Impact feedback
│   │   ├── glow.py             # Card/button highlights
│   │   └── transitions.py      # Scene wipes, fades
│   │
│   └── utils/
│       ├── __init__.py
│       ├── spritesheet.py      # Sprite loading utilities
│       ├── text.py             # Text rendering helpers
│       └── math_utils.py       # Easing, interpolation
```

---

## Color Palette

```python
# config.py

class Colors:
    # Felt table
    FELT_DARK = (30, 65, 45)
    FELT_MID = (40, 85, 55)
    FELT_LIGHT = (50, 105, 65)
    
    # UI panels
    PANEL_BG = (25, 25, 35, 220)      # Semi-transparent dark
    PANEL_BORDER = (60, 60, 80)
    PANEL_HIGHLIGHT = (80, 80, 110)
    
    # Cards
    CARD_WHITE = (250, 245, 235)      # Warm white, not pure
    CARD_RED = (220, 50, 50)
    CARD_BLACK = (30, 30, 35)
    CARD_SHADOW = (0, 0, 0, 100)
    
    # Accents
    GOLD = (255, 200, 50)
    GOLD_DARK = (200, 150, 30)
    
    # Count display (training mode)
    COUNT_POSITIVE = (80, 220, 120)   # Green = good for player
    COUNT_NEGATIVE = (220, 80, 80)    # Red = bad for player
    COUNT_NEUTRAL = (200, 200, 200)
    
    # Multipliers / highlights
    MULTIPLIER_BLUE = (100, 150, 255)
    HIGHLIGHT_YELLOW = (255, 230, 100)
    
    # Feedback
    WIN_GREEN = (100, 255, 150)
    LOSE_RED = (255, 100, 100)
    PUSH_GRAY = (180, 180, 180)

class Dimensions:
    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    
    CARD_WIDTH = 90
    CARD_HEIGHT = 126
    
    CHIP_SIZE = 40
    
    PANEL_PADDING = 16
    PANEL_RADIUS = 12
    PANEL_BORDER_WIDTH = 3
```

---

## Card Rendering System

### Card Sprite Class

```python
# components/card.py

import pygame
import math
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

class CardState(Enum):
    DECK = "deck"           # In shoe, not visible
    DEALING = "dealing"     # Flying to position
    FACE_DOWN = "face_down" # On table, back showing
    FLIPPING = "flipping"   # Mid-flip animation
    FACE_UP = "face_up"     # Revealed
    HIGHLIGHTED = "highlighted"  # Mouse hover / selected
    DISCARDING = "discarding"    # Flying to discard

@dataclass
class CardAnimation:
    """Current animation state"""
    start_pos: Tuple[float, float]
    end_pos: Tuple[float, float]
    start_rotation: float
    end_rotation: float
    start_scale: float
    end_scale: float
    duration: float
    elapsed: float = 0.0
    easing: str = "ease_out_back"
    
    @property
    def progress(self) -> float:
        return min(self.elapsed / self.duration, 1.0)
    
    @property
    def is_complete(self) -> bool:
        return self.elapsed >= self.duration


class CardSprite(pygame.sprite.Sprite):
    """
    A single card with full animation support.
    Handles position, rotation, scale, flip state, glow effects.
    """
    
    # Class-level sprite cache
    _face_cache: dict = {}
    _back_cache: Optional[pygame.Surface] = None
    
    def __init__(self, 
                 card_data,  # Your core Card object
                 position: Tuple[float, float] = (0, 0)):
        super().__init__()
        
        self.card_data = card_data
        self.state = CardState.DECK
        
        # Transform properties
        self._x, self._y = position
        self._rotation = 0.0        # Degrees
        self._scale = 1.0
        self._flip_progress = 0.0   # 0 = face down, 1 = face up
        
        # Visual effects
        self._glow_intensity = 0.0  # 0-1 for highlight glow
        self._shadow_offset = (4, 6)
        self._hover = False
        
        # Animation queue
        self._current_animation: Optional[CardAnimation] = None
        self._animation_queue: list = []
        
        # Callbacks
        self._on_animation_complete: Optional[callable] = None
        
        # Load/cache sprites
        self._load_sprites()
        self._update_image()
    
    @classmethod
    def _load_sprites(cls):
        """Load and cache card sprites (call once at startup)"""
        if cls._back_cache is not None:
            return
        
        # Load card back
        cls._back_cache = pygame.image.load(
            "assets/sprites/cards/card_back.png"
        ).convert_alpha()
        
        # Load all 52 card faces
        for suit in ['hearts', 'diamonds', 'clubs', 'spades']:
            for rank in range(1, 14):  # A-K
                key = f"{rank}_{suit}"
                path = f"assets/sprites/cards/{key}.png"
                cls._face_cache[key] = pygame.image.load(path).convert_alpha()
    
    @property
    def position(self) -> Tuple[float, float]:
        return (self._x, self._y)
    
    @position.setter
    def position(self, pos: Tuple[float, float]):
        self._x, self._y = pos
        self._update_image()
    
    def animate_to(self,
                   position: Tuple[float, float],
                   rotation: float = None,
                   scale: float = None,
                   duration: float = 0.3,
                   easing: str = "ease_out_back",
                   delay: float = 0.0,
                   on_complete: callable = None):
        """Queue a movement animation"""
        
        anim = CardAnimation(
            start_pos=self.position,
            end_pos=position,
            start_rotation=self._rotation,
            end_rotation=rotation if rotation is not None else self._rotation,
            start_scale=self._scale,
            end_scale=scale if scale is not None else self._scale,
            duration=duration,
            easing=easing
        )
        
        if delay > 0:
            # Add delay as a "wait" animation
            self._animation_queue.append(("wait", delay))
        
        self._animation_queue.append(("move", anim, on_complete))
        
        if self._current_animation is None:
            self._start_next_animation()
    
    def flip(self, duration: float = 0.25, on_complete: callable = None):
        """Animate card flip"""
        self._animation_queue.append(("flip", duration, on_complete))
        
        if self._current_animation is None:
            self._start_next_animation()
    
    def _start_next_animation(self):
        """Pop and start next queued animation"""
        if not self._animation_queue:
            self._current_animation = None
            return
        
        item = self._animation_queue.pop(0)
        anim_type = item[0]
        
        if anim_type == "wait":
            self._current_animation = ("wait", item[1], 0.0)
        elif anim_type == "move":
            self._current_animation = item[1]
            self._on_animation_complete = item[2]
        elif anim_type == "flip":
            self._current_animation = ("flip", item[1], 0.0)
            self._on_animation_complete = item[2]
    
    def update(self, dt: float):
        """Update animation state"""
        if self._current_animation is None:
            return
        
        # Handle different animation types
        if isinstance(self._current_animation, tuple):
            anim_type = self._current_animation[0]
            
            if anim_type == "wait":
                _, duration, elapsed = self._current_animation
                elapsed += dt
                if elapsed >= duration:
                    self._start_next_animation()
                else:
                    self._current_animation = ("wait", duration, elapsed)
                return
            
            elif anim_type == "flip":
                _, duration, elapsed = self._current_animation
                elapsed += dt
                progress = min(elapsed / duration, 1.0)
                
                # Flip uses a sine curve for natural motion
                self._flip_progress = math.sin(progress * math.pi / 2)
                
                if progress >= 1.0:
                    self._flip_progress = 1.0
                    self.state = CardState.FACE_UP
                    if self._on_animation_complete:
                        self._on_animation_complete()
                    self._start_next_animation()
                else:
                    self._current_animation = ("flip", duration, elapsed)
                
                self._update_image()
                return
        
        # Movement animation
        anim = self._current_animation
        anim.elapsed += dt
        
        t = self._apply_easing(anim.progress, anim.easing)
        
        # Interpolate all properties
        self._x = self._lerp(anim.start_pos[0], anim.end_pos[0], t)
        self._y = self._lerp(anim.start_pos[1], anim.end_pos[1], t)
        self._rotation = self._lerp(anim.start_rotation, anim.end_rotation, t)
        self._scale = self._lerp(anim.start_scale, anim.end_scale, t)
        
        self._update_image()
        
        if anim.is_complete:
            if self._on_animation_complete:
                self._on_animation_complete()
            self._start_next_animation()
    
    def _apply_easing(self, t: float, easing: str) -> float:
        """Apply easing function to progress value"""
        if easing == "linear":
            return t
        elif easing == "ease_out":
            return 1 - (1 - t) ** 2
        elif easing == "ease_in_out":
            return t * t * (3 - 2 * t)
        elif easing == "ease_out_back":
            # Overshoots slightly, then settles (satisfying!)
            c1 = 1.70158
            c3 = c1 + 1
            return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)
        elif easing == "ease_out_elastic":
            # Bouncy! Use sparingly
            if t == 0 or t == 1:
                return t
            return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1
        return t
    
    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t
    
    def _update_image(self):
        """Rebuild the card surface with current transforms"""
        # Get base sprite (face or back based on flip progress)
        if self._flip_progress < 0.5:
            base = self._back_cache.copy()
            # Scale X to simulate rotation (card getting thinner)
            scale_x = abs(math.cos(self._flip_progress * math.pi))
        else:
            key = f"{self.card_data.rank.value}_{self.card_data.suit.name.lower()}"
            base = self._face_cache.get(key, self._back_cache).copy()
            scale_x = abs(math.cos(self._flip_progress * math.pi))
        
        # Apply flip scale
        if scale_x < 0.1:
            scale_x = 0.1  # Prevent zero-width
        
        w = int(base.get_width() * self._scale * scale_x)
        h = int(base.get_height() * self._scale)
        
        if w > 0 and h > 0:
            base = pygame.transform.scale(base, (w, h))
        
        # Apply rotation
        if self._rotation != 0:
            base = pygame.transform.rotate(base, self._rotation)
        
        # Add glow effect if highlighted
        if self._glow_intensity > 0:
            base = self._apply_glow(base)
        
        self.image = base
        self.rect = self.image.get_rect(center=(self._x, self._y))
    
    def _apply_glow(self, surface: pygame.Surface) -> pygame.Surface:
        """Add glow effect around card"""
        # Create larger surface for glow
        padding = 20
        glow_surf = pygame.Surface(
            (surface.get_width() + padding * 2, 
             surface.get_height() + padding * 2),
            pygame.SRCALPHA
        )
        
        # Draw glow layers (multiple blurred copies)
        glow_color = (*Colors.HIGHLIGHT_YELLOW[:3], 
                      int(100 * self._glow_intensity))
        
        for i in range(3):
            offset = (i + 1) * 4
            glow_rect = surface.get_rect(
                center=(glow_surf.get_width() // 2,
                        glow_surf.get_height() // 2)
            )
            pygame.draw.rect(glow_surf, glow_color, 
                           glow_rect.inflate(offset, offset),
                           border_radius=8)
        
        # Blit original card on top
        glow_surf.blit(surface, 
                       (padding, padding))
        
        return glow_surf
    
    def draw_shadow(self, surface: pygame.Surface):
        """Draw drop shadow (call before drawing card)"""
        if self.image is None:
            return
        
        shadow = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 60))
        
        # Apply same shape as card
        shadow.blit(self.image, (0, 0), 
                   special_flags=pygame.BLEND_RGBA_MIN)
        
        shadow_pos = (
            self.rect.x + self._shadow_offset[0],
            self.rect.y + self._shadow_offset[1]
        )
        surface.blit(shadow, shadow_pos)
```

---

## Animated Number Counter

The satisfying "rolling" numbers when scores change:

```python
# components/counter.py

import pygame
import math
from typing import Tuple, Optional

class AnimatedCounter:
    """
    Number display that animates between values.
    Balatro-style: numbers roll/tick up with satisfying motion.
    """
    
    def __init__(self,
                 position: Tuple[int, int],
                 font: pygame.font.Font,
                 color: Tuple[int, int, int] = (255, 255, 255),
                 prefix: str = "",
                 suffix: str = "",
                 min_digits: int = 1):
        
        self.position = position
        self.font = font
        self.color = color
        self.prefix = prefix
        self.suffix = suffix
        self.min_digits = min_digits
        
        self._display_value: float = 0
        self._target_value: float = 0
        self._velocity: float = 0
        
        # Animation settings
        self._spring_stiffness = 12.0   # How snappy
        self._spring_damping = 0.7      # How quickly it settles
        
        # Visual effects
        self._scale = 1.0
        self._scale_velocity = 0.0
        self._color_flash: Optional[Tuple[int, int, int]] = None
        self._flash_timer = 0.0
        
    @property
    def value(self) -> int:
        return int(self._target_value)
    
    @value.setter
    def value(self, new_value: int):
        if new_value != self._target_value:
            old_value = self._target_value
            self._target_value = new_value
            
            # Trigger scale pop
            self._scale = 1.3
            self._scale_velocity = 0
            
            # Color flash based on change direction
            if new_value > old_value:
                self._color_flash = (100, 255, 150)  # Green for increase
            else:
                self._color_flash = (255, 100, 100)  # Red for decrease
            self._flash_timer = 0.3
    
    def set_immediate(self, value: int):
        """Set value without animation"""
        self._target_value = value
        self._display_value = value
        self._velocity = 0
    
    def update(self, dt: float):
        """Update animation state"""
        # Spring physics for value
        diff = self._target_value - self._display_value
        
        # Apply spring force
        self._velocity += diff * self._spring_stiffness * dt
        self._velocity *= (1 - self._spring_damping * dt * 10)
        self._display_value += self._velocity * dt * 60
        
        # Snap when close enough
        if abs(diff) < 0.5 and abs(self._velocity) < 0.1:
            self._display_value = self._target_value
            self._velocity = 0
        
        # Scale spring (for pop effect)
        scale_diff = 1.0 - self._scale
        self._scale_velocity += scale_diff * 20 * dt
        self._scale_velocity *= 0.85
        self._scale += self._scale_velocity
        
        # Flash timer
        if self._flash_timer > 0:
            self._flash_timer -= dt
            if self._flash_timer <= 0:
                self._color_flash = None
    
    def draw(self, surface: pygame.Surface):
        """Render the counter"""
        # Format number
        display_int = int(round(self._display_value))
        number_str = str(display_int).zfill(self.min_digits)
        full_text = f"{self.prefix}{number_str}{self.suffix}"
        
        # Determine color
        current_color = self._color_flash if self._color_flash else self.color
        
        # Render text
        text_surface = self.font.render(full_text, True, current_color)
        
        # Apply scale
        if self._scale != 1.0:
            new_width = int(text_surface.get_width() * self._scale)
            new_height = int(text_surface.get_height() * self._scale)
            text_surface = pygame.transform.scale(
                text_surface, (new_width, new_height)
            )
        
        # Center on position
        rect = text_surface.get_rect(center=self.position)
        surface.blit(text_surface, rect)


class CountDisplay(AnimatedCounter):
    """
    Specialized counter for card count display.
    Changes color based on positive/negative value.
    """
    
    def __init__(self, position: Tuple[int, int], font: pygame.font.Font):
        super().__init__(position, font, prefix="RC: ")
        
        self.positive_color = (80, 220, 120)   # Green
        self.negative_color = (220, 80, 80)    # Red  
        self.neutral_color = (200, 200, 200)   # Gray
    
    def update(self, dt: float):
        super().update(dt)
        
        # Update base color based on value
        if self._display_value > 0.5:
            self.color = self.positive_color
        elif self._display_value < -0.5:
            self.color = self.negative_color
        else:
            self.color = self.neutral_color
```

---

## Floating Toast Notifications

The "+10" popups that float up and fade:

```python
# components/toast.py

import pygame
from typing import Tuple, List
from dataclasses import dataclass
import math

@dataclass
class Toast:
    """A single floating notification"""
    text: str
    x: float
    y: float
    color: Tuple[int, int, int]
    font: pygame.font.Font
    lifetime: float = 1.5
    elapsed: float = 0.0
    velocity_y: float = -80  # Pixels per second, negative = up
    scale: float = 1.0
    
    @property
    def alpha(self) -> int:
        """Fade out near end of life"""
        remaining = self.lifetime - self.elapsed
        if remaining < 0.5:
            return int(255 * (remaining / 0.5))
        return 255
    
    @property
    def is_alive(self) -> bool:
        return self.elapsed < self.lifetime


class ToastManager:
    """
    Manages floating notification popups.
    Use for: score changes, count updates, win/lose feedback
    """
    
    def __init__(self):
        self.toasts: List[Toast] = []
        self.default_font: pygame.font.Font = None
    
    def set_font(self, font: pygame.font.Font):
        self.default_font = font
    
    def spawn(self,
              text: str,
              position: Tuple[int, int],
              color: Tuple[int, int, int] = (255, 255, 255),
              font: pygame.font.Font = None,
              scale: float = 1.0,
              lifetime: float = 1.5):
        """Create a new floating toast"""
        
        toast = Toast(
            text=text,
            x=position[0],
            y=position[1],
            color=color,
            font=font or self.default_font,
            scale=scale,
            lifetime=lifetime
        )
        
        # Add slight horizontal randomness
        toast.x += (hash(text) % 20) - 10
        
        self.toasts.append(toast)
    
    def spawn_score(self, amount: int, position: Tuple[int, int]):
        """Convenience method for score popups"""
        if amount > 0:
            self.spawn(f"+{amount}", position, color=(100, 255, 150), scale=1.2)
        elif amount < 0:
            self.spawn(str(amount), position, color=(255, 100, 100), scale=1.0)
    
    def spawn_count_change(self, change: int, position: Tuple[int, int]):
        """Convenience method for count change popups"""
        if change > 0:
            self.spawn(f"+{change}", position, color=(80, 220, 120), scale=0.8)
        elif change < 0:
            self.spawn(str(change), position, color=(220, 80, 80), scale=0.8)
    
    def spawn_result(self, result: str, position: Tuple[int, int]):
        """Win/Lose/Push popup"""
        colors = {
            "WIN": (100, 255, 150),
            "BLACKJACK": (255, 215, 0),
            "LOSE": (255, 100, 100),
            "BUST": (255, 80, 80),
            "PUSH": (180, 180, 180),
        }
        color = colors.get(result.upper(), (255, 255, 255))
        self.spawn(result.upper(), position, color=color, scale=1.5, lifetime=2.0)
    
    def update(self, dt: float):
        """Update all toasts"""
        for toast in self.toasts:
            toast.elapsed += dt
            toast.y += toast.velocity_y * dt
            
            # Slow down as it rises
            toast.velocity_y *= 0.98
            
            # Slight scale pulse at start
            if toast.elapsed < 0.2:
                toast.scale = 1.0 + 0.3 * math.sin(toast.elapsed * 20)
        
        # Remove dead toasts
        self.toasts = [t for t in self.toasts if t.is_alive]
    
    def draw(self, surface: pygame.Surface):
        """Render all toasts"""
        for toast in self.toasts:
            # Render text
            text_surf = toast.font.render(toast.text, True, toast.color)
            
            # Apply scale
            if toast.scale != 1.0:
                new_size = (
                    int(text_surf.get_width() * toast.scale),
                    int(text_surf.get_height() * toast.scale)
                )
                text_surf = pygame.transform.scale(text_surf, new_size)
            
            # Apply alpha
            text_surf.set_alpha(toast.alpha)
            
            # Draw centered on position
            rect = text_surf.get_rect(center=(toast.x, toast.y))
            surface.blit(text_surf, rect)
```

---

## CRT Post-Processing Effect

The retro scanline filter that ties everything together:

```python
# effects/crt_filter.py

import pygame
import math
from typing import Tuple

class CRTFilter:
    """
    Post-processing filter for CRT monitor aesthetic.
    Apply after all game rendering, before display flip.
    """
    
    def __init__(self, screen_size: Tuple[int, int]):
        self.width, self.height = screen_size
        
        # Pre-render scanline overlay
        self._scanline_surface = self._create_scanlines()
        
        # Pre-render vignette
        self._vignette_surface = self._create_vignette()
        
        # Settings
        self.scanline_intensity = 0.15    # 0-1
        self.vignette_intensity = 0.3     # 0-1
        self.chromatic_aberration = 2     # Pixels of RGB shift
        self.curvature = 0.0              # 0 = flat, 0.1 = subtle curve
        self.bloom_intensity = 0.1        # Glow on bright areas
        
    def _create_scanlines(self) -> pygame.Surface:
        """Create scanline overlay texture"""
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Draw horizontal lines every 2-3 pixels
        line_spacing = 3
        line_alpha = 40
        
        for y in range(0, self.height, line_spacing):
            pygame.draw.line(
                surface,
                (0, 0, 0, line_alpha),
                (0, y),
                (self.width, y)
            )
        
        return surface
    
    def _create_vignette(self) -> pygame.Surface:
        """Create edge darkening effect"""
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        center_x = self.width // 2
        center_y = self.height // 2
        max_dist = math.sqrt(center_x**2 + center_y**2)
        
        # Draw radial gradient (simplified with circles)
        for i in range(100, 0, -1):
            progress = i / 100
            radius = int(max_dist * progress)
            alpha = int(150 * (1 - progress) ** 2)
            
            pygame.draw.circle(
                surface,
                (0, 0, 0, alpha),
                (center_x, center_y),
                radius
            )
        
        return surface
    
    def apply(self, surface: pygame.Surface) -> pygame.Surface:
        """Apply CRT effects to rendered frame"""
        result = surface.copy()
        
        # Apply chromatic aberration (RGB channel shift)
        if self.chromatic_aberration > 0:
            result = self._apply_chromatic_aberration(result)
        
        # Apply bloom (glow on bright pixels)
        if self.bloom_intensity > 0:
            result = self._apply_bloom(result)
        
        # Apply scanlines
        if self.scanline_intensity > 0:
            scanlines = self._scanline_surface.copy()
            scanlines.set_alpha(int(255 * self.scanline_intensity))
            result.blit(scanlines, (0, 0))
        
        # Apply vignette
        if self.vignette_intensity > 0:
            vignette = self._vignette_surface.copy()
            vignette.set_alpha(int(255 * self.vignette_intensity))
            result.blit(vignette, (0, 0))
        
        return result
    
    def _apply_chromatic_aberration(self, surface: pygame.Surface) -> pygame.Surface:
        """Shift RGB channels slightly for retro monitor effect"""
        # This is expensive - use sparingly or pre-compute
        offset = self.chromatic_aberration
        
        # Create separate channel surfaces
        r_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        b_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        
        # Extract and offset red channel (shift left)
        r_surf.blit(surface, (-offset, 0))
        r_surf.fill((255, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)
        
        # Extract and offset blue channel (shift right)  
        b_surf.blit(surface, (offset, 0))
        b_surf.fill((0, 0, 255, 255), special_flags=pygame.BLEND_RGBA_MIN)
        
        # Combine: original green + shifted red/blue
        result = surface.copy()
        result.fill((0, 255, 0, 255), special_flags=pygame.BLEND_RGBA_MIN)
        result.blit(r_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        result.blit(b_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        return result
    
    def _apply_bloom(self, surface: pygame.Surface) -> pygame.Surface:
        """Add glow to bright areas"""
        # Downsample, blur, blend back
        small_size = (self.width // 4, self.height // 4)
        
        # Downscale
        small = pygame.transform.scale(surface, small_size)
        
        # Threshold to keep only bright pixels (simplified)
        # In practice you'd extract pixels above brightness threshold
        
        # Upscale back (creates blur effect)
        bloom = pygame.transform.scale(small, (self.width, self.height))
        bloom.set_alpha(int(255 * self.bloom_intensity))
        
        # Additive blend
        result = surface.copy()
        result.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        return result
```

---

## Screen Shake System

For satisfying impact feedback:

```python
# effects/screen_shake.py

import pygame
import random
import math
from typing import Tuple

class ScreenShake:
    """
    Camera shake effect for impactful moments.
    Use for: blackjack hit, big wins, busts
    """
    
    def __init__(self):
        self._trauma = 0.0          # Current shake intensity (0-1)
        self._decay_rate = 3.0      # How fast shake dies down
        self._max_offset = 15       # Max pixels of displacement
        self._max_rotation = 3      # Max degrees of rotation
        
        # Noise seeds for smooth randomness
        self._seed = random.random() * 1000
        
    def add_trauma(self, amount: float):
        """Add shake intensity (0-1 range, will be clamped)"""
        self._trauma = min(1.0, self._trauma + amount)
    
    def shake_small(self):
        """Preset: small impact (card dealt)"""
        self.add_trauma(0.15)
    
    def shake_medium(self):
        """Preset: medium impact (hit, stand)"""
        self.add_trauma(0.3)
    
    def shake_large(self):
        """Preset: large impact (blackjack, bust)"""
        self.add_trauma(0.6)
    
    def update(self, dt: float):
        """Decay trauma over time"""
        self._trauma = max(0, self._trauma - self._decay_rate * dt)
        self._seed += dt * 50  # Advance noise
    
    def get_offset(self) -> Tuple[float, float]:
        """Get current shake offset for camera/rendering"""
        if self._trauma <= 0:
            return (0, 0)
        
        # Use trauma squared for more dramatic falloff
        shake = self._trauma ** 2
        
        # Perlin-ish noise (simplified with sin)
        offset_x = math.sin(self._seed) * self._max_offset * shake
        offset_y = math.cos(self._seed * 1.3) * self._max_offset * shake
        
        return (offset_x, offset_y)
    
    def get_rotation(self) -> float:
        """Get current rotation offset"""
        if self._trauma <= 0:
            return 0
        
        shake = self._trauma ** 2
        return math.sin(self._seed * 0.7) * self._max_rotation * shake
    
    def apply_to_surface(self, 
                         surface: pygame.Surface,
                         target: pygame.Surface) -> None:
        """
        Blit surface onto target with shake applied.
        Call this instead of direct blit when shake is active.
        """
        offset = self.get_offset()
        # rotation = self.get_rotation()  # Optional, more expensive
        
        target.blit(surface, offset)
```

---

## Main Game Scene Structure

Putting it all together:

```python
# scenes/game_scene.py

import pygame
from typing import List, Optional
from components.card import CardSprite, CardState
from components.counter import CountDisplay, AnimatedCounter
from components.toast import ToastManager
from components.panel import Panel
from effects.crt_filter import CRTFilter
from effects.screen_shake import ScreenShake

class GameScene:
    """
    Main blackjack table scene.
    Orchestrates all visual components.
    """
    
    def __init__(self, screen: pygame.Surface, game_engine):
        self.screen = screen
        self.engine = game_engine  # Your core blackjack engine
        
        self.width = screen.get_width()
        self.height = screen.get_height()
        
        # Load assets
        self._load_fonts()
        self._load_sounds()
        
        # Initialize effects
        self.crt_filter = CRTFilter((self.width, self.height))
        self.screen_shake = ScreenShake()
        self.toast_manager = ToastManager()
        self.toast_manager.set_font(self.font_large)
        
        # Game render target (we render here, then apply effects)
        self.game_surface = pygame.Surface((self.width, self.height))
        
        # Card sprites
        self.player_cards: List[CardSprite] = []
        self.dealer_cards: List[CardSprite] = []
        
        # UI Components
        self._init_ui_components()
        
        # Subscribe to game events
        self.engine.subscribe(self._on_game_event)
        
        # Layout positions
        self.DEALER_HAND_POS = (self.width // 2, 180)
        self.PLAYER_HAND_POS = (self.width // 2, 450)
        self.DECK_POS = (self.width - 100, 180)
        
    def _load_fonts(self):
        self.font_small = pygame.font.Font("assets/fonts/pixel.ttf", 16)
        self.font_medium = pygame.font.Font("assets/fonts/pixel.ttf", 24)
        self.font_large = pygame.font.Font("assets/fonts/pixel.ttf", 36)
        self.font_huge = pygame.font.Font("assets/fonts/pixel_bold.ttf", 48)
    
    def _load_sounds(self):
        self.sounds = {
            'deal': pygame.mixer.Sound("assets/sounds/card_deal.wav"),
            'flip': pygame.mixer.Sound("assets/sounds/card_flip.wav"),
            'chip': pygame.mixer.Sound("assets/sounds/chip_stack.wav"),
            'win': pygame.mixer.Sound("assets/sounds/win_ding.wav"),
        }
    
    def _init_ui_components(self):
        # Left sidebar - count display panel
        self.count_panel = Panel(
            rect=pygame.Rect(20, 20, 200, 300),
            title="Count"
        )
        
        self.running_count = CountDisplay(
            position=(120, 80),
            font=self.font_large
        )
        
        self.true_count = CountDisplay(
            position=(120, 140),
            font=self.font_large
        )
        self.true_count.prefix = "TC: "
        
        # Bankroll display
        self.bankroll_counter = AnimatedCounter(
            position=(120, 550),
            font=self.font_medium,
            prefix="$",
            color=(255, 215, 0)  # Gold
        )
        
        # Stats panel (right side)
        self.stats_panel = Panel(
            rect=pygame.Rect(self.width - 220, 20, 200, 200),
            title="Statistics"
        )
    
    def _on_game_event(self, event):
        """Handle events from game engine"""
        
        if event.event_type == "card_dealt":
            self._animate_deal_card(event.data)
            self.sounds['deal'].play()
            self.screen_shake.shake_small()
            
        elif event.event_type == "card_flipped":
            self._animate_flip_card(event.data)
            self.sounds['flip'].play()
            
        elif event.event_type == "count_updated":
            old_rc = self.running_count.value
            new_rc = event.data['running_count']
            self.running_count.value = new_rc
            self.true_count.value = event.data['true_count']
            
            # Spawn count change toast
            change = new_rc - old_rc
            if change != 0:
                # Position near the card that was just dealt
                self.toast_manager.spawn_count_change(
                    change, 
                    event.data.get('card_position', (self.width//2, 300))
                )
        
        elif event.event_type == "hand_resolved":
            result = event.data['result']
            payout = event.data['payout']
            
            # Result toast
            self.toast_manager.spawn_result(result, self.PLAYER_HAND_POS)
            
            # Bankroll update
            self.bankroll_counter.value += payout
            
            if result in ["BLACKJACK", "WIN"]:
                self.screen_shake.shake_large()
                self.sounds['win'].play()
            elif result == "BUST":
                self.screen_shake.shake_medium()
    
    def _animate_deal_card(self, data):
        """Create and animate a new card sprite"""
        card_data = data['card']
        target = data['target']  # "player" or "dealer"
        
        # Create sprite at deck position
        sprite = CardSprite(card_data, position=self.DECK_POS)
        sprite.state = CardState.DEALING
        
        # Calculate target position in hand
        if target == "player":
            cards = self.player_cards
            base_pos = self.PLAYER_HAND_POS
        else:
            cards = self.dealer_cards
            base_pos = self.DEALER_HAND_POS
        
        # Fan out cards
        card_index = len(cards)
        offset_x = (card_index - 1) * 30  # 30px between cards
        target_pos = (base_pos[0] + offset_x, base_pos[1])
        
        # Slight rotation for visual interest
        target_rotation = (card_index - 1) * 2 - 2
        
        # Animate!
        sprite.animate_to(
            position=target_pos,
            rotation=target_rotation,
            duration=0.3,
            easing="ease_out_back",
            on_complete=lambda: setattr(sprite, 'state', CardState.FACE_DOWN)
        )
        
        cards.append(sprite)
    
    def update(self, dt: float):
        """Update all animated components"""
        # Update card animations
        for card in self.player_cards + self.dealer_cards:
            card.update(dt)
        
        # Update UI counters
        self.running_count.update(dt)
        self.true_count.update(dt)
        self.bankroll_counter.update(dt)
        
        # Update effects
        self.toast_manager.update(dt)
        self.screen_shake.update(dt)
    
    def draw(self):
        """Render the scene"""
        # Clear game surface
        self.game_surface.fill(Colors.FELT_DARK)
        
        # Draw felt texture/pattern
        self._draw_felt_background()
        
        # Draw card shadows first (under everything)
        for card in self.dealer_cards + self.player_cards:
            card.draw_shadow(self.game_surface)
        
        # Draw cards
        for card in self.dealer_cards:
            self.game_surface.blit(card.image, card.rect)
        for card in self.player_cards:
            self.game_surface.blit(card.image, card.rect)
        
        # Draw UI panels
        self.count_panel.draw(self.game_surface)
        self.running_count.draw(self.game_surface)
        self.true_count.draw(self.game_surface)
        
        self.stats_panel.draw(self.game_surface)
        self.bankroll_counter.draw(self.game_surface)
        
        # Draw toasts (on top of everything)
        self.toast_manager.draw(self.game_surface)
        
        # Apply screen shake
        shake_offset = self.screen_shake.get_offset()
        
        # Apply CRT filter
        final_surface = self.crt_filter.apply(self.game_surface)
        
        # Blit to screen with shake
        self.screen.fill((0, 0, 0))  # Black border for shake
        self.screen.blit(final_surface, shake_offset)
    
    def _draw_felt_background(self):
        """Draw the green felt table texture"""
        # Simple gradient for now - could be a texture
        for y in range(0, self.height, 4):
            progress = y / self.height
            color = (
                int(Colors.FELT_DARK[0] + (Colors.FELT_LIGHT[0] - Colors.FELT_DARK[0]) * progress * 0.3),
                int(Colors.FELT_DARK[1] + (Colors.FELT_LIGHT[1] - Colors.FELT_DARK[1]) * progress * 0.3),
                int(Colors.FELT_DARK[2] + (Colors.FELT_LIGHT[2] - Colors.FELT_DARK[2]) * progress * 0.3),
            )
            pygame.draw.line(self.game_surface, color, (0, y), (self.width, y))
```

---

## Asset Creation Guide

### Card Sprites

For that Balatro look, your cards need:

1. **Resolution**: 90×126 pixels (or 2x for hi-DPI: 180×252)
2. **Style**: Thick black outlines (2-3px), flat colors, simplified faces
3. **Face cards**: Stylized characters, not realistic portraits

**Tools:**
- Aseprite (pixel art, $20, worth it)
- Piskel (free, web-based)
- PyxelEdit (tiles and sprites)

**Quick option:** Start with CC0 pixel card assets from itch.io, customize colors

### Fonts

Recommended free pixel fonts:
- **Press Start 2P** (Google Fonts) - chunky arcade style
- **VT323** (Google Fonts) - terminal/CRT feel
- **Pixelify Sans** (Google Fonts) - modern pixel
- **m5x7** / **m3x6** by Daniel Linssen - tiny and readable

### Sounds

Free sources:
- **freesound.org** - search "card", "chip", "casino"
- **kenney.nl/assets** - free game audio packs
- **jsfxr** (web app) - generate retro sound effects

---

## Performance Considerations

```python
# Optimization tips for smooth 60fps

# 1. Pre-render static elements
class OptimizedPanel:
    def __init__(self, ...):
        self._cached_surface = None
        self._dirty = True
    
    def draw(self, surface):
        if self._dirty:
            self._cached_surface = self._render()
            self._dirty = False
        surface.blit(self._cached_surface, self.rect)

# 2. Sprite groups for batch rendering
self.card_group = pygame.sprite.Group()
self.card_group.draw(surface)  # More efficient than individual blits

# 3. Dirty rect updating (only redraw changed areas)
# PyGame has built-in support: pygame.display.update(dirty_rects)

# 4. Reduce CRT filter quality for performance
class CRTFilter:
    def __init__(self, ..., quality="high"):
        if quality == "low":
            self.chromatic_aberration = 0  # Disable expensive effects
            self.bloom_intensity = 0

# 5. Object pooling for particles/toasts
class ToastPool:
    def __init__(self, size=50):
        self.pool = [Toast() for _ in range(size)]
        self.active = []
```

---

## Development Phases

### Phase 1: Foundation (3-4 days)
- [ ] Basic PyGame window and game loop
- [ ] Load placeholder card sprites
- [ ] Card sprite class with position/scale
- [ ] Basic animation system (tweening)

### Phase 2: Card Polish (3-4 days)
- [ ] Deal animation (deck to hand)
- [ ] Flip animation
- [ ] Card hover/selection glow
- [ ] Drop shadows
- [ ] Hand layout (fan spacing)

### Phase 3: UI Components (3-4 days)
- [ ] Panel component (rounded, bordered)
- [ ] Animated counter
- [ ] Toast notifications
- [ ] Buttons with hover/press states

### Phase 4: Effects (2-3 days)
- [ ] Screen shake
- [ ] CRT scanlines
- [ ] Vignette
- [ ] Optional: chromatic aberration, bloom

### Phase 5: Integration (2-3 days)
- [ ] Connect to core engine events
- [ ] Count display updates
- [ ] Bet/bankroll UI
- [ ] Win/lose feedback

### Phase 6: Polish (ongoing)
- [ ] Sound effects
- [ ] Music
- [ ] Custom pixel card art
- [ ] Settings menu
- [ ] Training mode visibility toggles

---

## Key Takeaways

1. **Juice is in the details**: Easing functions, screen shake, number pops—these make it *feel* good
2. **Layer your rendering**: Background → shadows → cards → UI → effects → CRT filter
3. **Event-driven animation**: Don't poll state, react to game events
4. **Cache everything static**: Pre-render panels, scanlines, vignettes
5. **Start ugly, polish later**: Get animations working with rectangles before pixel art

The Balatro aesthetic is achievable—it's fundamentally clean pixel art plus *generous* application of juice. Every action should have feedback. Every number should animate. Every card should *arrive*, not just appear.
