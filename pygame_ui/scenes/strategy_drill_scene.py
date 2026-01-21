"""Strategy drill scene for practicing basic strategy decisions."""

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
from pygame_ui.core.difficulty_manager import create_strategy_drill_manager
from pygame_ui.effects.crt_filter import CRTFilter

from core.cards import Card, Rank, Suit
from core.strategy.basic import BasicStrategy, Action
from core.strategy.deviations import find_deviation, ILLUSTRIOUS_18, FAB_4


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

# Rank values for hand generation
RANK_VALUES = {
    Rank.TWO: 2, Rank.THREE: 3, Rank.FOUR: 4, Rank.FIVE: 5,
    Rank.SIX: 6, Rank.SEVEN: 7, Rank.EIGHT: 8, Rank.NINE: 9,
    Rank.TEN: 10, Rank.JACK: 10, Rank.QUEEN: 10, Rank.KING: 10,
    Rank.ACE: 11,
}


class DrillState(Enum):
    """States for the strategy drill."""
    SETUP = auto()
    WAITING_ANSWER = auto()
    SHOWING_RESULT = auto()


class StrategyDrillScene(BaseScene):
    """Scene for practicing basic strategy decisions.

    Features:
    - Random player hands and dealer upcards
    - Action buttons (Hit, Stand, Double, Split, Surrender)
    - Optional deviation mode with true count
    - Feedback on correct/incorrect answers
    """

    def __init__(self):
        super().__init__()

        self.state = DrillState.SETUP

        # Settings
        self.include_deviations = False
        self.true_count = 0.0

        # Current hand
        self.player_cards: List[Card] = []
        self.dealer_upcard: Optional[Card] = None
        self.player_sprites: List[CardSprite] = []
        self.dealer_sprite: Optional[CardSprite] = None

        # Strategy
        self.strategy = BasicStrategy()
        self.correct_action: Optional[Action] = None
        self.is_deviation = False
        self.deviation_desc = ""

        # UI
        self.action_buttons: List[Button] = []
        self.start_button: Optional[Button] = None
        self.deviation_toggle: Optional[Button] = None
        self.back_button: Optional[Button] = None
        self.toast_manager = ToastManager()

        # Stats
        self.drills_completed = 0
        self.drills_correct = 0

        # Timing
        self.result_display_time = 0.0

        # Progressive difficulty
        self.difficulty = create_strategy_drill_manager()

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

        # Deviation toggle
        self.deviation_toggle = Button(
            x=DIMENSIONS.CENTER_X,
            y=250,
            text="Deviations: OFF",
            font_size=26,
            on_click=self._toggle_deviations,
            bg_color=(60, 80, 100),
            hover_color=(80, 100, 130),
            width=200,
            height=45,
        )

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
            btn.action = action  # Store action for reference
            self.action_buttons.append(btn)

    def _toggle_deviations(self) -> None:
        """Toggle deviation mode."""
        self.include_deviations = not self.include_deviations
        state = "ON" if self.include_deviations else "OFF"
        self.deviation_toggle.text = f"Deviations: {state}"
        self.deviation_toggle.bg_color = COLORS.GOLD_DARK if self.include_deviations else (60, 80, 100)

    def _start_drill(self) -> None:
        """Start a new strategy drill."""
        self._generate_hand()
        self.state = DrillState.WAITING_ANSWER
        play_sound("card_deal")

    def _generate_hand(self) -> None:
        """Generate a random player hand and dealer upcard."""
        # Generate a true count if using deviations
        if self.include_deviations:
            # Generate a TC that might trigger deviations
            self.true_count = random.choice([-3, -2, -1, 0, 1, 2, 3, 4, 5, 6])
        else:
            self.true_count = 0.0

        # Decide hand type: hard (50%), soft (25%), pair (25%)
        hand_type = random.choices(["hard", "soft", "pair"], weights=[50, 25, 25])[0]

        # Generate dealer upcard
        dealer_rank = random.choice(list(Rank))
        dealer_suit = random.choice(list(Suit))
        self.dealer_upcard = Card(dealer_rank, dealer_suit)

        # Generate player cards
        if hand_type == "pair":
            rank = random.choice(list(Rank))
            suits = random.sample(list(Suit), 2)
            self.player_cards = [Card(rank, suits[0]), Card(rank, suits[1])]
        elif hand_type == "soft":
            # One ace + another card (not ace for simplicity)
            other_rank = random.choice([r for r in Rank if r != Rank.ACE])
            suits = random.sample(list(Suit), 2)
            self.player_cards = [Card(Rank.ACE, suits[0]), Card(other_rank, suits[1])]
        else:  # hard
            # Generate two cards that make a hard total (no aces, or aces counted as 1)
            # For simplicity, avoid aces in hard hands
            ranks = [r for r in Rank if r != Rank.ACE]
            rank1 = random.choice(ranks)
            rank2 = random.choice(ranks)
            suits = random.sample(list(Suit), 2)
            self.player_cards = [Card(rank1, suits[0]), Card(rank2, suits[1])]

        # Create card sprites
        self._create_card_sprites()

        # Calculate correct action
        self._calculate_correct_action()

    def _create_card_sprites(self) -> None:
        """Create card sprites for display."""
        # Dealer card
        self.dealer_sprite = CardSprite(
            x=DIMENSIONS.CENTER_X,
            y=180,
            face_up=True,
            card_value=RANK_MAP[self.dealer_upcard.rank],
            card_suit=SUIT_MAP[self.dealer_upcard.suit],
        )

        # Player cards
        self.player_sprites = []
        spacing = 100
        start_x = DIMENSIONS.CENTER_X - spacing / 2

        for i, card in enumerate(self.player_cards):
            sprite = CardSprite(
                x=start_x + i * spacing,
                y=380,
                face_up=True,
                card_value=RANK_MAP[card.rank],
                card_suit=SUIT_MAP[card.suit],
            )
            self.player_sprites.append(sprite)

    def _calculate_correct_action(self) -> None:
        """Calculate the correct action for the current hand."""
        # Calculate hand properties
        is_pair = (len(self.player_cards) == 2 and
                   self.player_cards[0].rank == self.player_cards[1].rank)

        has_ace = any(c.rank == Rank.ACE for c in self.player_cards)

        # Calculate total
        total = sum(RANK_VALUES[c.rank] for c in self.player_cards)
        if total > 21 and has_ace:
            total -= 10  # Count ace as 1

        is_soft = has_ace and total <= 21 and (total - 10 + 1) <= 21

        # Get dealer upcard value
        dealer_value = RANK_VALUES[self.dealer_upcard.rank]

        # Check for deviations first
        self.is_deviation = False
        self.deviation_desc = ""

        if self.include_deviations:
            deviation = find_deviation(
                player_total=total,
                is_soft=is_soft,
                is_pair=is_pair,
                dealer_upcard=dealer_value,
                true_count=self.true_count,
                include_surrender=True,
            )
            if deviation and deviation.should_deviate(self.true_count):
                self.correct_action = deviation.deviation_action
                self.is_deviation = True
                self.deviation_desc = deviation.description
                return

        # Get basic strategy action
        pair_rank = RANK_VALUES[self.player_cards[0].rank] if is_pair else None

        self.correct_action = self.strategy.get_action(
            player_total=total,
            dealer_upcard=dealer_value,
            is_soft=is_soft,
            is_pair=is_pair,
            pair_rank=pair_rank,
            can_double=True,
            can_surrender=True,
            can_split=is_pair,
        )

    def _submit_action(self, action: Action) -> None:
        """Submit an action answer."""
        if self.state != DrillState.WAITING_ANSWER:
            return

        self.drills_completed += 1

        # Check if correct
        is_correct = action == self.correct_action

        # Update difficulty
        level_change = self.difficulty.record(is_correct)

        if is_correct:
            self.drills_correct += 1
            msg = "CORRECT!"
            if self.is_deviation:
                msg += " (Deviation)"
            self.toast_manager.spawn(
                msg,
                DIMENSIONS.CENTER_X,
                DIMENSIONS.CENTER_Y - 30,
                ToastType.SUCCESS,
                duration=2.0,
            )
            play_sound("win")
        else:
            msg = f"INCORRECT - Correct: {self.correct_action.name}"
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
                DIMENSIONS.CENTER_Y + 20,
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
            # Deviation toggle
            if self.deviation_toggle and self.deviation_toggle.handle_event(event):
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
                    self.state = DrillState.SETUP
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
        if self.deviation_toggle:
            self.deviation_toggle.update(dt)
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
            if self.result_display_time >= 2.0:
                self._reset_button_colors()
                self.state = DrillState.SETUP

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.FELT_GREEN)

        # Title
        title = self.title_font.render("STRATEGY DRILL", True, COLORS.GOLD)
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
            "Practice your basic strategy decisions",
            True, COLORS.TEXT_MUTED
        )
        desc_rect = desc.get_rect(center=(DIMENSIONS.CENTER_X, 150))
        surface.blit(desc, desc_rect)

        # Deviation toggle
        if self.deviation_toggle:
            self.deviation_toggle.draw(surface)

        if self.include_deviations:
            dev_desc = self.label_font.render(
                "Includes Illustrious 18 and Fab 4 deviations",
                True, COLORS.GOLD
            )
            dev_rect = dev_desc.get_rect(center=(DIMENSIONS.CENTER_X, 300))
            surface.blit(dev_desc, dev_rect)

        # Difficulty indicator
        diff_text = f"Difficulty: {self.difficulty.settings.name}"
        diff = self.label_font.render(diff_text, True, COLORS.TEXT_MUTED)
        diff_rect = diff.get_rect(center=(DIMENSIONS.CENTER_X, 350))
        surface.blit(diff, diff_rect)

        # Start button
        if self.start_button:
            self.start_button.draw(surface)

        # Instructions
        font_small = pygame.font.Font(None, 22)
        instructions = "Toggle deviations and press START DRILL | ESC: Back"
        text = font_small.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(text, text_rect)

    def _draw_drill(self, surface: pygame.Surface) -> None:
        """Draw the drill interface."""
        # Dealer label
        dealer_label = self.label_font.render("DEALER", True, COLORS.GOLD)
        dealer_rect = dealer_label.get_rect(center=(DIMENSIONS.CENTER_X, 110))
        surface.blit(dealer_label, dealer_rect)

        # Dealer card
        if self.dealer_sprite:
            self.dealer_sprite.draw(surface)

        # Dealer upcard value
        dealer_val = RANK_VALUES[self.dealer_upcard.rank]
        val_text = self.value_font.render(f"({dealer_val})", True, COLORS.TEXT_WHITE)
        val_rect = val_text.get_rect(center=(DIMENSIONS.CENTER_X, 250))
        surface.blit(val_text, val_rect)

        # Player label
        player_label = self.label_font.render("YOUR HAND", True, COLORS.GOLD)
        player_rect = player_label.get_rect(center=(DIMENSIONS.CENTER_X, 300))
        surface.blit(player_label, player_rect)

        # Player cards
        for sprite in self.player_sprites:
            sprite.draw(surface)

        # Player hand value
        total = sum(RANK_VALUES[c.rank] for c in self.player_cards)
        has_ace = any(c.rank == Rank.ACE for c in self.player_cards)
        if total > 21 and has_ace:
            total -= 10
        is_soft = has_ace and total <= 21 and any(c.rank == Rank.ACE for c in self.player_cards)

        prefix = "Soft " if is_soft else ""
        is_pair = (len(self.player_cards) == 2 and
                   self.player_cards[0].rank == self.player_cards[1].rank)
        if is_pair:
            prefix = "Pair of "
            total = RANK_VALUES[self.player_cards[0].rank]

        hand_text = self.value_font.render(f"({prefix}{total})", True, COLORS.TEXT_WHITE)
        hand_rect = hand_text.get_rect(center=(DIMENSIONS.CENTER_X, 460))
        surface.blit(hand_text, hand_rect)

        # True count (if deviation mode)
        if self.include_deviations:
            tc_text = self.value_font.render(f"TC: {self.true_count:+.0f}", True, COLORS.GOLD)
            tc_rect = tc_text.get_rect(center=(DIMENSIONS.CENTER_X, 510))
            surface.blit(tc_text, tc_rect)

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

        # Show deviation description if showing result and it was a deviation
        if self.state == DrillState.SHOWING_RESULT and self.is_deviation:
            dev_text = self.label_font.render(self.deviation_desc, True, COLORS.GOLD)
            dev_rect = dev_text.get_rect(center=(DIMENSIONS.CENTER_X, 560))
            surface.blit(dev_text, dev_rect)
