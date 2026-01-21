"""Settings scene with toggles and sliders for game configuration."""

from typing import Optional, List, Callable

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.panel import Panel
from pygame_ui.effects.crt_filter import CRTFilter
from pygame_ui.core.sound_manager import get_sound_manager, play_sound
from pygame_ui.core.game_settings import get_settings_manager, TableRules


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
        step: float = 0.0,
        value_format: str = "{:.0%}",
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
        self.step = step
        self.value_format = value_format

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
        raw_value = self.min_value + normalized * (self.max_value - self.min_value)
        if self.step > 0:
            raw_value = round(raw_value / self.step) * self.step
        return raw_value

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
            if self._dragging:
                new_value = self._value_from_x(event.pos[0])
                if new_value != self.value:
                    self.value = new_value
                    if self.on_change:
                        self.on_change(self.value)
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._dragging = True
                new_value = self._value_from_x(event.pos[0])
                if new_value != self.value:
                    self.value = new_value
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
        value_text = self.value_format.format(self.value)
        value_surface = self.font.render(value_text, True, COLORS.TEXT_MUTED)
        value_rect = value_surface.get_rect(
            midleft=(self.x + self.width // 2 + 15, self.y)
        )
        surface.blit(value_surface, value_rect)


class OptionSelector:
    """A multi-option selector (radio button style)."""

    def __init__(
        self,
        x: float,
        y: float,
        label: str,
        options: List[tuple[str, str]],  # (value, display_label)
        initial_value: str,
        on_change: Callable[[str], None] = None,
    ):
        self.x = x
        self.y = y
        self.label = label
        self.options = options
        self.value = initial_value
        self.on_change = on_change

        self._hovered_index = -1
        self._font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 24)
        return self._font

    def _get_option_rects(self) -> List[pygame.Rect]:
        """Get rectangles for each option."""
        rects = []
        option_width = 70
        total_width = len(self.options) * option_width
        start_x = self.x - total_width // 2

        for i in range(len(self.options)):
            rect = pygame.Rect(
                int(start_x + i * option_width),
                int(self.y - 15),
                option_width - 4,
                30,
            )
            rects.append(rect)
        return rects

    def handle_event(self, event: pygame.event.Event) -> bool:
        rects = self._get_option_rects()

        if event.type == pygame.MOUSEMOTION:
            self._hovered_index = -1
            for i, rect in enumerate(rects):
                if rect.collidepoint(event.pos):
                    self._hovered_index = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(rects):
                if rect.collidepoint(event.pos):
                    new_value = self.options[i][0]
                    if new_value != self.value:
                        self.value = new_value
                        play_sound("button_click")
                        if self.on_change:
                            self.on_change(self.value)
                    return True

        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        # Draw label
        label_font = pygame.font.Font(None, 28)
        label_surface = label_font.render(self.label, True, COLORS.TEXT_WHITE)
        label_rect = label_surface.get_rect(
            midright=(self.x - 120, self.y)
        )
        surface.blit(label_surface, label_rect)

        # Draw options
        rects = self._get_option_rects()
        for i, (value, display) in enumerate(self.options):
            rect = rects[i]
            is_selected = value == self.value
            is_hovered = i == self._hovered_index

            # Background
            bg_color = (80, 130, 80) if is_selected else COLORS.PANEL_BG
            pygame.draw.rect(surface, bg_color, rect, border_radius=5)

            # Border
            border_color = COLORS.GOLD if is_hovered else COLORS.TEXT_MUTED
            pygame.draw.rect(surface, border_color, rect, width=2, border_radius=5)

            # Text
            text_color = COLORS.TEXT_WHITE if is_selected else COLORS.TEXT_MUTED
            text_surface = self.font.render(display, True, text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            surface.blit(text_surface, text_rect)


class TabBar:
    """Tab bar for switching between settings pages."""

    def __init__(
        self,
        x: float,
        y: float,
        tabs: List[str],
        on_change: Callable[[int], None] = None,
    ):
        self.x = x
        self.y = y
        self.tabs = tabs
        self.active_index = 0
        self.on_change = on_change

        self._font: Optional[pygame.font.Font] = None
        self._tab_width = 140
        self._tab_height = 40

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 28)
        return self._font

    def _get_tab_rects(self) -> List[pygame.Rect]:
        rects = []
        total_width = len(self.tabs) * self._tab_width
        start_x = self.x - total_width // 2

        for i in range(len(self.tabs)):
            rect = pygame.Rect(
                int(start_x + i * self._tab_width),
                int(self.y),
                self._tab_width - 4,
                self._tab_height,
            )
            rects.append(rect)
        return rects

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rects = self._get_tab_rects()
            for i, rect in enumerate(rects):
                if rect.collidepoint(event.pos):
                    if i != self.active_index:
                        self.active_index = i
                        play_sound("button_click")
                        if self.on_change:
                            self.on_change(i)
                    return True
        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        rects = self._get_tab_rects()
        for i, (rect, label) in enumerate(zip(rects, self.tabs)):
            is_active = i == self.active_index

            # Background
            bg_color = (60, 80, 60) if is_active else (40, 40, 45)
            pygame.draw.rect(surface, bg_color, rect, border_radius=5)

            # Border (only top/sides for active tab effect)
            border_color = COLORS.GOLD if is_active else COLORS.TEXT_MUTED
            pygame.draw.rect(surface, border_color, rect, width=2, border_radius=5)

            # Text
            text_color = COLORS.GOLD if is_active else COLORS.TEXT_MUTED
            text_surface = self.font.render(label, True, text_color)
            text_rect = text_surface.get_rect(center=rect.center)
            surface.blit(text_surface, text_rect)


class SettingsScene(BaseScene):
    """Settings scene with game options organized in tabs."""

    def __init__(self):
        super().__init__()

        # CRT filter for consistency
        self.crt_filter = CRTFilter(
            scanline_alpha=25,
            vignette_strength=0.25,
            enabled=True,
        )

        # UI components per tab
        self.tab_bar: Optional[TabBar] = None
        self.toggles: List[Toggle] = []
        self.sliders: List[Slider] = []
        self.selectors: List[OptionSelector] = []
        self.back_button: Optional[Button] = None
        self.reset_button: Optional[Button] = None
        self.panel: Optional[Panel] = None

        # Tab-specific components
        self._audio_toggles: List[Toggle] = []
        self._audio_sliders: List[Slider] = []
        self._rules_toggles: List[Toggle] = []
        self._rules_sliders: List[Slider] = []
        self._rules_selectors: List[OptionSelector] = []
        self._session_sliders: List[Slider] = []
        self._session_toggles: List[Toggle] = []

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._font: Optional[pygame.font.Font] = None

        # Current tab
        self._current_tab = 0  # 0=Audio, 1=Table Rules, 2=Session

        # Settings values (synced with managers)
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

        # Tab bar
        self.tab_bar = TabBar(
            x=center_x,
            y=DIMENSIONS.SCREEN_HEIGHT // 5 + 40,
            tabs=["Audio", "Table Rules", "Session"],
            on_change=self._on_tab_change,
        )

        # Panel background
        self.panel = Panel(
            x=center_x,
            y=DIMENSIONS.CENTER_Y + 20,
            width=600,
            height=340,
        )

        # Setup components for each tab
        self._setup_audio_tab()
        self._setup_rules_tab()
        self._setup_session_tab()

        # Back button
        self.back_button = Button(
            x=center_x - 100,
            y=DIMENSIONS.SCREEN_HEIGHT - 100,
            text="BACK",
            font_size=32,
            on_click=self._go_back,
            bg_color=(100, 60, 60),
            hover_color=(130, 80, 80),
            width=150,
            height=50,
        )

        # Reset defaults button
        self.reset_button = Button(
            x=center_x + 100,
            y=DIMENSIONS.SCREEN_HEIGHT - 100,
            text="RESET",
            font_size=32,
            on_click=self._reset_defaults,
            bg_color=(80, 80, 60),
            hover_color=(110, 110, 80),
            width=150,
            height=50,
        )

        self._update_active_components()

    def _setup_audio_tab(self) -> None:
        """Setup audio settings tab."""
        center_x = DIMENSIONS.CENTER_X
        start_y = DIMENSIONS.CENTER_Y - 40

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

        self._audio_toggles = [crt_toggle, sound_toggle]

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

        self._audio_sliders = [volume_slider]

    def _setup_rules_tab(self) -> None:
        """Setup table rules tab."""
        center_x = DIMENSIONS.CENTER_X
        start_y = DIMENSIONS.CENTER_Y - 80
        settings = get_settings_manager()
        rules = settings.table_rules

        # Number of decks selector
        decks_selector = OptionSelector(
            x=center_x + 60,
            y=start_y,
            label="Decks",
            options=[("1", "1"), ("2", "2"), ("4", "4"), ("6", "6"), ("8", "8")],
            initial_value=str(rules.num_decks),
            on_change=self._on_decks_change,
        )

        # Dealer soft 17 selector
        h17_selector = OptionSelector(
            x=center_x + 60,
            y=start_y + 45,
            label="Soft 17",
            options=[("h17", "H17"), ("s17", "S17")],
            initial_value="h17" if rules.dealer_hits_soft_17 else "s17",
            on_change=self._on_h17_change,
        )

        # Blackjack payout selector
        payout_selector = OptionSelector(
            x=center_x + 60,
            y=start_y + 90,
            label="BJ Payout",
            options=[("3:2", "3:2"), ("6:5", "6:5")],
            initial_value="3:2" if rules.blackjack_payout == 1.5 else "6:5",
            on_change=self._on_payout_change,
        )

        # Double rules selector
        double_selector = OptionSelector(
            x=center_x + 60,
            y=start_y + 135,
            label="Double On",
            options=[("any", "Any"), ("9-11", "9-11"), ("10-11", "10-11")],
            initial_value=rules.double_on,
            on_change=self._on_double_change,
        )

        # Surrender selector
        surrender_selector = OptionSelector(
            x=center_x + 60,
            y=start_y + 180,
            label="Surrender",
            options=[("none", "None"), ("late", "Late")],
            initial_value=rules.surrender,
            on_change=self._on_surrender_change,
        )

        self._rules_selectors = [
            decks_selector,
            h17_selector,
            payout_selector,
            double_selector,
            surrender_selector,
        ]

        # DAS toggle
        das_toggle = Toggle(
            x=center_x + 100,
            y=start_y + 225,
            label="Double After Split",
            initial_state=rules.double_after_split,
            on_change=self._on_das_change,
        )

        # RSA toggle
        rsa_toggle = Toggle(
            x=center_x + 100,
            y=start_y + 270,
            label="Resplit Aces",
            initial_state=rules.resplit_aces,
            on_change=self._on_rsa_change,
        )

        self._rules_toggles = [das_toggle, rsa_toggle]

        # Penetration slider
        penetration_slider = Slider(
            x=center_x + 50,
            y=start_y + 315,
            label="Penetration",
            min_value=0.5,
            max_value=0.9,
            initial_value=rules.penetration,
            step=0.05,
            on_change=self._on_penetration_change,
            width=180,
        )

        self._rules_sliders = [penetration_slider]

    def _setup_session_tab(self) -> None:
        """Setup session goals tab."""
        center_x = DIMENSIONS.CENTER_X
        start_y = DIMENSIONS.CENTER_Y - 60
        settings = get_settings_manager()
        goals = settings.session_goals

        # Win goal slider
        win_slider = Slider(
            x=center_x + 50,
            y=start_y,
            label="Win Goal",
            min_value=0,
            max_value=1000,
            initial_value=goals.win_goal,
            step=50,
            on_change=self._on_win_goal_change,
            width=180,
            value_format="${:.0f}",
        )

        # Loss limit slider
        loss_slider = Slider(
            x=center_x + 50,
            y=start_y + 60,
            label="Loss Limit",
            min_value=0,
            max_value=1000,
            initial_value=goals.loss_limit,
            step=50,
            on_change=self._on_loss_limit_change,
            width=180,
            value_format="${:.0f}",
        )

        # Number of hands slider
        hands_slider = Slider(
            x=center_x + 50,
            y=start_y + 120,
            label="Hands",
            min_value=1,
            max_value=3,
            initial_value=settings.num_hands,
            step=1,
            on_change=self._on_num_hands_change,
            width=180,
            value_format="{:.0f}",
        )

        self._session_sliders = [win_slider, loss_slider, hands_slider]

        # Auto-stop toggle
        auto_stop_toggle = Toggle(
            x=center_x + 100,
            y=start_y + 180,
            label="Auto-Stop at Limit",
            initial_state=goals.auto_stop,
            on_change=self._on_auto_stop_change,
        )

        self._session_toggles = [auto_stop_toggle]

    def _on_tab_change(self, tab_index: int) -> None:
        """Handle tab change."""
        self._current_tab = tab_index
        self._update_active_components()

    def _update_active_components(self) -> None:
        """Update which components are active based on current tab."""
        if self._current_tab == 0:  # Audio
            self.toggles = self._audio_toggles
            self.sliders = self._audio_sliders
            self.selectors = []
        elif self._current_tab == 1:  # Table Rules
            self.toggles = self._rules_toggles
            self.sliders = self._rules_sliders
            self.selectors = self._rules_selectors
        else:  # Session
            self.toggles = self._session_toggles
            self.sliders = self._session_sliders
            self.selectors = []

    # Audio callbacks
    def _on_crt_change(self, enabled: bool) -> None:
        self._crt_enabled = enabled
        self.crt_filter.enabled = enabled

    def _on_sound_change(self, enabled: bool) -> None:
        self._sound_enabled = enabled
        get_sound_manager().enabled = enabled

    def _on_volume_change(self, value: float) -> None:
        self._volume = value
        get_sound_manager().volume = value

    # Rules callbacks
    def _on_decks_change(self, value: str) -> None:
        settings = get_settings_manager()
        settings.settings.table_rules.num_decks = int(value)
        settings.save()

    def _on_h17_change(self, value: str) -> None:
        settings = get_settings_manager()
        settings.settings.table_rules.dealer_hits_soft_17 = value == "h17"
        settings.save()

    def _on_payout_change(self, value: str) -> None:
        settings = get_settings_manager()
        settings.settings.table_rules.blackjack_payout = 1.5 if value == "3:2" else 1.2
        settings.save()

    def _on_double_change(self, value: str) -> None:
        settings = get_settings_manager()
        settings.settings.table_rules.double_on = value
        settings.save()

    def _on_surrender_change(self, value: str) -> None:
        settings = get_settings_manager()
        settings.settings.table_rules.surrender = value
        settings.save()

    def _on_das_change(self, enabled: bool) -> None:
        settings = get_settings_manager()
        settings.settings.table_rules.double_after_split = enabled
        settings.save()

    def _on_rsa_change(self, enabled: bool) -> None:
        settings = get_settings_manager()
        settings.settings.table_rules.resplit_aces = enabled
        settings.save()

    def _on_penetration_change(self, value: float) -> None:
        settings = get_settings_manager()
        settings.settings.table_rules.penetration = value
        settings.save()

    # Session callbacks
    def _on_win_goal_change(self, value: float) -> None:
        settings = get_settings_manager()
        settings.settings.session_goals.win_goal = int(value)
        settings.save()

    def _on_loss_limit_change(self, value: float) -> None:
        settings = get_settings_manager()
        settings.settings.session_goals.loss_limit = int(value)
        settings.save()

    def _on_num_hands_change(self, value: float) -> None:
        settings = get_settings_manager()
        settings.num_hands = int(value)

    def _on_auto_stop_change(self, enabled: bool) -> None:
        settings = get_settings_manager()
        settings.settings.session_goals.auto_stop = enabled
        settings.save()

    def _go_back(self) -> None:
        play_sound("button_click")
        self.change_scene("title", transition=True)

    def _reset_defaults(self) -> None:
        """Reset all settings to defaults."""
        play_sound("button_click")
        get_settings_manager().reset_to_defaults()
        # Refresh UI
        self._setup_ui()

    def handle_event(self, event: pygame.event.Event) -> bool:
        # Handle tab bar
        if self.tab_bar and self.tab_bar.handle_event(event):
            return True

        # Handle toggles
        for toggle in self.toggles:
            if toggle.handle_event(event):
                return True

        # Handle sliders
        for slider in self.sliders:
            if slider.handle_event(event):
                return True

        # Handle selectors
        for selector in self.selectors:
            if selector.handle_event(event):
                return True

        # Handle buttons
        if self.back_button and self.back_button.handle_event(event):
            return True
        if self.reset_button and self.reset_button.handle_event(event):
            return True

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return True
            elif event.key == pygame.K_LEFT:
                if self._current_tab > 0:
                    self._on_tab_change(self._current_tab - 1)
                    if self.tab_bar:
                        self.tab_bar.active_index = self._current_tab
                return True
            elif event.key == pygame.K_RIGHT:
                if self._current_tab < 2:
                    self._on_tab_change(self._current_tab + 1)
                    if self.tab_bar:
                        self.tab_bar.active_index = self._current_tab
                return True

        return False

    def update(self, dt: float) -> None:
        if self.tab_bar:
            self.tab_bar.update(dt)
        for toggle in self.toggles:
            toggle.update(dt)
        for slider in self.sliders:
            slider.update(dt)
        for selector in self.selectors:
            selector.update(dt)
        if self.back_button:
            self.back_button.update(dt)
        if self.reset_button:
            self.reset_button.update(dt)

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

        # Draw tab bar
        if self.tab_bar:
            self.tab_bar.draw(surface)

        # Draw toggles
        for toggle in self.toggles:
            toggle.draw(surface)

        # Draw sliders
        for slider in self.sliders:
            slider.draw(surface)

        # Draw selectors
        for selector in self.selectors:
            selector.draw(surface)

        # Draw buttons
        if self.back_button:
            self.back_button.draw(surface)
        if self.reset_button:
            self.reset_button.draw(surface)

        # Instructions
        instructions = "←→: Switch Tabs | ESC: Back"
        inst_surface = self._font.render(instructions, True, COLORS.TEXT_MUTED)
        inst_rect = inst_surface.get_rect(
            center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 40)
        )
        surface.blit(inst_surface, inst_rect)

        # Apply CRT
        self.crt_filter.apply(surface)
