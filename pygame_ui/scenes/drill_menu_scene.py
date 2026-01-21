"""Drill menu scene for selecting training exercises."""

from typing import Optional, List

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.panel import Panel
from pygame_ui.effects.crt_filter import CRTFilter


class DrillMenuScene(BaseScene):
    """Menu for selecting different training drills.

    Options:
    - Counting Drill: Practice card counting
    - Strategy Drill: Practice basic strategy decisions
    - Speed Challenge: Timed counting test
    """

    def __init__(self):
        super().__init__()

        # UI Components
        self.buttons: List[Button] = []
        self.back_button: Optional[Button] = None

        # Visual effects
        self.crt_filter = CRTFilter(scanline_alpha=20, vignette_strength=0.2)

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._desc_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 56)
        return self._title_font

    @property
    def desc_font(self) -> pygame.font.Font:
        if self._desc_font is None:
            self._desc_font = pygame.font.Font(None, 24)
        return self._desc_font

    def on_enter(self) -> None:
        """Initialize the scene."""
        super().on_enter()

        button_y_start = 200
        button_spacing = 100

        # Counting Drill button
        counting_btn = Button(
            x=DIMENSIONS.CENTER_X,
            y=button_y_start,
            text="COUNTING DRILL",
            font_size=32,
            on_click=lambda: self.change_scene("counting_drill", transition=True),
            bg_color=(60, 100, 60),
            hover_color=(80, 130, 80),
            width=300,
            height=60,
        )

        # Strategy Drill button
        strategy_btn = Button(
            x=DIMENSIONS.CENTER_X,
            y=button_y_start + button_spacing,
            text="STRATEGY DRILL",
            font_size=32,
            on_click=lambda: self.change_scene("strategy_drill", transition=True),
            bg_color=(60, 80, 120),
            hover_color=(80, 100, 150),
            width=300,
            height=60,
        )

        # Speed Challenge button
        speed_btn = Button(
            x=DIMENSIONS.CENTER_X,
            y=button_y_start + button_spacing * 2,
            text="SPEED CHALLENGE",
            font_size=32,
            on_click=lambda: self.change_scene("speed_drill", transition=True),
            bg_color=(120, 80, 60),
            hover_color=(150, 100, 80),
            width=300,
            height=60,
        )

        self.buttons = [counting_btn, strategy_btn, speed_btn]

        # Back button
        self.back_button = Button(
            x=80,
            y=40,
            text="BACK",
            font_size=24,
            on_click=self._on_back,
            bg_color=COLORS.BUTTON_DEFAULT,
            hover_color=COLORS.BUTTON_HOVER,
            width=100,
            height=40,
        )

    def _on_back(self) -> None:
        """Handle back button click."""
        self.change_scene("title", transition=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        # Menu buttons
        for button in self.buttons:
            if button.handle_event(event):
                return True

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_back()
                return True
            elif event.key == pygame.K_1:
                self.change_scene("counting_drill", transition=True)
                return True
            elif event.key == pygame.K_2:
                self.change_scene("strategy_drill", transition=True)
                return True
            elif event.key == pygame.K_3:
                self.change_scene("speed_drill", transition=True)
                return True

        return False

    def update(self, dt: float) -> None:
        """Update scene."""
        for button in self.buttons:
            button.update(dt)
        if self.back_button:
            self.back_button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.BACKGROUND)

        # Title
        title = self.title_font.render("TRAINING DRILLS", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 80))
        surface.blit(title, title_rect)

        # Drill descriptions
        descriptions = [
            ("Practice counting cards as they flash on screen", 260),
            ("Test your knowledge of basic strategy", 360),
            ("Race against the clock for high scores", 460),
        ]

        for desc_text, y_pos in descriptions:
            desc = self.desc_font.render(desc_text, True, COLORS.TEXT_MUTED)
            desc_rect = desc.get_rect(center=(DIMENSIONS.CENTER_X, y_pos))
            surface.blit(desc, desc_rect)

        # Buttons
        for button in self.buttons:
            button.draw(surface)

        # Back button
        if self.back_button:
            self.back_button.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "1-3: Quick select | ESC: Back"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

        # Apply CRT filter
        self.crt_filter.apply(surface)
