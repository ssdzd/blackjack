"""Strategy chart scene displaying basic strategy tables."""

from typing import Optional, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.strategy_chart import (
    StrategyChartGrid,
    StrategyChartTabs,
    StrategyChartLegend,
)
from pygame_ui.components.button import Button
from pygame_ui.effects.crt_filter import CRTFilter

from core.strategy.basic import BasicStrategy


class StrategyChartScene(BaseScene):
    """Scene displaying the basic strategy charts.

    Features:
    - Three tabs: Hard Totals, Soft Totals, Pairs
    - Color-coded cells for each action
    - Highlight for current hand (when opened from game)
    - ESC to close
    """

    def __init__(self):
        super().__init__()

        # Strategy data
        self.strategy = BasicStrategy()

        # Chart components
        self.chart_grid: Optional[StrategyChartGrid] = None
        self.tabs: Optional[StrategyChartTabs] = None
        self.legend: Optional[StrategyChartLegend] = None
        self.back_button: Optional[Button] = None

        # Highlight state (passed from game scene)
        self.highlight_player_value: Optional[int] = None
        self.highlight_dealer_upcard: Optional[int] = None
        self.highlight_is_soft: bool = False
        self.highlight_is_pair: bool = False

        # Visual effects
        self.crt_filter = CRTFilter(scanline_alpha=20, vignette_strength=0.2)

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 48)
        return self._title_font

    def on_enter(self) -> None:
        """Initialize the scene."""
        super().on_enter()

        # Create chart grid
        self.chart_grid = StrategyChartGrid(
            x=DIMENSIONS.CENTER_X,
            y=DIMENSIONS.CENTER_Y + 20,
            cell_size=38,
        )

        # Set initial table (hard)
        self.chart_grid.set_hard_table(self.strategy.hard_table)

        # Apply highlight if set
        self._apply_highlight()

        # Create tabs
        self.tabs = StrategyChartTabs(
            x=DIMENSIONS.CENTER_X,
            y=100,
            width=400,
            height=40,
        )

        # Create legend
        self.legend = StrategyChartLegend(
            x=DIMENSIONS.CENTER_X,
            y=DIMENSIONS.SCREEN_HEIGHT - 60,
        )

        # Create back button
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

    def set_highlight(
        self,
        player_value: int,
        dealer_upcard: int,
        is_soft: bool = False,
        is_pair: bool = False,
    ) -> None:
        """Set the hand to highlight.

        Args:
            player_value: Player hand value or pair rank
            dealer_upcard: Dealer upcard (2-11)
            is_soft: Whether hand is soft
            is_pair: Whether hand is a pair
        """
        self.highlight_player_value = player_value
        self.highlight_dealer_upcard = dealer_upcard
        self.highlight_is_soft = is_soft
        self.highlight_is_pair = is_pair

        # If scene is already active, apply highlight
        if self.chart_grid:
            self._apply_highlight()

    def _apply_highlight(self) -> None:
        """Apply the highlight to the appropriate tab and cell."""
        if self.highlight_player_value is None or self.highlight_dealer_upcard is None:
            return

        if not self.chart_grid or not self.tabs:
            return

        # Switch to appropriate tab
        if self.highlight_is_pair:
            self.tabs.selected_tab = 2
            self.chart_grid.set_pair_table(self.strategy.pair_table)
        elif self.highlight_is_soft:
            self.tabs.selected_tab = 1
            self.chart_grid.set_soft_table(self.strategy.soft_table)
        else:
            self.tabs.selected_tab = 0
            self.chart_grid.set_hard_table(self.strategy.hard_table)

        # Set highlight
        self.chart_grid.set_highlight(
            self.highlight_player_value,
            self.highlight_dealer_upcard,
            self.highlight_is_soft,
            self.highlight_is_pair,
        )

    def _on_back(self) -> None:
        """Handle back button click."""
        self.pop_scene()

    def _switch_tab(self, tab_index: int) -> None:
        """Switch to a different chart tab."""
        if not self.chart_grid:
            return

        # Clear highlight when manually switching tabs
        self.chart_grid.clear_highlight()

        if tab_index == 0:
            self.chart_grid.set_hard_table(self.strategy.hard_table)
        elif tab_index == 1:
            self.chart_grid.set_soft_table(self.strategy.soft_table)
        elif tab_index == 2:
            self.chart_grid.set_pair_table(self.strategy.pair_table)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        # Tab switching
        if self.tabs:
            old_tab = self.tabs.selected_tab
            if self.tabs.handle_event(event):
                self._switch_tab(self.tabs.selected_tab)
                return True

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_back()
                return True
            elif event.key == pygame.K_1:
                if self.tabs:
                    self.tabs.selected_tab = 0
                    self._switch_tab(0)
                return True
            elif event.key == pygame.K_2:
                if self.tabs:
                    self.tabs.selected_tab = 1
                    self._switch_tab(1)
                return True
            elif event.key == pygame.K_3:
                if self.tabs:
                    self.tabs.selected_tab = 2
                    self._switch_tab(2)
                return True

        return False

    def update(self, dt: float) -> None:
        """Update scene."""
        if self.chart_grid:
            self.chart_grid.update(dt)
        if self.back_button:
            self.back_button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.BACKGROUND)

        # Title
        title = self.title_font.render("BASIC STRATEGY CHART", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 50))
        surface.blit(title, title_rect)

        # Tabs
        if self.tabs:
            self.tabs.draw(surface)

        # Chart
        if self.chart_grid:
            self.chart_grid.draw(surface)

        # Legend
        if self.legend:
            self.legend.draw(surface)

        # Back button
        if self.back_button:
            self.back_button.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "1-3: Switch tabs | ESC: Back"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 25))
        surface.blit(text, text_rect)

        # Apply CRT filter
        self.crt_filter.apply(surface)
