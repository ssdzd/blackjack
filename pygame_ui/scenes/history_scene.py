"""Hand history scene for viewing past hands."""

from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.panel import Panel
from pygame_ui.effects.crt_filter import CRTFilter
from pygame_ui.core.sound_manager import play_sound
from pygame_ui.core.hand_logger import (
    get_hand_logger,
    HandRecord,
    HandOutcome,
)
from pygame_ui.core.export import (
    export_hand_history,
    export_decisions,
    get_export_directory,
    generate_export_filename,
)


class FilterMode(Enum):
    ALL = "all"
    WINS = "wins"
    LOSSES = "losses"
    MISTAKES = "mistakes"
    TODAY = "today"


class HistoryScene(BaseScene):
    """Scene for viewing hand history."""

    def __init__(self):
        super().__init__()

        self.crt_filter = CRTFilter(
            scanline_alpha=25,
            vignette_strength=0.25,
            enabled=True,
        )

        # UI components
        self.panel: Optional[Panel] = None
        self.detail_panel: Optional[Panel] = None
        self.back_button: Optional[Button] = None
        self.export_button: Optional[Button] = None
        self.filter_buttons: List[Button] = []
        self.nav_buttons: List[Button] = []

        # Data
        self._all_hands: List[HandRecord] = []
        self._filtered_hands: List[HandRecord] = []
        self._selected_hand: Optional[HandRecord] = None
        self._filter_mode = FilterMode.ALL
        self._scroll_offset = 0
        self._max_visible = 10

        # Pagination
        self._page = 0
        self._hands_per_page = 10

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._font: Optional[pygame.font.Font] = None
        self._small_font: Optional[pygame.font.Font] = None

    def _init_fonts(self) -> None:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 48)
            self._font = pygame.font.Font(None, 24)
            self._small_font = pygame.font.Font(None, 20)

    def on_enter(self) -> None:
        super().on_enter()
        self._init_fonts()
        self._load_data()
        self._setup_ui()

    def _load_data(self) -> None:
        """Load hand history."""
        logger = get_hand_logger()
        self._all_hands = list(reversed(logger.history))  # Most recent first
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply current filter to hands."""
        if self._filter_mode == FilterMode.ALL:
            self._filtered_hands = self._all_hands
        elif self._filter_mode == FilterMode.WINS:
            self._filtered_hands = [
                h for h in self._all_hands
                if h.outcome in ("win", "blackjack")
            ]
        elif self._filter_mode == FilterMode.LOSSES:
            self._filtered_hands = [
                h for h in self._all_hands
                if h.outcome in ("lose", "bust")
            ]
        elif self._filter_mode == FilterMode.MISTAKES:
            self._filtered_hands = [
                h for h in self._all_hands
                if len(h.mistakes) > 0
            ]
        elif self._filter_mode == FilterMode.TODAY:
            today = datetime.now().date()
            self._filtered_hands = [
                h for h in self._all_hands
                if self._get_hand_date(h) == today
            ]

        self._page = 0
        self._selected_hand = None

    def _get_hand_date(self, hand: HandRecord) -> Optional[datetime]:
        """Get date from hand timestamp."""
        try:
            return datetime.fromisoformat(hand.timestamp).date()
        except ValueError:
            return None

    def _setup_ui(self) -> None:
        """Setup UI components."""
        center_x = DIMENSIONS.CENTER_X

        # Main panel (left side - hand list)
        self.panel = Panel(
            x=center_x - 180,
            y=DIMENSIONS.CENTER_Y + 20,
            width=320,
            height=380,
        )

        # Detail panel (right side)
        self.detail_panel = Panel(
            x=center_x + 180,
            y=DIMENSIONS.CENTER_Y + 20,
            width=320,
            height=380,
        )

        # Filter buttons
        filters = [
            ("All", FilterMode.ALL),
            ("Wins", FilterMode.WINS),
            ("Losses", FilterMode.LOSSES),
            ("Mistakes", FilterMode.MISTAKES),
            ("Today", FilterMode.TODAY),
        ]
        filter_y = 90
        for i, (label, mode) in enumerate(filters):
            btn = Button(
                x=center_x - 220 + i * 90,
                y=filter_y,
                text=label,
                font_size=22,
                on_click=lambda m=mode: self._set_filter(m),
                bg_color=(60, 80, 60) if mode == self._filter_mode else (50, 50, 60),
                hover_color=(80, 110, 80),
                width=80,
                height=30,
            )
            self.filter_buttons.append(btn)

        # Navigation buttons
        self.nav_buttons = [
            Button(
                x=center_x - 260,
                y=DIMENSIONS.SCREEN_HEIGHT - 140,
                text="◀",
                font_size=28,
                on_click=self._prev_page,
                bg_color=(50, 50, 60),
                hover_color=(70, 70, 80),
                width=40,
                height=30,
            ),
            Button(
                x=center_x - 100,
                y=DIMENSIONS.SCREEN_HEIGHT - 140,
                text="▶",
                font_size=28,
                on_click=self._next_page,
                bg_color=(50, 50, 60),
                hover_color=(70, 70, 80),
                width=40,
                height=30,
            ),
        ]

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

    def _set_filter(self, mode: FilterMode) -> None:
        """Set filter mode."""
        play_sound("button_click")
        self._filter_mode = mode
        self._apply_filter()

        # Update button colors
        for i, btn in enumerate(self.filter_buttons):
            modes = [FilterMode.ALL, FilterMode.WINS, FilterMode.LOSSES, FilterMode.MISTAKES, FilterMode.TODAY]
            if i < len(modes) and modes[i] == mode:
                btn.bg_color = (60, 80, 60)
            else:
                btn.bg_color = (50, 50, 60)

    def _prev_page(self) -> None:
        """Go to previous page."""
        if self._page > 0:
            play_sound("button_click")
            self._page -= 1

    def _next_page(self) -> None:
        """Go to next page."""
        max_page = (len(self._filtered_hands) - 1) // self._hands_per_page
        if self._page < max_page:
            play_sound("button_click")
            self._page += 1

    def _export_data(self) -> None:
        """Export hand history to CSV."""
        play_sound("button_click")

        export_dir = get_export_directory()

        # Export hands
        hands_file = generate_export_filename("hands")
        export_hand_history(f"{export_dir}/{hands_file}", self._filtered_hands)

        # Export decisions
        decisions_file = generate_export_filename("decisions")
        export_decisions(f"{export_dir}/{decisions_file}", self._filtered_hands)

    def _go_back(self) -> None:
        play_sound("button_click")
        self.change_scene("title", transition=True)

    def _select_hand(self, hand: HandRecord) -> None:
        """Select a hand to view details."""
        play_sound("button_click")
        self._selected_hand = hand

    def handle_event(self, event: pygame.event.Event) -> bool:
        # Filter buttons
        for btn in self.filter_buttons:
            if btn.handle_event(event):
                return True

        # Nav buttons
        for btn in self.nav_buttons:
            if btn.handle_event(event):
                return True

        # Export button
        if self.export_button and self.export_button.handle_event(event):
            return True

        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        # Click on hand row
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check if clicking in hand list area
            list_x = DIMENSIONS.CENTER_X - 180 - 150
            list_y = DIMENSIONS.CENTER_Y - 150
            row_height = 35

            start_idx = self._page * self._hands_per_page
            visible = self._filtered_hands[start_idx:start_idx + self._hands_per_page]

            for i, hand in enumerate(visible):
                row_rect = pygame.Rect(list_x, list_y + i * row_height, 300, row_height - 2)
                if row_rect.collidepoint(event.pos):
                    self._select_hand(hand)
                    return True

        # Keyboard
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return True
            elif event.key == pygame.K_LEFT:
                self._prev_page()
                return True
            elif event.key == pygame.K_RIGHT:
                self._next_page()
                return True

        return False

    def update(self, dt: float) -> None:
        for btn in self.filter_buttons:
            btn.update(dt)
        for btn in self.nav_buttons:
            btn.update(dt)
        if self.export_button:
            self.export_button.update(dt)
        if self.back_button:
            self.back_button.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        self._init_fonts()

        # Background
        surface.fill(COLORS.BACKGROUND)

        # Panels
        if self.panel:
            self.panel.draw(surface)
        if self.detail_panel:
            self.detail_panel.draw(surface)

        # Title
        title = self._title_font.render("HAND HISTORY", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 45))
        surface.blit(title, title_rect)

        # Filter buttons
        for btn in self.filter_buttons:
            btn.draw(surface)

        # Draw hand list
        self._draw_hand_list(surface)

        # Draw details
        self._draw_hand_details(surface)

        # Nav buttons
        for btn in self.nav_buttons:
            btn.draw(surface)

        # Page indicator
        total_pages = max(1, (len(self._filtered_hands) + self._hands_per_page - 1) // self._hands_per_page)
        page_text = f"Page {self._page + 1} / {total_pages}"
        page_surf = self._font.render(page_text, True, COLORS.TEXT_MUTED)
        page_rect = page_surf.get_rect(center=(DIMENSIONS.CENTER_X - 180, DIMENSIONS.SCREEN_HEIGHT - 134))
        surface.blit(page_surf, page_rect)

        # Export button
        if self.export_button:
            self.export_button.draw(surface)

        # Back button
        if self.back_button:
            self.back_button.draw(surface)

        # Instructions
        inst = "Click row to view details | ←→ Navigate | ESC: Back"
        inst_surf = self._small_font.render(inst, True, COLORS.TEXT_MUTED)
        inst_rect = inst_surf.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 25))
        surface.blit(inst_surf, inst_rect)

        self.crt_filter.apply(surface)

    def _draw_hand_list(self, surface: pygame.Surface) -> None:
        """Draw the hand list."""
        list_x = DIMENSIONS.CENTER_X - 180 - 150
        list_y = DIMENSIONS.CENTER_Y - 150
        row_height = 35

        # Header
        headers = ["Time", "Cards", "Outcome", "P/L"]
        header_widths = [70, 100, 70, 50]
        hx = list_x
        for header, width in zip(headers, header_widths):
            text = self._font.render(header, True, COLORS.GOLD)
            surface.blit(text, (hx, list_y - 25))
            hx += width

        if not self._filtered_hands:
            no_data = self._font.render("No hands recorded", True, COLORS.TEXT_MUTED)
            rect = no_data.get_rect(center=(DIMENSIONS.CENTER_X - 180, DIMENSIONS.CENTER_Y))
            surface.blit(no_data, rect)
            return

        # Visible hands
        start_idx = self._page * self._hands_per_page
        visible = self._filtered_hands[start_idx:start_idx + self._hands_per_page]

        for i, hand in enumerate(visible):
            y = list_y + i * row_height

            # Background
            is_selected = hand == self._selected_hand
            if is_selected:
                bg_color = (60, 80, 60)
            elif len(hand.mistakes) > 0:
                bg_color = (60, 50, 50)
            else:
                bg_color = (45, 45, 55)

            pygame.draw.rect(
                surface,
                bg_color,
                (list_x, y, 300, row_height - 2),
                border_radius=3,
            )

            # Time
            try:
                dt = datetime.fromisoformat(hand.timestamp)
                time_str = dt.strftime("%H:%M")
            except ValueError:
                time_str = "??:??"
            time_surf = self._small_font.render(time_str, True, COLORS.TEXT_WHITE)
            surface.blit(time_surf, (list_x + 8, y + 8))

            # Cards (abbreviated)
            cards = " ".join(hand.player_cards[:3])
            if len(hand.player_cards) > 3:
                cards += "..."
            cards_surf = self._small_font.render(cards, True, COLORS.TEXT_WHITE)
            surface.blit(cards_surf, (list_x + 75, y + 8))

            # Outcome
            outcome_colors = {
                "win": (100, 180, 100),
                "blackjack": (180, 180, 100),
                "lose": (180, 100, 100),
                "bust": (180, 80, 80),
                "push": (150, 150, 150),
                "surrender": (150, 120, 100),
            }
            outcome_color = outcome_colors.get(hand.outcome, COLORS.TEXT_WHITE)
            outcome_surf = self._small_font.render(hand.outcome.upper(), True, outcome_color)
            surface.blit(outcome_surf, (list_x + 175, y + 8))

            # Profit/Loss
            if hand.profit_loss >= 0:
                pl_text = f"+{hand.profit_loss:.0f}"
                pl_color = (100, 180, 100)
            else:
                pl_text = f"{hand.profit_loss:.0f}"
                pl_color = (180, 100, 100)
            pl_surf = self._small_font.render(pl_text, True, pl_color)
            surface.blit(pl_surf, (list_x + 255, y + 8))

            # Mistake indicator
            if len(hand.mistakes) > 0:
                err_surf = self._small_font.render("!", True, (255, 100, 100))
                surface.blit(err_surf, (list_x + 290, y + 8))

    def _draw_hand_details(self, surface: pygame.Surface) -> None:
        """Draw details for selected hand."""
        detail_x = DIMENSIONS.CENTER_X + 180 - 150
        detail_y = DIMENSIONS.CENTER_Y - 150

        # Header
        header = self._font.render("Hand Details", True, COLORS.GOLD)
        surface.blit(header, (detail_x, detail_y - 25))

        if not self._selected_hand:
            hint = self._font.render("Select a hand to", True, COLORS.TEXT_MUTED)
            hint2 = self._font.render("view details", True, COLORS.TEXT_MUTED)
            surface.blit(hint, (detail_x + 60, detail_y + 80))
            surface.blit(hint2, (detail_x + 75, detail_y + 105))
            return

        hand = self._selected_hand
        y = detail_y

        # Timestamp
        try:
            dt = datetime.fromisoformat(hand.timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            time_str = "Unknown"
        time_surf = self._small_font.render(f"Time: {time_str}", True, COLORS.TEXT_MUTED)
        surface.blit(time_surf, (detail_x, y))
        y += 25

        # Player cards
        player_text = f"Player: {' '.join(hand.player_cards)} = {hand.player_final_value}"
        player_surf = self._font.render(player_text, True, COLORS.TEXT_WHITE)
        surface.blit(player_surf, (detail_x, y))
        y += 25

        # Dealer cards
        dealer_text = f"Dealer: {' '.join(hand.dealer_cards)} = {hand.dealer_final_value}"
        dealer_surf = self._font.render(dealer_text, True, COLORS.TEXT_WHITE)
        surface.blit(dealer_surf, (detail_x, y))
        y += 30

        # Betting
        bet_text = f"Bet: ${hand.initial_bet}"
        if hand.final_bet != hand.initial_bet:
            bet_text += f" → ${hand.final_bet}"
        bet_surf = self._font.render(bet_text, True, COLORS.TEXT_WHITE)
        surface.blit(bet_surf, (detail_x, y))
        y += 25

        # Count
        count_text = f"Count: RC {hand.running_count:+d}, TC {hand.true_count:+.1f}"
        count_surf = self._font.render(count_text, True, COLORS.TEXT_WHITE)
        surface.blit(count_surf, (detail_x, y))
        y += 30

        # Outcome
        outcome_text = f"Outcome: {hand.outcome.upper()}"
        if hand.profit_loss >= 0:
            outcome_text += f" (+${hand.profit_loss:.0f})"
        else:
            outcome_text += f" (${hand.profit_loss:.0f})"
        outcome_surf = self._font.render(outcome_text, True, COLORS.GOLD)
        surface.blit(outcome_surf, (detail_x, y))
        y += 35

        # Decisions
        dec_header = self._font.render("Decisions:", True, COLORS.TEXT_WHITE)
        surface.blit(dec_header, (detail_x, y))
        y += 22

        for decision in hand.decisions[:5]:  # Limit to 5
            action = decision.get("action", "?")
            correct = decision.get("is_correct", True)
            color = (100, 180, 100) if correct else (180, 100, 100)

            dec_text = f"  {action.upper()}"
            if not correct:
                dec_text += f" (should {decision.get('correct_action', '?')})"

            dec_surf = self._small_font.render(dec_text, True, color)
            surface.blit(dec_surf, (detail_x, y))
            y += 18

        # Mistakes summary
        if len(hand.mistakes) > 0:
            y += 10
            err_text = f"Mistakes: {len(hand.mistakes)}"
            err_surf = self._font.render(err_text, True, (180, 100, 100))
            surface.blit(err_surf, (detail_x, y))
