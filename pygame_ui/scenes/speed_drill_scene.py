"""Speed drill scene for timed card counting challenges."""

import random
import time
from typing import Optional, List
from enum import Enum, auto

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.card import CardSprite
from pygame_ui.components.toast import ToastManager, ToastType
from pygame_ui.core.sound_manager import play_sound
from pygame_ui.core.particles import get_particle_system
from pygame_ui.effects.crt_filter import CRTFilter

from core.cards import Card, Rank, Suit
from core.counting.hilo import HiLoSystem


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


class DrillState(Enum):
    """States for the speed drill."""
    SETUP = auto()
    COUNTDOWN = auto()
    RUNNING = auto()
    WAITING_INPUT = auto()
    SHOWING_RESULT = auto()


class SpeedDrillScene(BaseScene):
    """Scene for timed card counting challenges.

    Features:
    - 52-card deck countdown
    - Real-time timer
    - Score calculation (base + time bonus + accuracy)
    - High scores tracking
    """

    def __init__(self):
        super().__init__()

        self.state = DrillState.SETUP

        # Drill state
        self.cards: List[Card] = []
        self.current_card_index = 0
        self.card_sprite: Optional[CardSprite] = None
        self.counter = HiLoSystem()
        self.actual_count = 0

        # Timer
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.countdown_value = 3

        # User input
        self.user_input = ""

        # Scoring
        self.score = 0
        self.high_scores: List[int] = []  # Could persist to file

        # Timing for card display
        self.card_display_time = 0.0
        self.cards_per_second = 2.0  # Start slower, can increase

        # UI
        self.start_button: Optional[Button] = None
        self.back_button: Optional[Button] = None
        self.toast_manager = ToastManager()

        # Particles
        self.particles = get_particle_system()

        # Visual effects
        self.crt_filter = CRTFilter(scanline_alpha=20, vignette_strength=0.2)

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._timer_font: Optional[pygame.font.Font] = None
        self._countdown_font: Optional[pygame.font.Font] = None
        self._input_font: Optional[pygame.font.Font] = None
        self._score_font: Optional[pygame.font.Font] = None
        self._label_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 48)
        return self._title_font

    @property
    def timer_font(self) -> pygame.font.Font:
        if self._timer_font is None:
            self._timer_font = pygame.font.Font(None, 64)
        return self._timer_font

    @property
    def countdown_font(self) -> pygame.font.Font:
        if self._countdown_font is None:
            self._countdown_font = pygame.font.Font(None, 200)
        return self._countdown_font

    @property
    def input_font(self) -> pygame.font.Font:
        if self._input_font is None:
            self._input_font = pygame.font.Font(None, 48)
        return self._input_font

    @property
    def score_font(self) -> pygame.font.Font:
        if self._score_font is None:
            self._score_font = pygame.font.Font(None, 56)
        return self._score_font

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
        self.particles.clear()

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
            y=DIMENSIONS.CENTER_Y + 100,
            text="START CHALLENGE",
            font_size=32,
            on_click=self._start_countdown,
            bg_color=(120, 80, 60),
            hover_color=(150, 100, 80),
            width=250,
            height=55,
        )

    def _start_countdown(self) -> None:
        """Start the countdown before the drill."""
        self.countdown_value = 3
        self.state = DrillState.COUNTDOWN
        self.elapsed_time = 0.0

    def _start_drill(self) -> None:
        """Start the actual drill."""
        # Generate shuffled deck
        self.cards = []
        for suit in Suit:
            for rank in Rank:
                self.cards.append(Card(rank, suit))
        random.shuffle(self.cards)

        self.current_card_index = 0
        self.counter.reset()
        self.actual_count = 0
        self.user_input = ""

        # Start timer
        self.start_time = time.time()
        self.card_display_time = 0.0

        # Show first card
        self._show_current_card()

        self.state = DrillState.RUNNING
        play_sound("card_deal")

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
        self.card_sprite.scale = 1.8

    def _finish_cards(self) -> None:
        """All cards have been shown."""
        self.elapsed_time = time.time() - self.start_time
        self.state = DrillState.WAITING_INPUT
        self.card_sprite = None

    def _check_answer(self) -> None:
        """Check the user's answer and calculate score."""
        try:
            user_count = int(self.user_input) if self.user_input else 0
        except ValueError:
            user_count = 0

        # Calculate score
        base_score = 1000
        is_correct = user_count == self.actual_count

        if is_correct:
            # Time bonus: faster = more points
            # Baseline is 30 seconds for full deck
            time_bonus = max(0, int((30 - self.elapsed_time) * 50))

            # Accuracy bonus
            accuracy_bonus = 500

            self.score = base_score + time_bonus + accuracy_bonus

            self.toast_manager.spawn(
                f"PERFECT! Score: {self.score}",
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 100,
                ToastType.SUCCESS,
                duration=3.0,
            )
            play_sound("blackjack")
            self.particles.emit_burst(DIMENSIONS.CENTER_X, DIMENSIONS.CENTER_Y, "stars", 30)
            self.particles.emit_burst(DIMENSIONS.CENTER_X, DIMENSIONS.CENTER_Y, "confetti", 50)
        else:
            # Partial score based on how close
            diff = abs(user_count - self.actual_count)
            partial_accuracy = max(0, 500 - diff * 100)
            time_bonus = max(0, int((30 - self.elapsed_time) * 25))

            self.score = time_bonus + partial_accuracy

            self.toast_manager.spawn(
                f"Off by {diff}. Score: {self.score}",
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 100,
                ToastType.WARNING if diff <= 2 else ToastType.ERROR,
                duration=3.0,
            )
            play_sound("lose")

        # Update high scores
        self.high_scores.append(self.score)
        self.high_scores.sort(reverse=True)
        self.high_scores = self.high_scores[:5]  # Keep top 5

        self.state = DrillState.SHOWING_RESULT

    def _on_back(self) -> None:
        """Handle back button click."""
        self.change_scene("drill_menu", transition=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        if self.state == DrillState.SETUP:
            # Start button
            if self.start_button and self.start_button.handle_event(event):
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

        # Update card sprite
        if self.card_sprite:
            self.card_sprite.update(dt)

        # Update toast
        self.toast_manager.update(dt)

        # Update particles
        self.particles.update(dt)

        # State-specific updates
        if self.state == DrillState.COUNTDOWN:
            self.elapsed_time += dt
            new_countdown = 3 - int(self.elapsed_time)
            if new_countdown != self.countdown_value and new_countdown > 0:
                self.countdown_value = new_countdown
                play_sound("button_click")
            elif self.elapsed_time >= 3.0:
                self._start_drill()

        elif self.state == DrillState.RUNNING:
            self.card_display_time += dt

            # Adaptive speed: start at 2 cards/sec, ramp up to 4 cards/sec
            progress = self.current_card_index / 52
            current_speed = 2.0 + progress * 2.0  # 2 to 4 cards per second

            if self.card_display_time >= (1.0 / current_speed):
                self.card_display_time = 0.0
                self.current_card_index += 1

                if self.current_card_index >= len(self.cards):
                    self._finish_cards()
                else:
                    self._show_current_card()
                    play_sound("card_flip")

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.FELT_GREEN)

        # Title
        title = self.title_font.render("SPEED CHALLENGE", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 50))
        surface.blit(title, title_rect)

        if self.state == DrillState.SETUP:
            self._draw_setup(surface)
        elif self.state == DrillState.COUNTDOWN:
            self._draw_countdown(surface)
        elif self.state == DrillState.RUNNING:
            self._draw_running(surface)
        elif self.state == DrillState.WAITING_INPUT:
            self._draw_input(surface)
        elif self.state == DrillState.SHOWING_RESULT:
            self._draw_result(surface)

        # Back button (always visible)
        if self.back_button:
            self.back_button.draw(surface)

        # Toasts
        self.toast_manager.draw(surface)

        # Particles
        self.particles.draw(surface)

        # Apply CRT filter
        self.crt_filter.apply(surface)

    def _draw_setup(self, surface: pygame.Surface) -> None:
        """Draw the setup screen."""
        # Description
        desc_lines = [
            "Count a full shuffled deck as fast as you can!",
            "Cards will flash increasingly faster.",
            "Enter the final running count to score.",
        ]

        y_start = 180
        for i, line in enumerate(desc_lines):
            text = self.label_font.render(line, True, COLORS.TEXT_MUTED)
            text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, y_start + i * 35))
            surface.blit(text, text_rect)

        # High scores
        if self.high_scores:
            hs_label = self.label_font.render("HIGH SCORES:", True, COLORS.GOLD)
            hs_rect = hs_label.get_rect(center=(DIMENSIONS.CENTER_X, 350))
            surface.blit(hs_label, hs_rect)

            for i, score in enumerate(self.high_scores[:5]):
                score_text = self.label_font.render(f"{i + 1}. {score}", True, COLORS.TEXT_WHITE)
                score_rect = score_text.get_rect(center=(DIMENSIONS.CENTER_X, 385 + i * 28))
                surface.blit(score_text, score_rect)

        # Start button
        if self.start_button:
            self.start_button.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Press START to begin | ESC: Back"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

    def _draw_countdown(self, surface: pygame.Surface) -> None:
        """Draw the countdown."""
        text = self.countdown_font.render(str(self.countdown_value), True, COLORS.GOLD)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.CENTER_Y))
        surface.blit(text, text_rect)

        # Ready message
        ready = self.label_font.render("GET READY!", True, COLORS.TEXT_WHITE)
        ready_rect = ready.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.CENTER_Y + 100))
        surface.blit(ready, ready_rect)

    def _draw_running(self, surface: pygame.Surface) -> None:
        """Draw during the drill."""
        # Progress
        progress_text = f"Card {self.current_card_index + 1} / 52"
        progress = self.label_font.render(progress_text, True, COLORS.TEXT_WHITE)
        progress_rect = progress.get_rect(center=(DIMENSIONS.CENTER_X, 100))
        surface.blit(progress, progress_rect)

        # Progress bar
        bar_width = 400
        bar_height = 15
        bar_x = DIMENSIONS.CENTER_X - bar_width / 2
        bar_y = 130

        # Background
        pygame.draw.rect(
            surface,
            COLORS.PANEL_BG,
            (bar_x, bar_y, bar_width, bar_height),
            border_radius=5,
        )

        # Fill
        fill_width = (self.current_card_index / 52) * bar_width
        pygame.draw.rect(
            surface,
            COLORS.GOLD,
            (bar_x, bar_y, fill_width, bar_height),
            border_radius=5,
        )

        # Timer
        elapsed = time.time() - self.start_time
        timer_text = f"{elapsed:.1f}s"
        timer = self.timer_font.render(timer_text, True, COLORS.TEXT_WHITE)
        timer_rect = timer.get_rect(center=(DIMENSIONS.CENTER_X, 180))
        surface.blit(timer, timer_rect)

        # Current card
        if self.card_sprite:
            self.card_sprite.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Keep counting! | ESC: Cancel"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

    def _draw_input(self, surface: pygame.Surface) -> None:
        """Draw the input screen."""
        # Time display
        time_text = f"Time: {self.elapsed_time:.2f}s"
        time_rendered = self.timer_font.render(time_text, True, COLORS.GOLD)
        time_rect = time_rendered.get_rect(center=(DIMENSIONS.CENTER_X, 150))
        surface.blit(time_rendered, time_rect)

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

        # Cursor
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
        """Draw the result screen."""
        # Score
        score_text = f"SCORE: {self.score}"
        score = self.score_font.render(score_text, True, COLORS.GOLD)
        score_rect = score.get_rect(center=(DIMENSIONS.CENTER_X, 150))
        surface.blit(score, score_rect)

        # Time
        time_text = f"Time: {self.elapsed_time:.2f}s"
        time_rendered = self.label_font.render(time_text, True, COLORS.TEXT_WHITE)
        time_rect = time_rendered.get_rect(center=(DIMENSIONS.CENTER_X, 220))
        surface.blit(time_rendered, time_rect)

        # User answer vs correct
        user_text = f"Your answer: {self.user_input or '0'}"
        user = self.label_font.render(user_text, True, COLORS.TEXT_WHITE)
        user_rect = user.get_rect(center=(DIMENSIONS.CENTER_X, 280))
        surface.blit(user, user_rect)

        correct_text = f"Correct answer: {self.actual_count}"
        correct = self.label_font.render(correct_text, True, COLORS.GOLD)
        correct_rect = correct.get_rect(center=(DIMENSIONS.CENTER_X, 320))
        surface.blit(correct, correct_rect)

        # High score check
        if self.high_scores and self.score == self.high_scores[0]:
            new_high = self.label_font.render("NEW HIGH SCORE!", True, COLORS.COUNT_POSITIVE)
            new_rect = new_high.get_rect(center=(DIMENSIONS.CENTER_X, 380))
            surface.blit(new_high, new_rect)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Press ENTER or SPACE to continue"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)
