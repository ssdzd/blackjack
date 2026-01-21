"""Deviation drill scene for practicing Illustrious 18 and Fab 4 deviations."""

import random
from typing import Optional, List, Tuple
from enum import Enum, auto

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.card import CardSprite
from pygame_ui.components.toast import ToastManager, ToastType
from pygame_ui.core.sound_manager import play_sound
from pygame_ui.core.spaced_repetition import get_sr_manager
from pygame_ui.core.difficulty_manager import create_deviation_drill_manager
from pygame_ui.effects.crt_filter import CRTFilter

from core.cards import Rank, Suit
from core.strategy.basic import Action
from core.strategy.deviations import ILLUSTRIOUS_18, FAB_4, IndexPlay


# Map rank values to display strings
VALUE_TO_DISPLAY = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "8", 9: "9", 10: "10", 11: "A",
}

# Rank values for card generation
TOTAL_TO_CARDS = {
    # Hard totals - pairs of cards that make the total
    9: [(2, 7), (3, 6), (4, 5)],
    10: [(2, 8), (3, 7), (4, 6)],
    11: [(2, 9), (3, 8), (4, 7), (5, 6)],
    12: [(2, 10), (3, 9), (4, 8), (5, 7)],
    13: [(3, 10), (4, 9), (5, 8), (6, 7)],
    14: [(4, 10), (5, 9), (6, 8)],
    15: [(5, 10), (6, 9), (7, 8)],
    16: [(6, 10), (7, 9)],
    20: [(10, 10)],  # For pair of 10s
}

# For soft totals: ace + value
SOFT_TOTAL_TO_CARDS = {
    # player_total - 11 gives the second card value
    13: [(11, 2)],  # A + 2
    14: [(11, 3)],
    15: [(11, 4)],
    16: [(11, 5)],
    17: [(11, 6)],
    18: [(11, 7)],
    19: [(11, 8)],
    20: [(11, 9)],
}

# Map for card sprite display
RANK_VALUE_TO_DISPLAY = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "8", 9: "9", 10: "10", 11: "A",
}


class DrillState(Enum):
    """States for the deviation drill."""
    SETUP = auto()
    WAITING_ANSWER = auto()
    SHOWING_RESULT = auto()


class DeviationDrillScene(BaseScene):
    """Scene for practicing Illustrious 18 and Fab 4 deviations.

    Features:
    - Focuses specifically on deviation situations
    - Shows true count at or near index threshold
    - Mode toggle: I18 only / Fab 4 only / Both
    - Spaced repetition for weak spots
    - Progressive difficulty
    """

    def __init__(self):
        super().__init__()

        self.state = DrillState.SETUP

        # Settings
        self.include_i18 = True
        self.include_fab4 = True
        self.use_spaced_repetition = True

        # Get available deviations
        self.all_deviations: List[Tuple[int, IndexPlay]] = []
        self._refresh_deviation_list()

        # Current drill
        self.current_deviation: Optional[IndexPlay] = None
        self.current_deviation_index: int = 0
        self.true_count: float = 0.0
        self.correct_action: Optional[Action] = None
        self.should_deviate: bool = False

        # Card display
        self.player_sprites: List[CardSprite] = []
        self.dealer_sprite: Optional[CardSprite] = None

        # UI
        self.action_buttons: List[Button] = []
        self.start_button: Optional[Button] = None
        self.mode_buttons: List[Button] = []
        self.back_button: Optional[Button] = None
        self.toast_manager = ToastManager()

        # Stats
        self.drills_completed = 0
        self.drills_correct = 0

        # Timing
        self.result_display_time = 0.0

        # Progressive difficulty
        self.difficulty = create_deviation_drill_manager()

        # Visual effects
        self.crt_filter = CRTFilter(scanline_alpha=20, vignette_strength=0.2)

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._label_font: Optional[pygame.font.Font] = None
        self._value_font: Optional[pygame.font.Font] = None
        self._tc_font: Optional[pygame.font.Font] = None

    def _refresh_deviation_list(self) -> None:
        """Refresh the list of available deviations based on settings."""
        self.all_deviations = []

        if self.include_i18:
            for i, play in enumerate(ILLUSTRIOUS_18):
                # Skip insurance (index 0) - special case
                if play.player_total == 0:
                    continue
                self.all_deviations.append((i, play))

        if self.include_fab4:
            for i, play in enumerate(FAB_4):
                self.all_deviations.append((len(ILLUSTRIOUS_18) + i, play))

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
    def tc_font(self) -> pygame.font.Font:
        if self._tc_font is None:
            self._tc_font = pygame.font.Font(None, 64)
        return self._tc_font

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

        # Mode selection buttons
        mode_y = 200
        modes = [
            ("I18 Only", "i18"),
            ("Fab 4 Only", "fab4"),
            ("Both", "both"),
        ]
        total_width = len(modes) * 150
        start_x = DIMENSIONS.CENTER_X - total_width / 2 + 75

        self.mode_buttons = []
        for i, (label, mode) in enumerate(modes):
            is_selected = (
                (mode == "both" and self.include_i18 and self.include_fab4) or
                (mode == "i18" and self.include_i18 and not self.include_fab4) or
                (mode == "fab4" and not self.include_i18 and self.include_fab4)
            )
            btn = Button(
                x=start_x + i * 150,
                y=mode_y,
                text=label,
                font_size=24,
                on_click=lambda m=mode: self._select_mode(m),
                bg_color=COLORS.GOLD_DARK if is_selected else (60, 80, 100),
                hover_color=(80, 100, 130),
                width=140,
                height=40,
            )
            self.mode_buttons.append(btn)

        # Action buttons (positioned at bottom during drill)
        button_y = DIMENSIONS.SCREEN_HEIGHT - 120
        button_spacing = 130

        actions = [
            ("HIT", Action.HIT, (60, 100, 60), "H"),
            ("STAND", Action.STAND, (100, 100, 100), "S"),
            ("DOUBLE", Action.DOUBLE, (60, 80, 120), "D"),
            ("SPLIT", Action.SPLIT, (120, 100, 60), "P"),
            ("SURRENDER", Action.SURRENDER, (120, 60, 60), "R"),
        ]

        total_width = len(actions) * button_spacing
        start_x = DIMENSIONS.CENTER_X - total_width / 2 + button_spacing / 2

        self.action_buttons = []
        for i, (text, action, color, hotkey) in enumerate(actions):
            btn = Button(
                x=start_x + i * button_spacing,
                y=button_y,
                text=text,
                font_size=24,
                on_click=lambda a=action: self._submit_action(a),
                bg_color=color,
                hover_color=tuple(min(c + 30, 255) for c in color),
                width=110,
                height=45,
            )
            btn.action = action
            self.action_buttons.append(btn)

    def _select_mode(self, mode: str) -> None:
        """Select deviation mode."""
        if mode == "i18":
            self.include_i18 = True
            self.include_fab4 = False
        elif mode == "fab4":
            self.include_i18 = False
            self.include_fab4 = True
        else:  # both
            self.include_i18 = True
            self.include_fab4 = True

        self._refresh_deviation_list()
        self._update_mode_button_colors()

    def _update_mode_button_colors(self) -> None:
        """Update mode button colors based on selection."""
        modes = ["i18", "fab4", "both"]
        for i, btn in enumerate(self.mode_buttons):
            mode = modes[i]
            is_selected = (
                (mode == "both" and self.include_i18 and self.include_fab4) or
                (mode == "i18" and self.include_i18 and not self.include_fab4) or
                (mode == "fab4" and not self.include_i18 and self.include_fab4)
            )
            btn.bg_color = COLORS.GOLD_DARK if is_selected else (60, 80, 100)

    def _start_drill(self) -> None:
        """Start a new deviation drill."""
        if not self.all_deviations:
            return

        self._generate_scenario()
        self.state = DrillState.WAITING_ANSWER
        play_sound("card_deal")

    def _generate_scenario(self) -> None:
        """Generate a deviation scenario."""
        # Use spaced repetition to pick next item
        if self.use_spaced_repetition and self.all_deviations:
            sr_manager = get_sr_manager()
            keys = [f"deviation_{idx}" for idx, _ in self.all_deviations]
            next_key = sr_manager.get_next_item(keys)

            if next_key:
                # Extract index from key
                idx = int(next_key.split("_")[1])
                # Find the deviation with this index
                for i, (dev_idx, play) in enumerate(self.all_deviations):
                    if dev_idx == idx:
                        self.current_deviation_index = dev_idx
                        self.current_deviation = play
                        break
                else:
                    # Fallback to random
                    self.current_deviation_index, self.current_deviation = random.choice(
                        self.all_deviations
                    )
            else:
                self.current_deviation_index, self.current_deviation = random.choice(
                    self.all_deviations
                )
        else:
            self.current_deviation_index, self.current_deviation = random.choice(
                self.all_deviations
            )

        play = self.current_deviation

        # Generate true count near the threshold
        # Randomly at, above, or below the index
        offset = random.choice([-1, -0.5, 0, 0.5, 1, 1.5, 2])

        if play.direction == "at_or_above":
            self.true_count = play.index + offset
        else:  # at_or_below
            self.true_count = play.index - offset

        # Determine correct action
        self.should_deviate = play.should_deviate(self.true_count)
        if self.should_deviate:
            self.correct_action = play.deviation_action
        else:
            self.correct_action = play.basic_action

        # Generate cards for display
        self._generate_cards()

    def _generate_cards(self) -> None:
        """Generate card sprites for the current scenario."""
        play = self.current_deviation

        # Generate dealer card
        dealer_value = play.dealer_upcard
        dealer_display = RANK_VALUE_TO_DISPLAY.get(dealer_value, str(dealer_value))
        dealer_suit = random.choice(["hearts", "diamonds", "clubs", "spades"])

        self.dealer_sprite = CardSprite(
            x=DIMENSIONS.CENTER_X,
            y=180,
            face_up=True,
            card_value=dealer_display,
            card_suit=dealer_suit,
        )

        # Generate player cards
        self.player_sprites = []
        suits = ["hearts", "diamonds", "clubs", "spades"]
        random.shuffle(suits)

        if play.is_pair:
            # Pair hand - two cards of same value
            pair_value = play.player_total // 2
            display_val = RANK_VALUE_TO_DISPLAY.get(pair_value, str(pair_value))
            # For 10-value pairs, use random 10/J/Q/K
            if pair_value == 10:
                display_val = random.choice(["10", "J", "Q", "K"])

            for i in range(2):
                sprite = CardSprite(
                    x=DIMENSIONS.CENTER_X - 50 + i * 100,
                    y=380,
                    face_up=True,
                    card_value=display_val,
                    card_suit=suits[i],
                )
                self.player_sprites.append(sprite)

        elif play.is_soft:
            # Soft hand - one ace + another card
            other_value = play.player_total - 11
            ace_sprite = CardSprite(
                x=DIMENSIONS.CENTER_X - 50,
                y=380,
                face_up=True,
                card_value="A",
                card_suit=suits[0],
            )
            other_display = RANK_VALUE_TO_DISPLAY.get(other_value, str(other_value))
            other_sprite = CardSprite(
                x=DIMENSIONS.CENTER_X + 50,
                y=380,
                face_up=True,
                card_value=other_display,
                card_suit=suits[1],
            )
            self.player_sprites = [ace_sprite, other_sprite]

        else:
            # Hard hand
            total = play.player_total
            if total in TOTAL_TO_CARDS:
                card1, card2 = random.choice(TOTAL_TO_CARDS[total])
            else:
                # Fallback - make something reasonable
                card1 = min(10, total - 2)
                card2 = total - card1

            display1 = RANK_VALUE_TO_DISPLAY.get(card1, str(card1))
            display2 = RANK_VALUE_TO_DISPLAY.get(card2, str(card2))

            # For 10-value cards, randomize display
            if card1 == 10:
                display1 = random.choice(["10", "J", "Q", "K"])
            if card2 == 10:
                display2 = random.choice(["10", "J", "Q", "K"])

            sprite1 = CardSprite(
                x=DIMENSIONS.CENTER_X - 50,
                y=380,
                face_up=True,
                card_value=display1,
                card_suit=suits[0],
            )
            sprite2 = CardSprite(
                x=DIMENSIONS.CENTER_X + 50,
                y=380,
                face_up=True,
                card_value=display2,
                card_suit=suits[1],
            )
            self.player_sprites = [sprite1, sprite2]

    def _submit_action(self, action: Action) -> None:
        """Submit an action answer."""
        if self.state != DrillState.WAITING_ANSWER:
            return

        self.drills_completed += 1
        is_correct = action == self.correct_action

        # Update spaced repetition
        if self.use_spaced_repetition:
            sr_manager = get_sr_manager()
            key = f"deviation_{self.current_deviation_index}"
            if is_correct:
                sr_manager.record_correct(key)
            else:
                sr_manager.record_incorrect(key)

        # Update difficulty
        level_change = self.difficulty.record(is_correct)

        if is_correct:
            self.drills_correct += 1
            msg = "CORRECT!"
            if self.should_deviate:
                msg += " (Deviate)"
            else:
                msg += " (Basic)"
            self.toast_manager.spawn(
                msg,
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 30,
                ToastType.SUCCESS,
                duration=2.0,
            )
            play_sound("win")
        else:
            msg = f"INCORRECT - {self.correct_action.name}"
            self.toast_manager.spawn(
                msg,
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 30,
                ToastType.ERROR,
                duration=2.0,
            )
            play_sound("lose")

        # Show level change notification
        if level_change:
            self.toast_manager.spawn(
                level_change,
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y + 30,
                ToastType.INFO,
                duration=2.0,
            )

        # Highlight buttons
        for btn in self.action_buttons:
            if hasattr(btn, "action"):
                if btn.action == self.correct_action:
                    btn.bg_color = COLORS.COUNT_POSITIVE
                elif btn.action == action and not is_correct:
                    btn.bg_color = COLORS.COUNT_NEGATIVE

        self.state = DrillState.SHOWING_RESULT
        self.result_display_time = 0.0

    def _on_back(self) -> None:
        """Handle back button click."""
        self.change_scene("drill_menu", transition=True)

    def _reset_button_colors(self) -> None:
        """Reset action button colors."""
        colors = [
            (60, 100, 60),   # HIT
            (100, 100, 100), # STAND
            (60, 80, 120),   # DOUBLE
            (120, 100, 60),  # SPLIT
            (120, 60, 60),   # SURRENDER
        ]
        for i, btn in enumerate(self.action_buttons):
            btn.bg_color = colors[i]

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        if self.state == DrillState.SETUP:
            # Start button
            if self.start_button and self.start_button.handle_event(event):
                return True
            # Mode buttons
            for btn in self.mode_buttons:
                if btn.handle_event(event):
                    return True

        elif self.state == DrillState.WAITING_ANSWER:
            # Action buttons
            for btn in self.action_buttons:
                if btn.handle_event(event):
                    return True

            # Keyboard shortcuts
            if event.type == pygame.KEYDOWN:
                shortcuts = {
                    pygame.K_h: Action.HIT,
                    pygame.K_s: Action.STAND,
                    pygame.K_d: Action.DOUBLE,
                    pygame.K_p: Action.SPLIT,
                    pygame.K_r: Action.SURRENDER,
                }
                if event.key in shortcuts:
                    self._submit_action(shortcuts[event.key])
                    return True

        elif self.state == DrillState.SHOWING_RESULT:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self._reset_button_colors()
                    self._start_drill()  # Continue to next
                    return True

        # Global shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state != DrillState.SETUP:
                    self._reset_button_colors()
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
        for btn in self.mode_buttons:
            btn.update(dt)
        for btn in self.action_buttons:
            btn.update(dt)

        # Update card sprites
        if self.dealer_sprite:
            self.dealer_sprite.update(dt)
        for sprite in self.player_sprites:
            sprite.update(dt)

        # Update toast
        self.toast_manager.update(dt)

        # State updates
        if self.state == DrillState.SHOWING_RESULT:
            self.result_display_time += dt
            if self.result_display_time >= 2.5:
                self._reset_button_colors()
                self._start_drill()  # Auto-continue

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.FELT_GREEN)

        # Title
        title = self.title_font.render("DEVIATION DRILL", True, COLORS.GOLD)
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
            "Practice Illustrious 18 and Fab 4 deviations",
            True, COLORS.TEXT_MUTED
        )
        desc_rect = desc.get_rect(center=(DIMENSIONS.CENTER_X, 120))
        surface.blit(desc, desc_rect)

        # Mode label
        mode_label = self.label_font.render("Deviation Set:", True, COLORS.TEXT_MUTED)
        surface.blit(mode_label, (DIMENSIONS.CENTER_X - 220, 165))

        # Mode buttons
        for btn in self.mode_buttons:
            btn.draw(surface)

        # Info about selected mode
        count = len(self.all_deviations)
        mode_info = f"{count} deviations available"
        info = self.label_font.render(mode_info, True, COLORS.GOLD)
        info_rect = info.get_rect(center=(DIMENSIONS.CENTER_X, 260))
        surface.blit(info, info_rect)

        # Spaced repetition status
        if self.use_spaced_repetition:
            sr_manager = get_sr_manager()
            keys = [f"deviation_{idx}" for idx, _ in self.all_deviations]
            due_count = sr_manager.get_due_count(keys)
            sr_text = f"Spaced Repetition: {due_count} due for review"
            sr = self.label_font.render(sr_text, True, COLORS.TEXT_MUTED)
            sr_rect = sr.get_rect(center=(DIMENSIONS.CENTER_X, 300))
            surface.blit(sr, sr_rect)

        # Difficulty level
        diff_text = f"Difficulty: {self.difficulty.settings.name}"
        diff = self.label_font.render(diff_text, True, COLORS.TEXT_MUTED)
        diff_rect = diff.get_rect(center=(DIMENSIONS.CENTER_X, 340))
        surface.blit(diff, diff_rect)

        # Start button
        if self.start_button:
            self.start_button.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Select mode and press START DRILL | H/S/D/P/R: Answer | ESC: Back"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

    def _draw_drill(self, surface: pygame.Surface) -> None:
        """Draw the drill interface."""
        play = self.current_deviation

        # True Count - prominent display
        tc_color = COLORS.COUNT_POSITIVE if self.true_count >= 0 else COLORS.COUNT_NEGATIVE
        tc_text = f"TC: {self.true_count:+.1f}"
        tc = self.tc_font.render(tc_text, True, tc_color)
        tc_rect = tc.get_rect(center=(DIMENSIONS.CENTER_X, 95))
        surface.blit(tc, tc_rect)

        # Dealer label
        dealer_label = self.label_font.render("DEALER", True, COLORS.GOLD)
        dealer_rect = dealer_label.get_rect(center=(DIMENSIONS.CENTER_X, 130))
        surface.blit(dealer_label, dealer_rect)

        # Dealer card
        if self.dealer_sprite:
            self.dealer_sprite.draw(surface)

        # Dealer upcard value
        dealer_val = play.dealer_upcard
        dealer_display = "A" if dealer_val == 11 else str(dealer_val)
        val_text = self.value_font.render(f"({dealer_display})", True, COLORS.TEXT_WHITE)
        val_rect = val_text.get_rect(center=(DIMENSIONS.CENTER_X, 250))
        surface.blit(val_text, val_rect)

        # Player label
        player_label = self.label_font.render("YOUR HAND", True, COLORS.GOLD)
        player_rect = player_label.get_rect(center=(DIMENSIONS.CENTER_X, 300))
        surface.blit(player_label, player_rect)

        # Player cards
        for sprite in self.player_sprites:
            sprite.draw(surface)

        # Player hand description
        if play.is_pair:
            hand_desc = f"Pair of {play.player_total // 2}s"
        elif play.is_soft:
            hand_desc = f"Soft {play.player_total}"
        else:
            hand_desc = f"Hard {play.player_total}"

        hand_text = self.value_font.render(f"({hand_desc})", True, COLORS.TEXT_WHITE)
        hand_rect = hand_text.get_rect(center=(DIMENSIONS.CENTER_X, 460))
        surface.blit(hand_text, hand_rect)

        # Index threshold hint (based on difficulty)
        if self.difficulty.settings.show_tc_hint:
            direction = ">=" if play.direction == "at_or_above" else "<="
            hint_text = f"Index: {direction} {play.index:+.0f}"
            hint = self.label_font.render(hint_text, True, COLORS.TEXT_MUTED)
            hint_rect = hint.get_rect(center=(DIMENSIONS.CENTER_X, 500))
            surface.blit(hint, hint_rect)

        # Action buttons
        for btn in self.action_buttons:
            btn.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        if self.state == DrillState.WAITING_ANSWER:
            instructions = "H/S/D/P/R: Select action | ESC: Cancel"
        else:
            instructions = "Press ENTER or SPACE to continue"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

        # Show deviation description if showing result
        if self.state == DrillState.SHOWING_RESULT:
            desc_text = play.description
            desc = self.label_font.render(desc_text, True, COLORS.GOLD)
            desc_rect = desc.get_rect(center=(DIMENSIONS.CENTER_X, 540))
            surface.blit(desc, desc_rect)

            # Show what the correct play was
            if self.should_deviate:
                action_text = f"Correct: DEVIATE to {self.correct_action.name}"
            else:
                action_text = f"Correct: BASIC STRATEGY ({self.correct_action.name})"
            action = self.label_font.render(action_text, True, COLORS.TEXT_WHITE)
            action_rect = action.get_rect(center=(DIMENSIONS.CENTER_X, 570))
            surface.blit(action, action_rect)
