"""Mistakes breakdown scene showing common errors."""

from typing import Optional, List, Dict, Any

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.panel import Panel
from pygame_ui.components.heat_map import StrategyHeatMap
from pygame_ui.effects.crt_filter import CRTFilter
from pygame_ui.core.sound_manager import play_sound
from pygame_ui.core.hand_logger import get_hand_logger, MistakeStats
from pygame_ui.core.export import (
    export_mistake_breakdown,
    export_strategy_accuracy,
    get_export_directory,
    generate_export_filename,
)


class MistakesScene(BaseScene):
    """Scene showing mistake breakdown and strategy heat map."""

    def __init__(self):
        super().__init__()

        self.crt_filter = CRTFilter(
            scanline_alpha=25,
            vignette_strength=0.25,
            enabled=True,
        )

        # UI components
        self.panel: Optional[Panel] = None
        self.back_button: Optional[Button] = None
        self.export_button: Optional[Button] = None
        self.heat_map: Optional[StrategyHeatMap] = None
        self.mode_buttons: List[Button] = []

        # Data
        self._mistakes: List[MistakeStats] = []
        self._selected_mistake: Optional[Dict[str, Any]] = None
        self._scroll_offset = 0
        self._max_visible = 8

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._font: Optional[pygame.font.Font] = None
        self._small_font: Optional[pygame.font.Font] = None

    def _init_fonts(self) -> None:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 48)
            self._font = pygame.font.Font(None, 28)
            self._small_font = pygame.font.Font(None, 22)

    def on_enter(self) -> None:
        super().on_enter()
        self._init_fonts()
        self._load_data()
        self._setup_ui()

    def _load_data(self) -> None:
        """Load mistake data from hand logger."""
        logger = get_hand_logger()
        breakdown = logger.get_mistake_breakdown()

        # Sort by count descending
        self._mistakes = sorted(
            breakdown.values(),
            key=lambda m: m.count,
            reverse=True,
        )

    def _setup_ui(self) -> None:
        """Setup UI components."""
        center_x = DIMENSIONS.CENTER_X

        # Main panel (left side - mistakes list)
        self.panel = Panel(
            x=center_x - 200,
            y=DIMENSIONS.CENTER_Y,
            width=350,
            height=420,
        )

        # Heat map (right side)
        self.heat_map = StrategyHeatMap(
            x=center_x + 180,
            y=DIMENSIONS.CENTER_Y - 20,
            width=380,
            height=350,
            on_cell_click=self._on_cell_click,
        )
        self._update_heat_map()

        # Mode buttons for heat map
        modes = [("Hard", "hard"), ("Soft", "soft"), ("Pairs", "pair")]
        button_y = DIMENSIONS.CENTER_Y + 160
        for i, (label, mode) in enumerate(modes):
            btn = Button(
                x=center_x + 100 + i * 90,
                y=button_y,
                text=label,
                font_size=24,
                on_click=lambda m=mode: self._set_heat_map_mode(m),
                bg_color=(60, 80, 60) if mode == "hard" else (50, 50, 60),
                hover_color=(80, 110, 80),
                width=80,
                height=32,
            )
            self.mode_buttons.append(btn)

        # Export button
        self.export_button = Button(
            x=center_x - 100,
            y=DIMENSIONS.SCREEN_HEIGHT - 80,
            text="EXPORT CSV",
            font_size=28,
            on_click=self._export_data,
            bg_color=(60, 80, 100),
            hover_color=(80, 100, 130),
            width=150,
            height=40,
        )

        # Back button
        self.back_button = Button(
            x=center_x + 100,
            y=DIMENSIONS.SCREEN_HEIGHT - 80,
            text="BACK",
            font_size=28,
            on_click=self._go_back,
            bg_color=(100, 60, 60),
            hover_color=(130, 80, 80),
            width=150,
            height=40,
        )

    def _update_heat_map(self) -> None:
        """Update heat map with current accuracy data."""
        if self.heat_map:
            logger = get_hand_logger()
            accuracy_data = logger.get_strategy_accuracy()
            self.heat_map.set_data(accuracy_data)

    def _set_heat_map_mode(self, mode: str) -> None:
        """Set heat map display mode."""
        play_sound("button_click")
        if self.heat_map:
            self.heat_map.set_mode(mode)

        # Update button colors
        for btn in self.mode_buttons:
            if mode.lower() in btn.text.lower():
                btn.bg_color = (60, 80, 60)
            else:
                btn.bg_color = (50, 50, 60)

    def _on_cell_click(self, cell_data: Dict[str, Any]) -> None:
        """Handle heat map cell click."""
        self._selected_mistake = cell_data
        play_sound("button_click")

    def _export_data(self) -> None:
        """Export mistake data to CSV."""
        play_sound("button_click")

        export_dir = get_export_directory()

        # Export mistakes
        mistakes_file = generate_export_filename("mistakes")
        export_mistake_breakdown(f"{export_dir}/{mistakes_file}")

        # Export accuracy
        accuracy_file = generate_export_filename("accuracy")
        export_strategy_accuracy(f"{export_dir}/{accuracy_file}")

        # Show confirmation (would use toast in full implementation)

    def _go_back(self) -> None:
        play_sound("button_click")
        self.change_scene("title", transition=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        # Heat map
        if self.heat_map and self.heat_map.handle_event(event):
            return True

        # Mode buttons
        for btn in self.mode_buttons:
            if btn.handle_event(event):
                return True

        # Export button
        if self.export_button and self.export_button.handle_event(event):
            return True

        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        # Scroll mistakes list
        if event.type == pygame.MOUSEWHEEL:
            panel_rect = pygame.Rect(
                DIMENSIONS.CENTER_X - 200 - 175,
                DIMENSIONS.CENTER_Y - 210,
                350,
                420,
            )
            if panel_rect.collidepoint(pygame.mouse.get_pos()):
                self._scroll_offset -= event.y
                max_scroll = max(0, len(self._mistakes) - self._max_visible)
                self._scroll_offset = max(0, min(self._scroll_offset, max_scroll))
                return True

        # Keyboard
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return True
            elif event.key == pygame.K_UP:
                self._scroll_offset = max(0, self._scroll_offset - 1)
                return True
            elif event.key == pygame.K_DOWN:
                max_scroll = max(0, len(self._mistakes) - self._max_visible)
                self._scroll_offset = min(max_scroll, self._scroll_offset + 1)
                return True

        return False

    def update(self, dt: float) -> None:
        if self.heat_map:
            self.heat_map.update(dt)
        for btn in self.mode_buttons:
            btn.update(dt)
        if self.export_button:
            self.export_button.update(dt)
        if self.back_button:
            self.back_button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self._init_fonts()

        # Background
        surface.fill(COLORS.BACKGROUND)

        # Panel
        if self.panel:
            self.panel.draw(surface)

        # Title
        title = self._title_font.render("MISTAKE ANALYSIS", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 50))
        surface.blit(title, title_rect)

        # Draw mistakes list
        self._draw_mistakes_list(surface)

        # Heat map
        if self.heat_map:
            self.heat_map.draw(surface)

        # Mode buttons
        for btn in self.mode_buttons:
            btn.draw(surface)

        # Selected cell info
        if self._selected_mistake:
            self._draw_selected_info(surface)

        # Export button
        if self.export_button:
            self.export_button.draw(surface)

        # Back button
        if self.back_button:
            self.back_button.draw(surface)

        # Instructions
        inst = "Scroll: ↑↓ | Click heat map cell for details | ESC: Back"
        inst_surf = self._small_font.render(inst, True, COLORS.TEXT_MUTED)
        inst_rect = inst_surf.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 25))
        surface.blit(inst_surf, inst_rect)

        self.crt_filter.apply(surface)

    def _draw_mistakes_list(self, surface: pygame.Surface) -> None:
        """Draw the scrollable mistakes list."""
        list_x = DIMENSIONS.CENTER_X - 200 - 160
        list_y = DIMENSIONS.CENTER_Y - 180
        row_height = 45

        # Header
        header = self._font.render("Common Mistakes", True, COLORS.GOLD)
        surface.blit(header, (list_x, list_y - 30))

        if not self._mistakes:
            no_data = self._font.render("No mistakes recorded", True, COLORS.TEXT_MUTED)
            rect = no_data.get_rect(center=(DIMENSIONS.CENTER_X - 200, DIMENSIONS.CENTER_Y))
            surface.blit(no_data, rect)
            return

        # Visible mistakes
        visible = self._mistakes[self._scroll_offset:self._scroll_offset + self._max_visible]

        for i, mistake in enumerate(visible):
            y = list_y + i * row_height

            # Background
            bg_color = (50, 40, 40) if mistake.is_deviation else (40, 40, 50)
            pygame.draw.rect(surface, bg_color, (list_x, y, 330, row_height - 5), border_radius=4)

            # Situation
            sit_text = self._font.render(mistake.situation, True, COLORS.TEXT_WHITE)
            surface.blit(sit_text, (list_x + 10, y + 5))

            # Action info
            action_text = f"{mistake.wrong_action} → {mistake.correct_action}"
            action_surf = self._small_font.render(action_text, True, COLORS.TEXT_MUTED)
            surface.blit(action_surf, (list_x + 10, y + 25))

            # Count
            count_text = self._font.render(f"x{mistake.count}", True, COLORS.GOLD)
            count_rect = count_text.get_rect(right=list_x + 320, centery=y + row_height // 2)
            surface.blit(count_text, count_rect)

            # Deviation marker
            if mistake.is_deviation:
                dev_text = self._small_font.render("DEV", True, (200, 100, 100))
                surface.blit(dev_text, (list_x + 280, y + 5))

        # Scroll indicator
        if len(self._mistakes) > self._max_visible:
            total = len(self._mistakes)
            visible_ratio = self._max_visible / total
            scroll_ratio = self._scroll_offset / (total - self._max_visible)

            bar_height = 360
            thumb_height = int(bar_height * visible_ratio)
            thumb_y = list_y + int((bar_height - thumb_height) * scroll_ratio)

            # Track
            pygame.draw.rect(
                surface,
                (40, 40, 45),
                (list_x + 335, list_y, 8, bar_height),
                border_radius=4,
            )
            # Thumb
            pygame.draw.rect(
                surface,
                COLORS.TEXT_MUTED,
                (list_x + 335, thumb_y, 8, thumb_height),
                border_radius=4,
            )

    def _draw_selected_info(self, surface: pygame.Surface) -> None:
        """Draw info about the selected heat map cell."""
        if not self._selected_mistake:
            return

        info_x = DIMENSIONS.CENTER_X + 180
        info_y = DIMENSIONS.CENTER_Y + 200

        # Background
        pygame.draw.rect(
            surface,
            (40, 40, 50),
            (info_x - 150, info_y, 300, 60),
            border_radius=4,
        )

        # Stats
        total = self._selected_mistake.get("total", 0)
        correct = self._selected_mistake.get("correct", 0)
        accuracy = self._selected_mistake.get("accuracy", 1.0)

        text1 = f"Attempts: {total} | Correct: {correct}"
        text2 = f"Accuracy: {accuracy:.1%}"

        surf1 = self._font.render(text1, True, COLORS.TEXT_WHITE)
        surf2 = self._font.render(text2, True, COLORS.GOLD)

        surface.blit(surf1, (info_x - 140, info_y + 10))
        surface.blit(surf2, (info_x - 140, info_y + 35))
