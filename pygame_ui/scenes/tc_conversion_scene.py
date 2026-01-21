"""True Count conversion drill scene for practicing RC to TC conversion."""

import random
from typing import Optional
from enum import Enum, auto

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.toast import ToastManager, ToastType
from pygame_ui.core.sound_manager import play_sound
from pygame_ui.core.difficulty_manager import create_tc_conversion_manager
from pygame_ui.effects.crt_filter import CRTFilter


class DrillState(Enum):
    """States for the TC conversion drill."""
    SETUP = auto()
    SHOWING_PROBLEM = auto()
    WAITING_INPUT = auto()
    SHOWING_RESULT = auto()


class TCConversionScene(BaseScene):
    """Scene for practicing True Count conversion.

    Features:
    - Random running count and decks remaining scenarios
    - Visual deck indicator
    - Difficulty levels (full deck, half deck, quarter deck precision)
    - Formula display on result
    - Progressive difficulty
    """

    def __init__(self):
        super().__init__()

        self.state = DrillState.SETUP

        # Problem parameters
        self.decks_total = 6
        self.decks_remaining = 3.0
        self.running_count = 0
        self.true_count = 0.0
        self.tolerance = 0.5  # Accept answers within this range

        # User input
        self.user_input = ""
        self.input_active = False

        # UI
        self.start_button: Optional[Button] = None
        self.deck_buttons: List[Button] = []
        self.back_button: Optional[Button] = None
        self.toast_manager = ToastManager()

        # Stats
        self.drills_completed = 0
        self.drills_correct = 0

        # Timing
        self.result_display_time = 0.0
        self.problem_display_time = 0.0

        # Progressive difficulty
        self.difficulty = create_tc_conversion_manager()

        # Visual effects
        self.crt_filter = CRTFilter(scanline_alpha=20, vignette_strength=0.2)

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._label_font: Optional[pygame.font.Font] = None
        self._value_font: Optional[pygame.font.Font] = None
        self._input_font: Optional[pygame.font.Font] = None
        self._big_font: Optional[pygame.font.Font] = None

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

    @property
    def input_font(self) -> pygame.font.Font:
        if self._input_font is None:
            self._input_font = pygame.font.Font(None, 48)
        return self._input_font

    @property
    def big_font(self) -> pygame.font.Font:
        if self._big_font is None:
            self._big_font = pygame.font.Font(None, 72)
        return self._big_font

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

    def _start_drill(self) -> None:
        """Start a new TC conversion drill."""
        self._generate_problem()
        self.state = DrillState.SHOWING_PROBLEM
        self.problem_display_time = 0.0
        self.user_input = ""
        play_sound("card_deal")

    def _generate_problem(self) -> None:
        """Generate a random TC conversion problem."""
        settings = self.difficulty.settings

        # Decks remaining based on difficulty precision
        precision = settings.deck_precision
        min_decks = precision
        max_decks = self.decks_total - precision

        # Generate decks remaining
        if precision >= 1.0:
            # Full deck precision
            self.decks_remaining = float(random.randint(
                int(min_decks), int(max_decks)
            ))
        elif precision >= 0.5:
            # Half deck precision
            options = [x * 0.5 for x in range(
                int(min_decks * 2), int(max_decks * 2) + 1
            )]
            self.decks_remaining = random.choice(options) if options else 1.0
        else:
            # Quarter deck precision
            options = [x * 0.25 for x in range(
                int(min_decks * 4), int(max_decks * 4) + 1
            )]
            self.decks_remaining = random.choice(options) if options else 1.0

        # Ensure valid decks remaining
        self.decks_remaining = max(0.25, min(self.decks_total - 0.25, self.decks_remaining))

        # Running count based on difficulty
        rc_range = settings.rc_range
        self.running_count = random.randint(-rc_range, rc_range)

        # Calculate true count
        self.true_count = self.running_count / self.decks_remaining

    def _check_answer(self) -> None:
        """Check the user's answer."""
        try:
            # Handle decimal input
            user_input = self.user_input.replace(",", ".")
            if not user_input or user_input in ["-", "+", "."]:
                user_tc = 0.0
            else:
                user_tc = float(user_input)
        except ValueError:
            user_tc = 0.0

        self.drills_completed += 1

        # Check if within tolerance
        is_correct = abs(user_tc - self.true_count) <= self.tolerance

        # Update difficulty
        level_change = self.difficulty.record(is_correct)

        if is_correct:
            self.drills_correct += 1
            self.toast_manager.spawn(
                "CORRECT!",
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 80,
                ToastType.SUCCESS,
                duration=2.0,
            )
            play_sound("win")
        else:
            self.toast_manager.spawn(
                f"INCORRECT - Answer: {self.true_count:+.1f}",
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 80,
                ToastType.ERROR,
                duration=2.0,
            )
            play_sound("lose")

        # Show level change notification
        if level_change:
            self.toast_manager.spawn(
                level_change,
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 40,
                ToastType.INFO,
                duration=2.0,
            )

        self.state = DrillState.SHOWING_RESULT
        self.result_display_time = 0.0

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
            # Deck buttons
            for btn in self.deck_buttons:
                if btn.handle_event(event):
                    return True

        elif self.state == DrillState.SHOWING_PROBLEM:
            # Any key advances to input
            if event.type == pygame.KEYDOWN:
                self.state = DrillState.WAITING_INPUT
                self.input_active = True
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
                    if not self.user_input:
                        self.user_input = "-"
                    elif self.user_input[0] == "-":
                        self.user_input = self.user_input[1:]
                    else:
                        self.user_input = "-" + self.user_input
                    return True
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    if self.user_input and self.user_input[0] == "-":
                        self.user_input = self.user_input[1:]
                    return True
                elif event.key == pygame.K_PERIOD:
                    if "." not in self.user_input:
                        self.user_input += "."
                    return True
                elif event.unicode.isdigit():
                    self.user_input += event.unicode
                    return True

        elif self.state == DrillState.SHOWING_RESULT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self._start_drill()  # Continue to next
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
        for btn in self.deck_buttons:
            btn.update(dt)

        # Update toast
        self.toast_manager.update(dt)

        # State updates
        if self.state == DrillState.SHOWING_PROBLEM:
            self.problem_display_time += dt
            # Auto-advance after brief display
            if self.problem_display_time >= 1.0:
                self.state = DrillState.WAITING_INPUT
                self.input_active = True

        elif self.state == DrillState.SHOWING_RESULT:
            self.result_display_time += dt
            if self.result_display_time >= 3.0:
                self._start_drill()  # Auto-continue

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.FELT_GREEN)

        # Title
        title = self.title_font.render("TRUE COUNT CONVERSION", True, COLORS.GOLD)
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
            "Practice converting Running Count to True Count",
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

        # Precision info
        if settings.deck_precision >= 1.0:
            prec_text = "Full deck precision"
        elif settings.deck_precision >= 0.5:
            prec_text = "Half deck precision"
        else:
            prec_text = "Quarter deck precision"

        prec = self.label_font.render(prec_text, True, COLORS.TEXT_MUTED)
        prec_rect = prec.get_rect(center=(DIMENSIONS.CENTER_X, 310))
        surface.blit(prec, prec_rect)

        # Formula reminder
        formula = self.label_font.render(
            "TC = Running Count / Decks Remaining",
            True, COLORS.GOLD
        )
        formula_rect = formula.get_rect(center=(DIMENSIONS.CENTER_X, 380))
        surface.blit(formula, formula_rect)

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
        # Running count display
        rc_label = self.label_font.render("RUNNING COUNT", True, COLORS.TEXT_MUTED)
        rc_rect = rc_label.get_rect(center=(DIMENSIONS.CENTER_X, 120))
        surface.blit(rc_label, rc_rect)

        rc_color = COLORS.COUNT_POSITIVE if self.running_count >= 0 else COLORS.COUNT_NEGATIVE
        rc_text = f"{self.running_count:+d}"
        rc = self.big_font.render(rc_text, True, rc_color)
        rc_rect = rc.get_rect(center=(DIMENSIONS.CENTER_X, 170))
        surface.blit(rc, rc_rect)

        # Decks remaining display
        dr_label = self.label_font.render("DECKS REMAINING", True, COLORS.TEXT_MUTED)
        dr_rect = dr_label.get_rect(center=(DIMENSIONS.CENTER_X, 240))
        surface.blit(dr_label, dr_rect)

        # Format decks remaining nicely
        if self.decks_remaining == int(self.decks_remaining):
            dr_text = str(int(self.decks_remaining))
        else:
            dr_text = f"{self.decks_remaining:.2f}".rstrip('0').rstrip('.')

        dr = self.big_font.render(dr_text, True, COLORS.TEXT_WHITE)
        dr_rect = dr.get_rect(center=(DIMENSIONS.CENTER_X, 290))
        surface.blit(dr, dr_rect)

        # Visual deck indicator
        self._draw_deck_indicator(surface)

        if self.state == DrillState.SHOWING_PROBLEM:
            # Show prompt
            prompt = self.label_font.render("Press any key to answer...", True, COLORS.TEXT_MUTED)
            prompt_rect = prompt.get_rect(center=(DIMENSIONS.CENTER_X, 450))
            surface.blit(prompt, prompt_rect)

        elif self.state == DrillState.WAITING_INPUT:
            # Input prompt
            prompt = self.label_font.render("TRUE COUNT = ?", True, COLORS.GOLD)
            prompt_rect = prompt.get_rect(center=(DIMENSIONS.CENTER_X, 420))
            surface.blit(prompt, prompt_rect)

            # Input box
            input_rect = pygame.Rect(
                DIMENSIONS.CENTER_X - 100,
                DIMENSIONS.CENTER_Y + 80,
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
            instructions = "Type your answer and press ENTER | ESC: Cancel"
            text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
            text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
            surface.blit(text, text_rect)

        elif self.state == DrillState.SHOWING_RESULT:
            # Show formula and result
            formula_text = f"TC = {self.running_count:+d} / {dr_text} = {self.true_count:+.1f}"
            formula = self.value_font.render(formula_text, True, COLORS.GOLD)
            formula_rect = formula.get_rect(center=(DIMENSIONS.CENTER_X, 430))
            surface.blit(formula, formula_rect)

            # User answer
            try:
                user_tc = float(self.user_input.replace(",", ".")) if self.user_input else 0.0
            except ValueError:
                user_tc = 0.0

            user_text = f"Your answer: {user_tc:+.1f}"
            user = self.label_font.render(user_text, True, COLORS.TEXT_WHITE)
            user_rect = user.get_rect(center=(DIMENSIONS.CENTER_X, 480))
            surface.blit(user, user_rect)

            # Tolerance info
            tol_text = f"(Tolerance: ±{self.tolerance})"
            tol = self.label_font.render(tol_text, True, COLORS.TEXT_MUTED)
            tol_rect = tol.get_rect(center=(DIMENSIONS.CENTER_X, 510))
            surface.blit(tol, tol_rect)

            # Instructions
            font_small = pygame.font.Font(None, 22)
            instructions = "Press ENTER or SPACE to continue"
            text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
            text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
            surface.blit(text, text_rect)

    def _draw_deck_indicator(self, surface: pygame.Surface) -> None:
        """Draw visual deck indicator showing remaining decks."""
        # Draw on the right side
        indicator_x = DIMENSIONS.CENTER_X + 200
        indicator_y = 200
        deck_height = 20
        deck_width = 60
        spacing = 2

        # Total deck area
        total_height = self.decks_total * (deck_height + spacing) - spacing

        # Draw outline
        outline_rect = pygame.Rect(
            indicator_x - 5,
            indicator_y - 5,
            deck_width + 10,
            total_height + 10
        )
        pygame.draw.rect(surface, COLORS.TEXT_MUTED, outline_rect, width=2, border_radius=4)

        # Draw deck segments
        for i in range(self.decks_total):
            y = indicator_y + i * (deck_height + spacing)
            rect = pygame.Rect(indicator_x, y, deck_width, deck_height)

            # Deck number from bottom (1 = bottom)
            deck_num = self.decks_total - i

            # Color based on remaining
            if deck_num <= self.decks_remaining:
                # Remaining - green gradient
                intensity = int(100 + (deck_num / self.decks_total) * 100)
                color = (60, intensity, 60)
            else:
                # Used/discarded - red/gray
                color = (80, 50, 50)

            pygame.draw.rect(surface, color, rect, border_radius=2)

        # Label
        label = self.label_font.render("Shoe", True, COLORS.TEXT_MUTED)
        label_rect = label.get_rect(center=(indicator_x + deck_width // 2, indicator_y + total_height + 25))
        surface.blit(label, label_rect)


# Required for List typing
from typing import List
