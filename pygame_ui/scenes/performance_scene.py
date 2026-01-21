"""Performance tracking scene displaying player statistics."""

from typing import Optional, List, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.panel import Panel
from pygame_ui.effects.crt_filter import CRTFilter
from pygame_ui.core.stats_manager import get_stats_manager


class StatCard(Panel):
    """A card displaying a single statistic."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        title: str,
        value: str,
        subtitle: str = "",
        value_color: Tuple[int, int, int] = COLORS.TEXT_WHITE,
    ):
        super().__init__(
            x, y, width, height,
            bg_color=COLORS.PANEL_BG,
            bg_alpha=220,
            border_color=COLORS.PANEL_BORDER,
        )
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.value_color = value_color

        self._title_font: Optional[pygame.font.Font] = None
        self._value_font: Optional[pygame.font.Font] = None
        self._subtitle_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 24)
        return self._title_font

    @property
    def value_font(self) -> pygame.font.Font:
        if self._value_font is None:
            self._value_font = pygame.font.Font(None, 42)
        return self._value_font

    @property
    def subtitle_font(self) -> pygame.font.Font:
        if self._subtitle_font is None:
            self._subtitle_font = pygame.font.Font(None, 20)
        return self._subtitle_font

    def set_value(self, value: str, subtitle: str = "") -> None:
        """Update the displayed value."""
        self.value = value
        self.subtitle = subtitle
        self._needs_redraw = True

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the stat card."""
        super().draw(surface)

        # Title
        title_text = self.title_font.render(self.title, True, COLORS.TEXT_MUTED)
        title_rect = title_text.get_rect(
            centerx=int(self.center_x),
            top=int(self.y) + 12,
        )
        surface.blit(title_text, title_rect)

        # Value
        value_text = self.value_font.render(self.value, True, self.value_color)
        value_rect = value_text.get_rect(
            centerx=int(self.center_x),
            centery=int(self.center_y) + 5,
        )
        surface.blit(value_text, value_rect)

        # Subtitle
        if self.subtitle:
            sub_text = self.subtitle_font.render(self.subtitle, True, COLORS.TEXT_MUTED)
            sub_rect = sub_text.get_rect(
                centerx=int(self.center_x),
                bottom=int(self.y + self.height) - 8,
            )
            surface.blit(sub_text, sub_rect)


class PerformanceScene(BaseScene):
    """Scene displaying player performance statistics.

    Shows:
    - Game stats (hands played, win rate, net result, blackjacks)
    - Drill accuracy breakdown
    - Session info
    """

    def __init__(self):
        super().__init__()

        # UI Components
        self.stat_cards: List[StatCard] = []
        self.back_button: Optional[Button] = None
        self.reset_button: Optional[Button] = None

        # Visual effects
        self.crt_filter = CRTFilter(scanline_alpha=20, vignette_strength=0.2)

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._section_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 48)
        return self._title_font

    @property
    def section_font(self) -> pygame.font.Font:
        if self._section_font is None:
            self._section_font = pygame.font.Font(None, 32)
        return self._section_font

    def on_enter(self) -> None:
        """Initialize the scene."""
        super().on_enter()
        self._setup_ui()
        self._update_stats()

    def _setup_ui(self) -> None:
        """Set up UI components."""
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

        # Reset button
        self.reset_button = Button(
            x=DIMENSIONS.SCREEN_WIDTH - 100,
            y=40,
            text="RESET",
            font_size=24,
            on_click=self._on_reset,
            bg_color=(120, 60, 60),
            hover_color=(150, 80, 80),
            width=100,
            height=40,
        )

        # Create stat cards
        self._create_stat_cards()

    def _create_stat_cards(self) -> None:
        """Create the stat display cards."""
        self.stat_cards = []

        card_width = 180
        card_height = 100
        spacing_x = 200
        spacing_y = 120

        # Game stats row
        game_y = 180
        game_start_x = DIMENSIONS.CENTER_X - spacing_x * 1.5

        cards_config = [
            # Row 1: Game stats
            (game_start_x, game_y, "HANDS PLAYED", "0"),
            (game_start_x + spacing_x, game_y, "WIN RATE", "0%"),
            (game_start_x + spacing_x * 2, game_y, "NET RESULT", "$0"),
            (game_start_x + spacing_x * 3, game_y, "BLACKJACKS", "0"),

            # Row 2: Drill stats
            (game_start_x, game_y + spacing_y, "COUNTING", "0%"),
            (game_start_x + spacing_x, game_y + spacing_y, "STRATEGY", "0%"),
            (game_start_x + spacing_x * 2, game_y + spacing_y, "SPEED BEST", "0"),
            (game_start_x + spacing_x * 3, game_y + spacing_y, "SESSIONS", "0"),

            # Row 3: Additional game stats
            (game_start_x + spacing_x * 0.5, game_y + spacing_y * 2, "BUSTS", "0"),
            (game_start_x + spacing_x * 1.5, game_y + spacing_y * 2, "SPLITS", "0"),
            (game_start_x + spacing_x * 2.5, game_y + spacing_y * 2, "SURRENDERS", "0"),
        ]

        for x, y, title, value in cards_config:
            card = StatCard(x, y, card_width, card_height, title, value)
            self.stat_cards.append(card)

    def _update_stats(self) -> None:
        """Update stat card values from stats manager."""
        stats = get_stats_manager().stats
        game = stats.game
        drills = stats.drills

        # Update each card
        # Row 1
        self.stat_cards[0].set_value(
            str(game.hands_played),
            f"W:{game.hands_won} L:{game.hands_lost}"
        )

        win_rate = get_stats_manager().win_rate
        self.stat_cards[1].set_value(
            f"{win_rate:.1f}%",
            f"{game.hands_won}/{game.hands_won + game.hands_lost}"
        )
        self.stat_cards[1].value_color = (
            COLORS.COUNT_POSITIVE if win_rate >= 50 else
            COLORS.COUNT_NEGATIVE if win_rate < 45 else
            COLORS.TEXT_WHITE
        )

        net_str = f"${game.net_result:+,.0f}"
        self.stat_cards[2].set_value(net_str)
        self.stat_cards[2].value_color = (
            COLORS.COUNT_POSITIVE if game.net_result > 0 else
            COLORS.COUNT_NEGATIVE if game.net_result < 0 else
            COLORS.TEXT_WHITE
        )

        self.stat_cards[3].set_value(str(game.blackjacks))

        # Row 2: Drill stats
        counting_acc = get_stats_manager().counting_accuracy
        self.stat_cards[4].set_value(
            f"{counting_acc:.0f}%",
            f"{drills.counting_correct}/{drills.counting_attempts}"
        )
        self.stat_cards[4].value_color = (
            COLORS.COUNT_POSITIVE if counting_acc >= 80 else
            COLORS.COUNT_NEGATIVE if counting_acc < 60 else
            COLORS.TEXT_WHITE
        )

        strategy_acc = get_stats_manager().strategy_accuracy
        self.stat_cards[5].set_value(
            f"{strategy_acc:.0f}%",
            f"{drills.strategy_correct}/{drills.strategy_attempts}"
        )
        self.stat_cards[5].value_color = (
            COLORS.COUNT_POSITIVE if strategy_acc >= 90 else
            COLORS.COUNT_NEGATIVE if strategy_acc < 70 else
            COLORS.TEXT_WHITE
        )

        self.stat_cards[6].set_value(
            str(drills.speed_high_score),
            f"Best: {drills.speed_best_time:.1f}s" if drills.speed_best_time > 0 else ""
        )

        self.stat_cards[7].set_value(
            str(stats.total_sessions),
            f"{stats.total_play_time_minutes:.0f} min total"
        )

        # Row 3
        self.stat_cards[8].set_value(str(game.busts))
        self.stat_cards[9].set_value(str(game.splits_played))
        self.stat_cards[10].set_value(str(game.surrenders))

    def _on_back(self) -> None:
        """Handle back button click."""
        self.change_scene("title", transition=True)

    def _on_reset(self) -> None:
        """Handle reset button click."""
        get_stats_manager().reset_stats()
        self._update_stats()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        # Reset button
        if self.reset_button and self.reset_button.handle_event(event):
            return True

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_back()
                return True

        return False

    def update(self, dt: float) -> None:
        """Update scene."""
        if self.back_button:
            self.back_button.update(dt)
        if self.reset_button:
            self.reset_button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.BACKGROUND)

        # Title
        title = self.title_font.render("PERFORMANCE", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 60))
        surface.blit(title, title_rect)

        # Section labels
        sections = [
            ("GAME STATISTICS", 130),
            ("TRAINING DRILLS", 250),
            ("ADDITIONAL STATS", 370),
        ]

        for label, y in sections:
            text = self.section_font.render(label, True, COLORS.TEXT_MUTED)
            text_rect = text.get_rect(left=60, centery=y)
            surface.blit(text, text_rect)

        # Stat cards
        for card in self.stat_cards:
            card.draw(surface)

        # Back button
        if self.back_button:
            self.back_button.draw(surface)

        # Reset button
        if self.reset_button:
            self.reset_button.draw(surface)

        # Last session info
        stats = get_stats_manager().stats
        if stats.last_session:
            last_text = f"Last session: {stats.last_session[:10]}"
            font = pygame.font.Font(None, 22)
            text = font.render(last_text, True, COLORS.TEXT_MUTED)
            text_rect = text.get_rect(
                center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 60)
            )
            surface.blit(text, text_rect)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "ESC: Back | RESET: Clear all stats"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(
            center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30)
        )
        surface.blit(text, text_rect)

        # Apply CRT filter
        self.crt_filter.apply(surface)
