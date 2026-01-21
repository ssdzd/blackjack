"""Deck estimation drill scene for practicing estimating remaining decks."""

import random
from typing import Optional, List
from enum import Enum, auto

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.toast import ToastManager, ToastType
from pygame_ui.core.sound_manager import play_sound
from pygame_ui.core.difficulty_manager import create_deck_estimation_manager
from pygame_ui.effects.crt_filter import CRTFilter


class DrillState(Enum):
    """States for the deck estimation drill."""
    SETUP = auto()
    SHOWING_DISCARD = auto()
    WAITING_INPUT = auto()
    SHOWING_RESULT = auto()


class DeckEstimationScene(BaseScene):
    """Scene for practicing deck estimation.

    Features:
    - Visual discard tray with stacked cards
    - Visual shoe showing remaining cards
    - Slider/button grid for answer selection
    - Reference guide showing full deck height
    - Progressive difficulty
    """

    def __init__(self):
        super().__init__()

        self.state = DrillState.SETUP

        # Problem parameters
        self.decks_total = 6
        self.cards_dealt = 0
        self.decks_remaining = 6.0
        self.tolerance = 0.5  # Accept answers within this range

        # User selection
        self.selected_answer: Optional[float] = None

        # UI
        self.start_button: Optional[Button] = None
        self.deck_buttons: List[Button] = []
        self.answer_buttons: List[Button] = []
        self.back_button: Optional[Button] = None
        self.toast_manager = ToastManager()

        # Stats
        self.drills_completed = 0
        self.drills_correct = 0

        # Timing
        self.result_display_time = 0.0
        self.problem_display_time = 0.0

        # Progressive difficulty
        self.difficulty = create_deck_estimation_manager()

        # Visual effects
        self.crt_filter = CRTFilter(scanline_alpha=20, vignette_strength=0.2)

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._label_font: Optional[pygame.font.Font] = None
        self._value_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 48)
        return self._title_font

    @property
    def label_font(self) -> pygame.font.Font:
        if self._label_font is None:
            self._label_font = pygame.font.Font(None, 28)
        return self._label_font

    @property
    def value_font(self) -> pygame.font.Font:
        if self._value_font is None:
            self._value_font = pygame.font.Font(None, 36)
        return self._value_font

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

        # Deck count selection
        deck_y = 200
        decks = [2, 4, 6, 8]
        total_width = len(decks) * 80
        start_x = DIMENSIONS.CENTER_X - total_width / 2 + 40

        self.deck_buttons = []
        for i, count in enumerate(decks):
            btn = Button(
                x=start_x + i * 80,
                y=deck_y,
                text=str(count),
                font_size=24,
                on_click=lambda c=count: self._select_decks(c),
                bg_color=COLORS.GOLD_DARK if count == self.decks_total else (60, 80, 100),
                hover_color=(80, 100, 130),
                width=70,
                height=35,
            )
            self.deck_buttons.append(btn)

        # Answer buttons will be created when drill starts
        self.answer_buttons = []

    def _select_decks(self, count: int) -> None:
        """Select total deck count."""
        self.decks_total = count
        self._update_deck_button_colors()

    def _update_deck_button_colors(self) -> None:
        """Update deck button colors based on selection."""
        decks = [2, 4, 6, 8]
        for i, btn in enumerate(self.deck_buttons):
            if decks[i] == self.decks_total:
                btn.bg_color = COLORS.GOLD_DARK
            else:
                btn.bg_color = (60, 80, 100)

    def _create_answer_buttons(self) -> None:
        """Create answer selection buttons based on total decks."""
        self.answer_buttons = []

        # Generate options from 0.5 to decks_total in 0.5 increments
        options = [x * 0.5 for x in range(1, self.decks_total * 2 + 1)]

        # Layout in 2 rows
        buttons_per_row = len(options) // 2 + len(options) % 2
        button_width = 70
        button_height = 40
        button_spacing = 80
        row_spacing = 50

        start_y = 550

        for i, value in enumerate(options):
            row = i // buttons_per_row
            col = i % buttons_per_row

            # Center each row
            row_count = min(buttons_per_row, len(options) - row * buttons_per_row)
            total_width = row_count * button_spacing
            start_x = DIMENSIONS.CENTER_X - total_width / 2 + button_spacing / 2

            x = start_x + col * button_spacing
            y = start_y + row * row_spacing

            # Format value display
            if value == int(value):
                display = str(int(value))
            else:
                display = f"{value:.1f}"

            btn = Button(
                x=x,
                y=y,
                text=display,
                font_size=22,
                on_click=lambda v=value: self._submit_answer(v),
                bg_color=(60, 80, 100),
                hover_color=(80, 100, 130),
                width=button_width,
                height=button_height,
            )
            btn.value = value
            self.answer_buttons.append(btn)

    def _start_drill(self) -> None:
        """Start a new deck estimation drill."""
        self._generate_problem()
        self._create_answer_buttons()
        self.selected_answer = None
        self.state = DrillState.SHOWING_DISCARD
        self.problem_display_time = 0.0
        play_sound("card_deal")

    def _generate_problem(self) -> None:
        """Generate a random deck estimation problem."""
        # Cards dealt: between 1 deck and (total - 0.5 deck)
        min_cards = 52  # At least 1 deck dealt
        max_cards = int(self.decks_total * 52 - 26)  # Leave at least half deck

        self.cards_dealt = random.randint(min_cards, max_cards)

        # Calculate exact remaining decks
        cards_remaining = self.decks_total * 52 - self.cards_dealt
        self.decks_remaining = cards_remaining / 52.0

    def _submit_answer(self, value: float) -> None:
        """Submit an answer."""
        if self.state != DrillState.WAITING_INPUT:
            return

        self.selected_answer = value
        self.drills_completed += 1

        # Check if within tolerance
        is_correct = abs(value - self.decks_remaining) <= self.tolerance

        # Update difficulty
        level_change = self.difficulty.record(is_correct)

        # Highlight selected button
        for btn in self.answer_buttons:
            if hasattr(btn, "value"):
                if btn.value == value:
                    if is_correct:
                        btn.bg_color = COLORS.COUNT_POSITIVE
                    else:
                        btn.bg_color = COLORS.COUNT_NEGATIVE
                # Highlight correct answer
                if abs(btn.value - self.decks_remaining) <= 0.25:
                    btn.bg_color = COLORS.GOLD_DARK

        if is_correct:
            self.drills_correct += 1
            self.toast_manager.spawn(
                "CORRECT!",
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 100,
                ToastType.SUCCESS,
                duration=2.0,
            )
            play_sound("win")
        else:
            error = abs(value - self.decks_remaining)
            msg = f"Off by {error:.1f} decks"
            self.toast_manager.spawn(
                msg,
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 100,
                ToastType.ERROR,
                duration=2.0,
            )
            play_sound("lose")

        # Show level change notification
        if level_change:
            self.toast_manager.spawn(
                level_change,
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 60,
                ToastType.INFO,
                duration=2.0,
            )

        self.state = DrillState.SHOWING_RESULT
        self.result_display_time = 0.0

    def _on_back(self) -> None:
        """Handle back button click."""
        self.change_scene("drill_menu", transition=True)

    def _reset_answer_button_colors(self) -> None:
        """Reset answer button colors."""
        for btn in self.answer_buttons:
            btn.bg_color = (60, 80, 100)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        if self.state == DrillState.SETUP:
            # Start button
            if self.start_button and self.start_button.handle_event(event):
                return True
            # Deck buttons
            for btn in self.deck_buttons:
                if btn.handle_event(event):
                    return True

        elif self.state == DrillState.SHOWING_DISCARD:
            # Any key advances to input
            if event.type == pygame.KEYDOWN:
                self.state = DrillState.WAITING_INPUT
                return True

        elif self.state == DrillState.WAITING_INPUT:
            # Answer buttons
            for btn in self.answer_buttons:
                if btn.handle_event(event):
                    return True

            # Number key shortcuts (1-9 for first 9 options)
            if event.type == pygame.KEYDOWN:
                if pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(self.answer_buttons):
                        value = self.answer_buttons[idx].value
                        self._submit_answer(value)
                        return True

        elif self.state == DrillState.SHOWING_RESULT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self._reset_answer_button_colors()
                    self._start_drill()  # Continue to next
                    return True

        # Global shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state != DrillState.SETUP:
                    self._reset_answer_button_colors()
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
        for btn in self.deck_buttons:
            btn.update(dt)
        for btn in self.answer_buttons:
            btn.update(dt)

        # Update toast
        self.toast_manager.update(dt)

        # State updates
        if self.state == DrillState.SHOWING_DISCARD:
            self.problem_display_time += dt
            # Auto-advance after brief display
            if self.problem_display_time >= 1.5:
                self.state = DrillState.WAITING_INPUT

        elif self.state == DrillState.SHOWING_RESULT:
            self.result_display_time += dt
            if self.result_display_time >= 3.0:
                self._reset_answer_button_colors()
                self._start_drill()  # Auto-continue

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.FELT_GREEN)

        # Title
        title = self.title_font.render("DECK ESTIMATION", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 50))
        surface.blit(title, title_rect)

        if self.state == DrillState.SETUP:
            self._draw_setup(surface)
        else:
            self._draw_drill(surface)

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
        # Instructions
        desc = self.label_font.render(
            "Practice estimating remaining decks from the discard tray",
            True, COLORS.TEXT_MUTED
        )
        desc_rect = desc.get_rect(center=(DIMENSIONS.CENTER_X, 120))
        surface.blit(desc, desc_rect)

        # Deck count selection
        deck_label = self.label_font.render("Total Decks:", True, COLORS.TEXT_MUTED)
        surface.blit(deck_label, (DIMENSIONS.CENTER_X - 200, 165))

        for btn in self.deck_buttons:
            btn.draw(surface)

        # Difficulty info
        settings = self.difficulty.settings
        diff_text = f"Difficulty: {settings.name}"
        diff = self.label_font.render(diff_text, True, COLORS.TEXT_MUTED)
        diff_rect = diff.get_rect(center=(DIMENSIONS.CENTER_X, 280))
        surface.blit(diff, diff_rect)

        # Tolerance info
        tol_text = f"Tolerance: ±{self.tolerance} decks"
        tol = self.label_font.render(tol_text, True, COLORS.TEXT_MUTED)
        tol_rect = tol.get_rect(center=(DIMENSIONS.CENTER_X, 320))
        surface.blit(tol, tol_rect)

        # Start button
        if self.start_button:
            self.start_button.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Select deck count and press START DRILL | ESC: Back"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

    def _draw_drill(self, surface: pygame.Surface) -> None:
        """Draw the drill interface."""
        # Draw discard tray and shoe
        self._draw_discard_tray(surface)
        self._draw_shoe(surface)
        self._draw_reference_deck(surface)

        # Question prompt
        if self.state == DrillState.SHOWING_DISCARD:
            prompt = self.label_font.render("Study the shoe and discard...", True, COLORS.TEXT_MUTED)
            prompt_rect = prompt.get_rect(center=(DIMENSIONS.CENTER_X, 480))
            surface.blit(prompt, prompt_rect)

        elif self.state == DrillState.WAITING_INPUT:
            prompt = self.label_font.render("How many decks remain in the shoe?", True, COLORS.GOLD)
            prompt_rect = prompt.get_rect(center=(DIMENSIONS.CENTER_X, 500))
            surface.blit(prompt, prompt_rect)

            # Answer buttons
            for btn in self.answer_buttons:
                btn.draw(surface)

        elif self.state == DrillState.SHOWING_RESULT:
            # Show result
            if self.decks_remaining == int(self.decks_remaining):
                answer_text = f"Actual: {int(self.decks_remaining)} decks remaining"
            else:
                answer_text = f"Actual: {self.decks_remaining:.1f} decks remaining"

            answer = self.value_font.render(answer_text, True, COLORS.GOLD)
            answer_rect = answer.get_rect(center=(DIMENSIONS.CENTER_X, 500))
            surface.blit(answer, answer_rect)

            # Show answer buttons with highlighting
            for btn in self.answer_buttons:
                btn.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        if self.state == DrillState.WAITING_INPUT:
            instructions = "Click or press 1-9 to answer | ESC: Cancel"
        else:
            instructions = "Press ENTER or SPACE to continue"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

    def _draw_discard_tray(self, surface: pygame.Surface) -> None:
        """Draw the discard tray with stacked cards."""
        # Position on left side
        tray_x = 200
        tray_y = 150
        tray_width = 140
        tray_height = 300

        # Draw tray outline
        tray_rect = pygame.Rect(tray_x - 10, tray_y - 10, tray_width + 20, tray_height + 20)
        pygame.draw.rect(surface, (40, 40, 50), tray_rect, border_radius=8)
        pygame.draw.rect(surface, COLORS.TEXT_MUTED, tray_rect, width=2, border_radius=8)

        # Calculate stack height based on cards dealt
        max_height = tray_height - 20
        cards_per_deck = 52
        total_cards = self.decks_total * cards_per_deck

        stack_height = int((self.cards_dealt / total_cards) * max_height)

        # Draw card stack (bottom up)
        if stack_height > 0:
            stack_rect = pygame.Rect(
                tray_x,
                tray_y + tray_height - stack_height - 10,
                tray_width,
                stack_height
            )

            # Gradient effect for stack
            for i in range(stack_height):
                y = stack_rect.bottom - i - 1
                # Alternate colors slightly for layer effect
                if i % 3 == 0:
                    color = (180, 30, 30)  # Red card back
                else:
                    color = (160, 25, 25)

                pygame.draw.line(
                    surface,
                    color,
                    (stack_rect.left + 5, y),
                    (stack_rect.right - 5, y)
                )

            # Draw top card
            top_rect = pygame.Rect(
                tray_x + 5,
                tray_y + tray_height - stack_height - 15,
                tray_width - 10,
                8
            )
            pygame.draw.rect(surface, (200, 35, 35), top_rect, border_radius=2)

        # Label
        label = self.label_font.render("DISCARD", True, COLORS.TEXT_MUTED)
        label_rect = label.get_rect(center=(tray_x + tray_width // 2, tray_y + tray_height + 30))
        surface.blit(label, label_rect)

    def _draw_shoe(self, surface: pygame.Surface) -> None:
        """Draw the shoe with remaining cards."""
        # Position on right side
        shoe_x = DIMENSIONS.SCREEN_WIDTH - 340
        shoe_y = 150
        shoe_width = 140
        shoe_height = 300

        # Draw shoe outline
        shoe_rect = pygame.Rect(shoe_x - 10, shoe_y - 10, shoe_width + 20, shoe_height + 20)
        pygame.draw.rect(surface, (40, 40, 50), shoe_rect, border_radius=8)
        pygame.draw.rect(surface, COLORS.TEXT_MUTED, shoe_rect, width=2, border_radius=8)

        # Calculate remaining stack height
        max_height = shoe_height - 20
        cards_per_deck = 52
        total_cards = self.decks_total * cards_per_deck
        cards_remaining = total_cards - self.cards_dealt

        stack_height = int((cards_remaining / total_cards) * max_height)

        # Draw card stack (bottom up)
        if stack_height > 0:
            stack_rect = pygame.Rect(
                shoe_x,
                shoe_y + shoe_height - stack_height - 10,
                shoe_width,
                stack_height
            )

            # Gradient effect for stack - blue for shoe
            for i in range(stack_height):
                y = stack_rect.bottom - i - 1
                # Alternate colors slightly for layer effect
                if i % 3 == 0:
                    color = (30, 80, 180)  # Blue card back
                else:
                    color = (25, 70, 160)

                pygame.draw.line(
                    surface,
                    color,
                    (stack_rect.left + 5, y),
                    (stack_rect.right - 5, y)
                )

            # Draw top card
            top_rect = pygame.Rect(
                shoe_x + 5,
                shoe_y + shoe_height - stack_height - 15,
                shoe_width - 10,
                8
            )
            pygame.draw.rect(surface, (35, 90, 200), top_rect, border_radius=2)

        # Label
        label = self.label_font.render("SHOE", True, COLORS.TEXT_MUTED)
        label_rect = label.get_rect(center=(shoe_x + shoe_width // 2, shoe_y + shoe_height + 30))
        surface.blit(label, label_rect)

        # Question mark overlay when waiting input
        if self.state == DrillState.WAITING_INPUT:
            question = pygame.font.Font(None, 96).render("?", True, COLORS.GOLD)
            question_rect = question.get_rect(center=(shoe_x + shoe_width // 2, shoe_y + shoe_height // 2))
            surface.blit(question, question_rect)

    def _draw_reference_deck(self, surface: pygame.Surface) -> None:
        """Draw reference showing what 1 deck looks like."""
        # Position in center
        ref_x = DIMENSIONS.CENTER_X - 35
        ref_y = 200
        ref_width = 70
        ref_height = 50  # Height for 1 deck reference

        # Calculate what 1 deck height would be in the display
        max_height = 280  # Same as tray/shoe max
        cards_per_deck = 52
        total_cards = self.decks_total * cards_per_deck
        one_deck_height = int((cards_per_deck / total_cards) * max_height)

        # Draw reference outline
        ref_rect = pygame.Rect(ref_x - 5, ref_y - 5, ref_width + 10, one_deck_height + 10)
        pygame.draw.rect(surface, (50, 50, 60), ref_rect, border_radius=4)
        pygame.draw.rect(surface, COLORS.GOLD, ref_rect, width=2, border_radius=4)

        # Draw stack to show 1 deck
        for i in range(one_deck_height):
            y = ref_y + one_deck_height - i - 1
            if i % 3 == 0:
                color = (100, 100, 100)
            else:
                color = (90, 90, 90)

            pygame.draw.line(
                surface,
                color,
                (ref_x, y),
                (ref_x + ref_width, y)
            )

        # Label
        label = self.label_font.render("= 1 DECK", True, COLORS.GOLD)
        label_rect = label.get_rect(midleft=(ref_x + ref_width + 15, ref_y + one_deck_height // 2))
        surface.blit(label, label_rect)

        # Info text
        info = self.label_font.render(f"({self.decks_total} deck shoe)", True, COLORS.TEXT_MUTED)
        info_rect = info.get_rect(center=(DIMENSIONS.CENTER_X, ref_y + one_deck_height + 40))
        surface.blit(info, info_rect)
