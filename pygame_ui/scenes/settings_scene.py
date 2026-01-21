"""Settings scene with toggles and sliders."""

from typing import Optional, List, Callable

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.panel import Panel
from pygame_ui.effects.crt_filter import CRTFilter
from pygame_ui.core.sound_manager import get_sound_manager, play_sound


class Toggle:
    """A toggle switch component."""

    def __init__(
        self,
        x: float,
        y: float,
        label: str,
        initial_state: bool = False,
        on_change: Callable[[bool], None] = None,
        width: int = 60,
        height: int = 30,
    ):
        self.x = x
        self.y = y
        self.label = label
        self.state = initial_state
        self.on_change = on_change
        self.width = width
        self.height = height

        self._hovered = False
        self._animation_progress = 1.0 if initial_state else 0.0
        self._target_progress = self._animation_progress

        # Font
        self._font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 28)
        return self._font

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - self.width // 2),
            int(self.y - self.height // 2),
            self.width,
            self.height,
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.state = not self.state
                self._target_progress = 1.0 if self.state else 0.0
                play_sound("button_click")
                if self.on_change:
                    self.on_change(self.state)
                return True

        return False

    def update(self, dt: float) -> None:
        # Animate toggle
        speed = 8.0
        if self._animation_progress < self._target_progress:
            self._animation_progress = min(
                self._target_progress,
                self._animation_progress + dt * speed
            )
        elif self._animation_progress > self._target_progress:
            self._animation_progress = max(
                self._target_progress,
                self._animation_progress - dt * speed
            )

    def draw(self, surface: pygame.Surface) -> None:
        # Draw label
        label_surface = self.font.render(self.label, True, COLORS.TEXT_WHITE)
        label_rect = label_surface.get_rect(
            midright=(self.x - self.width // 2 - 20, self.y)
        )
        surface.blit(label_surface, label_rect)

        # Draw track
        track_color = (
            int(60 + 40 * self._animation_progress),
            int(60 + 70 * self._animation_progress),
            int(60 + 40 * self._animation_progress),
        )
        pygame.draw.rect(
            surface,
            track_color,
            self.rect,
            border_radius=self.height // 2,
        )

        # Draw border
        border_color = COLORS.GOLD if self._hovered else COLORS.TEXT_MUTED
        pygame.draw.rect(
            surface,
            border_color,
            self.rect,
            width=2,
            border_radius=self.height // 2,
        )

        # Draw knob
        knob_radius = self.height // 2 - 4
        knob_x = int(
            self.x - self.width // 2 + knob_radius + 4 +
            self._animation_progress * (self.width - 2 * knob_radius - 8)
        )
        pygame.draw.circle(
            surface,
            COLORS.TEXT_WHITE,
            (knob_x, int(self.y)),
            knob_radius,
        )


class Slider:
    """A horizontal slider component."""

    def __init__(
        self,
        x: float,
        y: float,
        label: str,
        min_value: float = 0.0,
        max_value: float = 1.0,
        initial_value: float = 0.5,
        on_change: Callable[[float], None] = None,
        width: int = 200,
        height: int = 20,
    ):
        self.x = x
        self.y = y
        self.label = label
        self.min_value = min_value
        self.max_value = max_value
        self.value = initial_value
        self.on_change = on_change
        self.width = width
        self.height = height

        self._dragging = False
        self._hovered = False

        # Font
        self._font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 28)
        return self._font

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - self.width // 2),
            int(self.y - self.height // 2),
            self.width,
            self.height,
        )

    @property
    def normalized_value(self) -> float:
        return (self.value - self.min_value) / (self.max_value - self.min_value)

    def _value_from_x(self, mouse_x: float) -> float:
        rel_x = mouse_x - (self.x - self.width // 2)
        normalized = max(0, min(1, rel_x / self.width))
        return self.min_value + normalized * (self.max_value - self.min_value)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
            if self._dragging:
                self.value = self._value_from_x(event.pos[0])
                if self.on_change:
                    self.on_change(self.value)
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._dragging = True
                self.value = self._value_from_x(event.pos[0])
                play_sound("button_click")
                if self.on_change:
                    self.on_change(self.value)
                return True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False

        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        # Draw label
        label_surface = self.font.render(self.label, True, COLORS.TEXT_WHITE)
        label_rect = label_surface.get_rect(
            midright=(self.x - self.width // 2 - 20, self.y)
        )
        surface.blit(label_surface, label_rect)

        # Draw track background
        pygame.draw.rect(
            surface,
            COLORS.PANEL_BG,
            self.rect,
            border_radius=self.height // 2,
        )

        # Draw filled portion
        fill_width = int(self.width * self.normalized_value)
        if fill_width > 0:
            fill_rect = pygame.Rect(
                int(self.x - self.width // 2),
                int(self.y - self.height // 2),
                fill_width,
                self.height,
            )
            pygame.draw.rect(
                surface,
                (80, 130, 80),
                fill_rect,
                border_radius=self.height // 2,
            )

        # Draw border
        border_color = COLORS.GOLD if self._hovered or self._dragging else COLORS.TEXT_MUTED
        pygame.draw.rect(
            surface,
            border_color,
            self.rect,
            width=2,
            border_radius=self.height // 2,
        )

        # Draw knob
        knob_x = int(self.x - self.width // 2 + self.width * self.normalized_value)
        knob_radius = self.height // 2 + 4
        pygame.draw.circle(
            surface,
            COLORS.TEXT_WHITE,
            (knob_x, int(self.y)),
            knob_radius,
        )
        pygame.draw.circle(
            surface,
            COLORS.PANEL_BORDER,
            (knob_x, int(self.y)),
            knob_radius,
            width=2,
        )

        # Draw value
        value_text = f"{int(self.value * 100)}%"
        value_surface = self.font.render(value_text, True, COLORS.TEXT_MUTED)
        value_rect = value_surface.get_rect(
            midleft=(self.x + self.width // 2 + 15, self.y)
        )
        surface.blit(value_surface, value_rect)


class SettingsScene(BaseScene):
    """Settings scene with game options."""

    def __init__(self):
        super().__init__()

        # CRT filter for consistency
        self.crt_filter = CRTFilter(
            scanline_alpha=25,
            vignette_strength=0.25,
            enabled=True,
        )

        # UI components
        self.toggles: List[Toggle] = []
        self.sliders: List[Slider] = []
        self.back_button: Optional[Button] = None
        self.panel: Optional[Panel] = None

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._font: Optional[pygame.font.Font] = None

        # Settings values (will be synced with global state)
        self._crt_enabled = True
        self._sound_enabled = True
        self._volume = 0.7

    def _init_fonts(self) -> None:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 64)
            self._font = pygame.font.Font(None, 32)

    def on_enter(self) -> None:
        super().on_enter()
        self._init_fonts()

        # Sync with current settings
        sound_manager = get_sound_manager()
        self._sound_enabled = sound_manager.enabled
        self._volume = sound_manager.volume

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize UI components."""
        center_x = DIMENSIONS.CENTER_X
        start_y = DIMENSIONS.SCREEN_HEIGHT // 3

        # Panel background
        self.panel = Panel(
            x=center_x,
            y=DIMENSIONS.CENTER_Y,
            width=500,
            height=300,
        )

        # CRT toggle
        crt_toggle = Toggle(
            x=center_x + 100,
            y=start_y,
            label="CRT Filter",
            initial_state=self._crt_enabled,
            on_change=self._on_crt_change,
        )

        # Sound toggle
        sound_toggle = Toggle(
            x=center_x + 100,
            y=start_y + 60,
            label="Sound",
            initial_state=self._sound_enabled,
            on_change=self._on_sound_change,
        )

        self.toggles = [crt_toggle, sound_toggle]

        # Volume slider
        volume_slider = Slider(
            x=center_x + 50,
            y=start_y + 130,
            label="Volume",
            min_value=0.0,
            max_value=1.0,
            initial_value=self._volume,
            on_change=self._on_volume_change,
            width=180,
        )

        self.sliders = [volume_slider]

        # Back button
        self.back_button = Button(
            x=center_x,
            y=DIMENSIONS.SCREEN_HEIGHT - 150,
            text="BACK",
            font_size=32,
            on_click=self._go_back,
            bg_color=(100, 60, 60),
            hover_color=(130, 80, 80),
            width=150,
            height=50,
        )

    def _on_crt_change(self, enabled: bool) -> None:
        self._crt_enabled = enabled
        self.crt_filter.enabled = enabled

    def _on_sound_change(self, enabled: bool) -> None:
        self._sound_enabled = enabled
        get_sound_manager().enabled = enabled

    def _on_volume_change(self, value: float) -> None:
        self._volume = value
        get_sound_manager().volume = value

    def _go_back(self) -> None:
        play_sound("button_click")
        self.change_scene("title", transition=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        # Handle toggles
        for toggle in self.toggles:
            if toggle.handle_event(event):
                return True

        # Handle sliders
        for slider in self.sliders:
            if slider.handle_event(event):
                return True

        # Handle back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return True

        return False

    def update(self, dt: float) -> None:
        for toggle in self.toggles:
            toggle.update(dt)
        for slider in self.sliders:
            slider.update(dt)
        if self.back_button:
            self.back_button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self._init_fonts()

        # Background
        surface.fill(COLORS.BACKGROUND)

        # Draw panel
        if self.panel:
            self.panel.draw(surface)

        # Title
        title_surface = self._title_font.render("SETTINGS", True, COLORS.GOLD)
        title_rect = title_surface.get_rect(
            center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT // 5)
        )
        surface.blit(title_surface, title_rect)

        # Draw toggles
        for toggle in self.toggles:
            toggle.draw(surface)

        # Draw sliders
        for slider in self.sliders:
            slider.draw(surface)

        # Draw back button
        if self.back_button:
            self.back_button.draw(surface)

        # Instructions
        instructions = "ESC: Back"
        inst_surface = self._font.render(instructions, True, COLORS.TEXT_MUTED)
        inst_rect = inst_surface.get_rect(
            center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 40)
        )
        surface.blit(inst_surface, inst_rect)

        # Apply CRT
        self.crt_filter.apply(surface)
