"""Counting drill scene for practicing card counting."""

import random
from typing import Optional, List
from enum import Enum, auto

import pygame

from pygame_ui.config import COLORS, DIMENSIONS, ANIMATION
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.card import CardSprite
from pygame_ui.components.toast import ToastManager, ToastType
from pygame_ui.core.animation import EaseType
from pygame_ui.core.sound_manager import play_sound
from pygame_ui.core.difficulty_manager import create_counting_drill_manager
from pygame_ui.effects.crt_filter import CRTFilter

from core.cards import Card, Rank, Suit
from core.counting.hilo import HiLoSystem
from core.counting.ko import KOSystem
from core.counting.omega2 import Omega2System
from core.counting.wong_halves import WongHalvesSystem


class DrillState(Enum):
    """States for the counting drill."""
    SETUP = auto()
    SHOWING_CARDS = auto()
    WAITING_INPUT = auto()
    SHOWING_RESULT = auto()


# Map core Suit to pygame_ui suit names
SUIT_MAP = {
    Suit.HEARTS: "hearts",
    Suit.DIAMONDS: "diamonds",
    Suit.CLUBS: "clubs",
    Suit.SPADES: "spades",
}

# Map core Rank to pygame_ui value strings
RANK_MAP = {
    Rank.TWO: "2",
    Rank.THREE: "3",
    Rank.FOUR: "4",
    Rank.FIVE: "5",
    Rank.SIX: "6",
    Rank.SEVEN: "7",
    Rank.EIGHT: "8",
    Rank.NINE: "9",
    Rank.TEN: "10",
    Rank.JACK: "J",
    Rank.QUEEN: "Q",
    Rank.KING: "K",
    Rank.ACE: "A",
}


class CountingDrillScene(BaseScene):
    """Scene for practicing card counting.

    Features:
    - Cards flash on screen one at a time
    - User enters their running count
    - System validates against actual count
    - Supports multiple counting systems
    """

    COUNTING_SYSTEMS = {
        "Hi-Lo": HiLoSystem,
        "KO": KOSystem,
        "Omega II": Omega2System,
        "Wong Halves": WongHalvesSystem,
    }

    def __init__(self):
        super().__init__()

        self.state = DrillState.SETUP

        # Settings
        self.card_count = 10
        self.card_speed = 1500  # milliseconds per card
        self.system_name = "Hi-Lo"

        # Drill state
        self.cards: List[Card] = []
        self.current_card_index = 0
        self.card_sprite: Optional[CardSprite] = None
        self.counter = HiLoSystem()
        self.actual_count = 0

        # User input
        self.user_input = ""
        self.input_active = False

        # Timing
        self.card_timer = 0.0
        self.result_display_time = 0.0

        # UI
        self.start_button: Optional[Button] = None
        self.back_button: Optional[Button] = None
        self.system_buttons: List[Button] = []
        self.card_count_buttons: List[Button] = []
        self.speed_buttons: List[Button] = []
        self.toast_manager = ToastManager()

        # Stats
        self.drills_completed = 0
        self.drills_correct = 0

        # Progressive difficulty
        self.difficulty = create_counting_drill_manager()

        # Visual effects
        self.crt_filter = CRTFilter(scanline_alpha=20, vignette_strength=0.2)

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._count_font: Optional[pygame.font.Font] = None
        self._input_font: Optional[pygame.font.Font] = None
        self._label_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 48)
        return self._title_font

    @property
    def count_font(self) -> pygame.font.Font:
        if self._count_font is None:
            self._count_font = pygame.font.Font(None, 72)
        return self._count_font

    @property
    def input_font(self) -> pygame.font.Font:
        if self._input_font is None:
            self._input_font = pygame.font.Font(None, 48)
        return self._input_font

    @property
    def label_font(self) -> pygame.font.Font:
        if self._label_font is None:
            self._label_font = pygame.font.Font(None, 28)
        return self._label_font

    def on_enter(self) -> None:
        """Initialize the scene."""
        super().on_enter()
        self._setup_ui()
        self.state = DrillState.SETUP

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

        # Start button
        self.start_button = Button(
            x=DIMENSIONS.CENTER_X,
            y=DIMENSIONS.SCREEN_HEIGHT - 100,
            text="START DRILL",
            font_size=32,
            on_click=self._start_drill,
            bg_color=(60, 100, 60),
            hover_color=(80, 130, 80),
            width=200,
            height=50,
        )

        # System selection buttons
        system_y = 180
        system_names = list(self.COUNTING_SYSTEMS.keys())
        total_width = len(system_names) * 130
        start_x = DIMENSIONS.CENTER_X - total_width / 2 + 65

        self.system_buttons = []
        for i, name in enumerate(system_names):
            btn = Button(
                x=start_x + i * 130,
                y=system_y,
                text=name,
                font_size=22,
                on_click=lambda n=name: self._select_system(n),
                bg_color=(60, 80, 100) if name != self.system_name else COLORS.GOLD_DARK,
                hover_color=(80, 100, 130),
                width=120,
                height=35,
            )
            self.system_buttons.append(btn)

        # Card count buttons
        count_y = 280
        counts = [5, 10, 20, 52]
        total_width = len(counts) * 80
        start_x = DIMENSIONS.CENTER_X - total_width / 2 + 40

        self.card_count_buttons = []
        for i, count in enumerate(counts):
            btn = Button(
                x=start_x + i * 80,
                y=count_y,
                text=str(count),
                font_size=24,
                on_click=lambda c=count: self._select_card_count(c),
                bg_color=(60, 80, 100) if count != self.card_count else COLORS.GOLD_DARK,
                hover_color=(80, 100, 130),
                width=70,
                height=35,
            )
            self.card_count_buttons.append(btn)

        # Speed buttons
        speed_y = 380
        speeds = [("Fast", 800), ("Normal", 1500), ("Slow", 2500)]
        total_width = len(speeds) * 100
        start_x = DIMENSIONS.CENTER_X - total_width / 2 + 50

        self.speed_buttons = []
        for i, (label, speed) in enumerate(speeds):
            btn = Button(
                x=start_x + i * 100,
                y=speed_y,
                text=label,
                font_size=22,
                on_click=lambda s=speed: self._select_speed(s),
                bg_color=(60, 80, 100) if speed != self.card_speed else COLORS.GOLD_DARK,
                hover_color=(80, 100, 130),
                width=90,
                height=35,
            )
            self.speed_buttons.append(btn)

    def _select_system(self, name: str) -> None:
        """Select a counting system."""
        self.system_name = name
        system_class = self.COUNTING_SYSTEMS.get(name, HiLoSystem)
        self.counter = system_class()
        self._update_button_colors()

    def _select_card_count(self, count: int) -> None:
        """Select number of cards."""
        self.card_count = count
        self._update_button_colors()

    def _select_speed(self, speed: int) -> None:
        """Select card display speed."""
        self.card_speed = speed
        self._update_button_colors()

    def _update_button_colors(self) -> None:
        """Update button colors based on selection."""
        # System buttons
        for btn in self.system_buttons:
            if btn.text == self.system_name:
                btn.bg_color = COLORS.GOLD_DARK
            else:
                btn.bg_color = (60, 80, 100)

        # Count buttons
        counts = [5, 10, 20, 52]
        for i, btn in enumerate(self.card_count_buttons):
            if counts[i] == self.card_count:
                btn.bg_color = COLORS.GOLD_DARK
            else:
                btn.bg_color = (60, 80, 100)

        # Speed buttons
        speeds = [800, 1500, 2500]
        for i, btn in enumerate(self.speed_buttons):
            if speeds[i] == self.card_speed:
                btn.bg_color = COLORS.GOLD_DARK
            else:
                btn.bg_color = (60, 80, 100)

    def _start_drill(self) -> None:
        """Start a new counting drill."""
        # Generate random cards
        self.cards = self._generate_cards(self.card_count)
        self.current_card_index = 0

        # Reset counter
        self.counter.reset()
        self.actual_count = 0

        # Reset state
        self.user_input = ""
        self.input_active = False
        self.card_timer = 0.0

        # Create first card sprite
        self._show_current_card()

        self.state = DrillState.SHOWING_CARDS
        play_sound("card_deal")

    def _generate_cards(self, count: int) -> List[Card]:
        """Generate random cards for the drill."""
        # Create a deck
        deck = []
        for suit in Suit:
            for rank in Rank:
                deck.append(Card(rank, suit))

        random.shuffle(deck)
        return deck[:count]

    def _show_current_card(self) -> None:
        """Display the current card."""
        if self.current_card_index >= len(self.cards):
            return

        card = self.cards[self.current_card_index]

        # Count this card
        self.counter.count_card(card)
        self.actual_count = int(self.counter.running_count)

        # Create card sprite
        self.card_sprite = CardSprite(
            x=DIMENSIONS.CENTER_X,
            y=DIMENSIONS.CENTER_Y,
            face_up=True,
            card_value=RANK_MAP[card.rank],
            card_suit=SUIT_MAP[card.suit],
        )
        self.card_sprite.scale = 1.5

    def _on_back(self) -> None:
        """Handle back button click."""
        self.change_scene("drill_menu", transition=True)

    def _check_answer(self) -> None:
        """Check the user's answer."""
        try:
            user_count = int(self.user_input) if self.user_input else 0
        except ValueError:
            user_count = 0

        self.drills_completed += 1
        is_correct = user_count == self.actual_count

        # Update difficulty
        level_change = self.difficulty.record(is_correct)

        if is_correct:
            self.drills_correct += 1
            self.toast_manager.spawn(
                "CORRECT!",
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 50,
                ToastType.SUCCESS,
                duration=2.0,
            )
            play_sound("win")
        else:
            self.toast_manager.spawn(
                f"INCORRECT - Answer: {self.actual_count}",
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 50,
                ToastType.ERROR,
                duration=2.0,
            )
            play_sound("lose")

        # Show level change notification
        if level_change:
            self.toast_manager.spawn(
                level_change,
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y,
                ToastType.INFO,
                duration=2.0,
            )

        self.state = DrillState.SHOWING_RESULT
        self.result_display_time = 0.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        if self.state == DrillState.SETUP:
            # Start button
            if self.start_button and self.start_button.handle_event(event):
                return True

            # Setting buttons
            for btn in self.system_buttons + self.card_count_buttons + self.speed_buttons:
                if btn.handle_event(event):
                    return True

        elif self.state == DrillState.WAITING_INPUT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self._check_answer()
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.user_input = self.user_input[:-1]
                    return True
                elif event.key == pygame.K_MINUS:
                    if not self.user_input or (self.user_input and self.user_input[0] != '-'):
                        self.user_input = "-" + self.user_input
                    return True
                elif event.unicode.isdigit():
                    self.user_input += event.unicode
                    return True

        elif self.state == DrillState.SHOWING_RESULT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.state = DrillState.SETUP
                    return True

        # Global shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state != DrillState.SETUP:
                    self.state = DrillState.SETUP
                else:
                    self._on_back()
                return True

        return False

    def update(self, dt: float) -> None:
        """Update scene."""
        # Update buttons
        if self.back_button:
            self.back_button.update(dt)
        if self.start_button:
            self.start_button.update(dt)
        for btn in self.system_buttons + self.card_count_buttons + self.speed_buttons:
            btn.update(dt)

        # Update card sprite
        if self.card_sprite:
            self.card_sprite.update(dt)

        # Update toast
        self.toast_manager.update(dt)

        # State-specific updates
        if self.state == DrillState.SHOWING_CARDS:
            self.card_timer += dt * 1000  # Convert to ms

            if self.card_timer >= self.card_speed:
                self.card_timer = 0.0
                self.current_card_index += 1

                if self.current_card_index >= len(self.cards):
                    # All cards shown, wait for input
                    self.state = DrillState.WAITING_INPUT
                    self.input_active = True
                    self.card_sprite = None
                else:
                    self._show_current_card()
                    play_sound("card_flip")

        elif self.state == DrillState.SHOWING_RESULT:
            self.result_display_time += dt
            if self.result_display_time >= 2.5:
                self.state = DrillState.SETUP

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.FELT_GREEN)

        # Title
        title = self.title_font.render("COUNTING DRILL", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 50))
        surface.blit(title, title_rect)

        if self.state == DrillState.SETUP:
            self._draw_setup(surface)
        elif self.state == DrillState.SHOWING_CARDS:
            self._draw_showing_cards(surface)
        elif self.state == DrillState.WAITING_INPUT:
            self._draw_input(surface)
        elif self.state == DrillState.SHOWING_RESULT:
            self._draw_result(surface)

        # Back button (always visible)
        if self.back_button:
            self.back_button.draw(surface)

        # Toasts
        self.toast_manager.draw(surface)

        # Stats
        if self.drills_completed > 0:
            accuracy = (self.drills_correct / self.drills_completed) * 100
            stats_text = f"Accuracy: {self.drills_correct}/{self.drills_completed} ({accuracy:.0f}%)"
            stats = self.label_font.render(stats_text, True, COLORS.TEXT_WHITE)
            stats_rect = stats.get_rect(topright=(DIMENSIONS.SCREEN_WIDTH - 20, 20))
            surface.blit(stats, stats_rect)

        # Apply CRT filter
        self.crt_filter.apply(surface)

    def _draw_setup(self, surface: pygame.Surface) -> None:
        """Draw the setup screen."""
        # System selection
        label = self.label_font.render("Counting System:", True, COLORS.TEXT_MUTED)
        surface.blit(label, (DIMENSIONS.CENTER_X - 200, 145))
        for btn in self.system_buttons:
            btn.draw(surface)

        # Card count selection
        label = self.label_font.render("Number of Cards:", True, COLORS.TEXT_MUTED)
        surface.blit(label, (DIMENSIONS.CENTER_X - 200, 245))
        for btn in self.card_count_buttons:
            btn.draw(surface)

        # Speed selection
        label = self.label_font.render("Card Speed:", True, COLORS.TEXT_MUTED)
        surface.blit(label, (DIMENSIONS.CENTER_X - 200, 345))
        for btn in self.speed_buttons:
            btn.draw(surface)

        # Difficulty indicator
        diff_text = f"Difficulty: {self.difficulty.settings.name}"
        diff = self.label_font.render(diff_text, True, COLORS.TEXT_MUTED)
        diff_rect = diff.get_rect(center=(DIMENSIONS.CENTER_X, 440))
        surface.blit(diff, diff_rect)

        # Start button
        if self.start_button:
            self.start_button.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Configure settings and press START DRILL | ESC: Back"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

    def _draw_showing_cards(self, surface: pygame.Surface) -> None:
        """Draw the card display phase."""
        # Progress
        progress_text = f"Card {self.current_card_index + 1} of {len(self.cards)}"
        progress = self.label_font.render(progress_text, True, COLORS.TEXT_WHITE)
        progress_rect = progress.get_rect(center=(DIMENSIONS.CENTER_X, 120))
        surface.blit(progress, progress_rect)

        # System being used
        system_text = f"System: {self.system_name}"
        system = self.label_font.render(system_text, True, COLORS.TEXT_MUTED)
        system_rect = system.get_rect(center=(DIMENSIONS.CENTER_X, 150))
        surface.blit(system, system_rect)

        # Current card
        if self.card_sprite:
            self.card_sprite.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Count the cards as they appear | ESC: Cancel"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

    def _draw_input(self, surface: pygame.Surface) -> None:
        """Draw the input phase."""
        # Prompt
        prompt = self.label_font.render("Enter the running count:", True, COLORS.TEXT_WHITE)
        prompt_rect = prompt.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.CENTER_Y - 80))
        surface.blit(prompt, prompt_rect)

        # Input box
        input_rect = pygame.Rect(
            DIMENSIONS.CENTER_X - 100,
            DIMENSIONS.CENTER_Y - 40,
            200,
            60,
        )
        pygame.draw.rect(surface, COLORS.PANEL_BG, input_rect, border_radius=8)
        pygame.draw.rect(surface, COLORS.GOLD, input_rect, width=3, border_radius=8)

        # Input text
        display_text = self.user_input or "0"
        input_text = self.input_font.render(display_text, True, COLORS.TEXT_WHITE)
        input_text_rect = input_text.get_rect(center=input_rect.center)
        surface.blit(input_text, input_text_rect)

        # Cursor blink
        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            cursor_x = input_text_rect.right + 5
            pygame.draw.line(
                surface,
                COLORS.TEXT_WHITE,
                (cursor_x, input_rect.centery - 20),
                (cursor_x, input_rect.centery + 20),
                2,
            )

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Type your count and press ENTER | ESC: Cancel"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

    def _draw_result(self, surface: pygame.Surface) -> None:
        """Draw the result phase."""
        # Show user's answer vs correct
        user_text = f"Your answer: {self.user_input or '0'}"
        user = self.label_font.render(user_text, True, COLORS.TEXT_WHITE)
        user_rect = user.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.CENTER_Y + 50))
        surface.blit(user, user_rect)

        correct_text = f"Correct answer: {self.actual_count}"
        correct = self.label_font.render(correct_text, True, COLORS.GOLD)
        correct_rect = correct.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.CENTER_Y + 90))
        surface.blit(correct, correct_rect)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Press ENTER or SPACE to continue"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)
