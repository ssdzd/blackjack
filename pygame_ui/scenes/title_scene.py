"""Title screen scene with animated elements."""

import math
from typing import Optional

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.effects.crt_filter import CRTFilter


class TitleScene(BaseScene):
    """Title screen with animated title and start prompt.

    Features:
    - Animated pulsing title
    - Floating card decorations
    - "Press SPACE to start" with blink
    - CRT filter overlay
    """

    def __init__(self):
        super().__init__()

        # Animation state
        self._time = 0.0
        self._title_scale = 1.0
        self._prompt_alpha = 255
        self._card_offsets = [0.0, 0.0, 0.0, 0.0]

        # Fonts (initialized lazily)
        self._title_font: Optional[pygame.font.Font] = None
        self._subtitle_font: Optional[pygame.font.Font] = None
        self._prompt_font: Optional[pygame.font.Font] = None
        self._version_font: Optional[pygame.font.Font] = None

        # CRT effect
        self.crt_filter = CRTFilter(
            scanline_alpha=20,
            vignette_strength=0.3,
            enabled=True,
        )

        # Menu buttons
        self.start_button: Optional[Button] = None
        self.drills_button: Optional[Button] = None
        self.performance_button: Optional[Button] = None
        self.statistics_button: Optional[Button] = None
        self.simulation_button: Optional[Button] = None
        self.history_button: Optional[Button] = None
        self.mistakes_button: Optional[Button] = None
        self.settings_button: Optional[Button] = None

    def _init_fonts(self) -> None:
        """Initialize fonts (must be called after pygame.init)."""
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 96)
            self._subtitle_font = pygame.font.Font(None, 36)
            self._prompt_font = pygame.font.Font(None, 32)
            self._version_font = pygame.font.Font(None, 24)

    def _init_button(self) -> None:
        """Initialize menu buttons."""
        if self.start_button is None:
            button_y_start = DIMENSIONS.SCREEN_HEIGHT - 340
            button_spacing = 36

            self.start_button = Button(
                x=DIMENSIONS.CENTER_X,
                y=button_y_start,
                text="PLAY GAME",
                font_size=32,
                on_click=self._start_game,
                bg_color=(60, 100, 60),
                hover_color=(80, 130, 80),
                width=200,
                height=40,
            )

            self.drills_button = Button(
                x=DIMENSIONS.CENTER_X,
                y=button_y_start + button_spacing,
                text="TRAINING DRILLS",
                font_size=26,
                on_click=self._open_drills,
                bg_color=(80, 80, 120),
                hover_color=(100, 100, 150),
                width=200,
                height=32,
            )

            self.performance_button = Button(
                x=DIMENSIONS.CENTER_X,
                y=button_y_start + button_spacing * 2,
                text="PERFORMANCE",
                font_size=26,
                on_click=self._open_performance,
                bg_color=(100, 80, 60),
                hover_color=(130, 100, 80),
                width=200,
                height=32,
            )

            self.statistics_button = Button(
                x=DIMENSIONS.CENTER_X,
                y=button_y_start + button_spacing * 3,
                text="STATISTICS",
                font_size=26,
                on_click=self._open_statistics,
                bg_color=(80, 100, 80),
                hover_color=(100, 130, 100),
                width=200,
                height=32,
            )

            self.simulation_button = Button(
                x=DIMENSIONS.CENTER_X,
                y=button_y_start + button_spacing * 4,
                text="SIMULATION",
                font_size=26,
                on_click=self._open_simulation,
                bg_color=(100, 80, 100),
                hover_color=(130, 100, 130),
                width=200,
                height=32,
            )

            self.history_button = Button(
                x=DIMENSIONS.CENTER_X,
                y=button_y_start + button_spacing * 5,
                text="HAND HISTORY",
                font_size=26,
                on_click=self._open_history,
                bg_color=(80, 90, 80),
                hover_color=(100, 120, 100),
                width=200,
                height=32,
            )

            self.mistakes_button = Button(
                x=DIMENSIONS.CENTER_X,
                y=button_y_start + button_spacing * 6,
                text="MISTAKE ANALYSIS",
                font_size=26,
                on_click=self._open_mistakes,
                bg_color=(100, 70, 70),
                hover_color=(130, 90, 90),
                width=200,
                height=32,
            )

            self.settings_button = Button(
                x=DIMENSIONS.CENTER_X,
                y=button_y_start + button_spacing * 7,
                text="SETTINGS",
                font_size=26,
                on_click=self._open_settings,
                bg_color=(60, 60, 80),
                hover_color=(80, 80, 110),
                width=200,
                height=32,
            )

    def on_enter(self) -> None:
        """Initialize when entering the scene."""
        super().on_enter()
        self._time = 0.0
        self._init_fonts()
        self._init_button()

    def _start_game(self) -> None:
        """Transition to the game scene."""
        self.change_scene("game", transition=True)

    def _open_drills(self) -> None:
        """Open the drill menu scene."""
        self.change_scene("drill_menu", transition=True)

    def _open_performance(self) -> None:
        """Open the performance scene."""
        self.change_scene("performance", transition=True)

    def _open_statistics(self) -> None:
        """Open the statistics calculator scene."""
        self.change_scene("statistics", transition=True)

    def _open_simulation(self) -> None:
        """Open the simulation scene."""
        self.change_scene("simulation", transition=True)

    def _open_history(self) -> None:
        """Open the hand history scene."""
        self.change_scene("history", transition=True)

    def _open_mistakes(self) -> None:
        """Open the mistakes analysis scene."""
        self.change_scene("mistakes", transition=True)

    def _open_settings(self) -> None:
        """Open the settings scene."""
        self.change_scene("settings", transition=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        # Handle buttons
        if self.start_button and self.start_button.handle_event(event):
            return True
        if self.drills_button and self.drills_button.handle_event(event):
            return True
        if self.performance_button and self.performance_button.handle_event(event):
            return True
        if self.statistics_button and self.statistics_button.handle_event(event):
            return True
        if self.simulation_button and self.simulation_button.handle_event(event):
            return True
        if self.history_button and self.history_button.handle_event(event):
            return True
        if self.mistakes_button and self.mistakes_button.handle_event(event):
            return True
        if self.settings_button and self.settings_button.handle_event(event):
            return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._start_game()
                return True
            elif event.key == pygame.K_t:
                self._open_drills()
                return True
            elif event.key == pygame.K_p:
                self._open_performance()
                return True
            elif event.key == pygame.K_s:
                self._open_statistics()
                return True
            elif event.key == pygame.K_m:
                self._open_simulation()
                return True
            elif event.key == pygame.K_h:
                self._open_history()
                return True
            elif event.key == pygame.K_a:
                self._open_mistakes()
                return True
            elif event.key == pygame.K_c:
                self.crt_filter.toggle()
                return True

        return False

    def update(self, dt: float) -> None:
        """Update animations."""
        self._time += dt

        # Title pulse animation
        self._title_scale = 1.0 + 0.03 * math.sin(self._time * 2.0)

        # Prompt blink animation
        blink_cycle = (self._time % 1.5) / 1.5
        if blink_cycle < 0.7:
            self._prompt_alpha = 255
        else:
            self._prompt_alpha = int(255 * (1.0 - (blink_cycle - 0.7) / 0.3))

        # Floating card animations
        for i in range(4):
            phase = i * (math.pi / 2)
            self._card_offsets[i] = 10 * math.sin(self._time * 1.5 + phase)

        # Update buttons
        if self.start_button:
            self.start_button.update(dt)
        if self.drills_button:
            self.drills_button.update(dt)
        if self.performance_button:
            self.performance_button.update(dt)
        if self.statistics_button:
            self.statistics_button.update(dt)
        if self.simulation_button:
            self.simulation_button.update(dt)
        if self.history_button:
            self.history_button.update(dt)
        if self.mistakes_button:
            self.mistakes_button.update(dt)
        if self.settings_button:
            self.settings_button.update(dt)

    def _draw_decorative_cards(self, surface: pygame.Surface) -> None:
        """Draw floating decorative cards in corners."""
        card_width = 60
        card_height = 84
        margin = 80

        positions = [
            (margin, margin + self._card_offsets[0]),  # Top left
            (DIMENSIONS.SCREEN_WIDTH - margin, margin + self._card_offsets[1]),  # Top right
            (margin, DIMENSIONS.SCREEN_HEIGHT - margin + self._card_offsets[2]),  # Bottom left
            (DIMENSIONS.SCREEN_WIDTH - margin, DIMENSIONS.SCREEN_HEIGHT - margin + self._card_offsets[3]),  # Bottom right
        ]

        suits = ["♠", "♥", "♣", "♦"]
        colors = [COLORS.CARD_BLACK, COLORS.CARD_RED, COLORS.CARD_BLACK, COLORS.CARD_RED]

        for i, (x, y) in enumerate(positions):
            # Card background
            card_rect = pygame.Rect(0, 0, card_width, card_height)
            card_rect.center = (int(x), int(y))

            # Slight rotation based on position
            angle = 15 if i % 2 == 0 else -15

            # Create card surface
            card_surface = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
            pygame.draw.rect(card_surface, COLORS.CARD_WHITE, (0, 0, card_width, card_height), border_radius=6)
            pygame.draw.rect(card_surface, COLORS.CARD_BLACK, (0, 0, card_width, card_height), width=2, border_radius=6)

            # Draw suit
            suit_font = pygame.font.Font(None, 48)
            suit_text = suit_font.render(suits[i], True, colors[i])
            suit_rect = suit_text.get_rect(center=(card_width // 2, card_height // 2))
            card_surface.blit(suit_text, suit_rect)

            # Rotate and blit
            rotated = pygame.transform.rotate(card_surface, angle)
            rotated_rect = rotated.get_rect(center=(int(x), int(y)))
            surface.blit(rotated, rotated_rect)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the title screen."""
        self._init_fonts()  # Ensure fonts are ready

        # Background gradient (dark to darker)
        surface.fill(COLORS.BACKGROUND)

        # Draw felt-like pattern in center
        center_rect = pygame.Rect(
            DIMENSIONS.SCREEN_WIDTH // 4,
            DIMENSIONS.SCREEN_HEIGHT // 4,
            DIMENSIONS.SCREEN_WIDTH // 2,
            DIMENSIONS.SCREEN_HEIGHT // 2,
        )
        pygame.draw.rect(surface, COLORS.FELT_DARK, center_rect, border_radius=20)
        pygame.draw.rect(surface, COLORS.FELT_GREEN, center_rect.inflate(-8, -8), border_radius=16)

        # Draw decorative cards
        self._draw_decorative_cards(surface)

        # Draw title with scale animation
        title_text = "BLACKJACK"
        title_surface = self._title_font.render(title_text, True, COLORS.GOLD)

        # Apply scale
        if self._title_scale != 1.0:
            new_width = int(title_surface.get_width() * self._title_scale)
            new_height = int(title_surface.get_height() * self._title_scale)
            title_surface = pygame.transform.scale(title_surface, (new_width, new_height))

        title_rect = title_surface.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT // 3))
        surface.blit(title_surface, title_rect)

        # Draw subtitle
        subtitle_text = "CARD COUNTING TRAINER"
        subtitle_surface = self._subtitle_font.render(subtitle_text, True, COLORS.TEXT_WHITE)
        subtitle_rect = subtitle_surface.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT // 3 + 60))
        surface.blit(subtitle_surface, subtitle_rect)

        # Draw "Press SPACE to start" with blink (above buttons)
        prompt_text = "Press SPACE to start"
        prompt_surface = self._prompt_font.render(prompt_text, True, COLORS.TEXT_WHITE)
        prompt_surface.set_alpha(self._prompt_alpha)
        prompt_rect = prompt_surface.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 375))
        surface.blit(prompt_surface, prompt_rect)

        # Draw buttons
        if self.start_button:
            self.start_button.draw(surface)
        if self.drills_button:
            self.drills_button.draw(surface)
        if self.performance_button:
            self.performance_button.draw(surface)
        if self.statistics_button:
            self.statistics_button.draw(surface)
        if self.simulation_button:
            self.simulation_button.draw(surface)
        if self.history_button:
            self.history_button.draw(surface)
        if self.mistakes_button:
            self.mistakes_button.draw(surface)
        if self.settings_button:
            self.settings_button.draw(surface)

        # Draw version/credits
        version_text = "v0.1 - Balatro Style UI"
        version_surface = self._version_font.render(version_text, True, COLORS.TEXT_MUTED)
        version_rect = version_surface.get_rect(bottomright=(DIMENSIONS.SCREEN_WIDTH - 20, DIMENSIONS.SCREEN_HEIGHT - 20))
        surface.blit(version_surface, version_rect)

        # Draw controls hint
        controls_text = "T: Training | P: Perf | S: Stats | M: Sim | H: History | A: Mistakes"
        controls_surface = self._version_font.render(controls_text, True, COLORS.TEXT_MUTED)
        controls_rect = controls_surface.get_rect(bottomleft=(20, DIMENSIONS.SCREEN_HEIGHT - 20))
        surface.blit(controls_surface, controls_rect)

        # Apply CRT filter
        self.crt_filter.apply(surface)
