"""Simulation scene for auto-playing hands with basic strategy."""

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from decimal import Decimal
from typing import List, Optional, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.panel import Panel
from pygame_ui.components.progress_bar import SimpleProgressBar
from pygame_ui.effects.crt_filter import CRTFilter
from pygame_ui.core.sound_manager import play_sound
from pygame_ui.core.game_settings import get_settings_manager

from core.cards import Card, Shoe
from core.hand import Hand, evaluate_hands
from core.strategy.basic import BasicStrategy, Action
from core.strategy.rules import RuleSet
from core.counting.hilo import HiLoSystem


class SimState(Enum):
    """Simulation states."""

    SETUP = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETE = auto()


@dataclass
class SimulationConfig:
    """Simulation configuration."""

    num_hands: int = 1000
    initial_bankroll: int = 10000
    base_bet: int = 10
    use_counting: bool = True
    bet_spread: int = 8  # 1-8 spread with counting
    speed: int = 100  # Hands per second


@dataclass
class SimulationStats:
    """Statistics from simulation."""

    hands_played: int = 0
    hands_won: int = 0
    hands_lost: int = 0
    hands_pushed: int = 0
    blackjacks: int = 0
    doubles_won: int = 0
    doubles_lost: int = 0
    splits: int = 0
    surrenders: int = 0
    total_wagered: float = 0.0
    total_won: float = 0.0
    peak_bankroll: float = 0.0
    low_bankroll: float = 0.0
    bankroll_history: List[float] = field(default_factory=list)

    @property
    def net_profit(self) -> float:
        return self.total_won - self.total_wagered

    @property
    def win_rate(self) -> float:
        total = self.hands_won + self.hands_lost
        return (self.hands_won / total * 100) if total > 0 else 0.0

    @property
    def house_edge(self) -> float:
        if self.total_wagered == 0:
            return 0.0
        return (self.total_wagered - self.total_won) / self.total_wagered * 100

    @property
    def ev_per_hand(self) -> float:
        if self.hands_played == 0:
            return 0.0
        return self.net_profit / self.hands_played


class SimulationEngine:
    """Engine for running blackjack simulations."""

    def __init__(self, config: SimulationConfig, rules: RuleSet):
        self.config = config
        self.rules = rules
        self.stats = SimulationStats()

        # Game components
        self.shoe = Shoe(num_decks=rules.num_decks, penetration=0.75)
        self.shoe.shuffle()
        self.counter = HiLoSystem() if config.use_counting else None
        self.strategy = BasicStrategy()

        # Current state
        self.bankroll = float(config.initial_bankroll)
        self.stats.peak_bankroll = self.bankroll
        self.stats.low_bankroll = self.bankroll
        self.stats.bankroll_history.append(self.bankroll)

    def get_bet_amount(self) -> int:
        """Calculate bet based on count and spread."""
        if not self.config.use_counting or self.counter is None:
            return self.config.base_bet

        tc = self.counter.true_count(self.shoe.decks_remaining)

        # Bet ramp: TC <= 1: 1 unit, TC 2: 2 units, ... TC >= spread: max units
        if tc <= 1:
            multiplier = 1
        else:
            multiplier = min(int(tc), self.config.bet_spread)

        return self.config.base_bet * multiplier

    def play_hand(self) -> None:
        """Play a single hand using perfect basic strategy."""
        # Check for shuffle
        if self.shoe.needs_shuffle:
            self.shoe.shuffle()
            if self.counter:
                self.counter.reset()

        # Place bet
        bet = self.get_bet_amount()
        if bet > self.bankroll:
            bet = int(self.bankroll)
        if bet <= 0:
            return

        self.stats.total_wagered += bet

        # Deal cards
        player_hand = Hand(bet=bet)
        dealer_hand = Hand()

        player_hand.add_card(self._deal_card())
        dealer_hand.add_card(self._deal_card())
        player_hand.add_card(self._deal_card())
        dealer_hole = self.shoe.draw()  # Dealer hole card (not counted yet)
        dealer_hand.add_card(dealer_hole)

        # Check for player blackjack
        if player_hand.is_blackjack:
            self.stats.blackjacks += 1
            # Dealer doesn't have blackjack (simplified)
            if not dealer_hand.is_blackjack:
                winnings = bet * self.rules.blackjack_payout
                self.bankroll += winnings
                self.stats.total_won += bet + winnings
                self.stats.hands_won += 1
            else:
                # Push
                self.stats.total_won += bet
                self.stats.hands_pushed += 1
            self._count_card(dealer_hole)
            self._record_bankroll()
            self.stats.hands_played += 1
            return

        # Player turn
        hands = [player_hand]
        hand_index = 0

        while hand_index < len(hands):
            current_hand = hands[hand_index]

            while not current_hand.is_busted and not current_hand.is_doubled:
                action = self._get_best_action(current_hand, dealer_hand.cards[0])

                if action == Action.HIT:
                    current_hand.add_card(self._deal_card())
                elif action == Action.STAND:
                    break
                elif action == Action.DOUBLE:
                    if len(current_hand.cards) == 2 and current_hand.bet <= self.bankroll:
                        self.stats.total_wagered += current_hand.bet
                        current_hand.bet *= 2
                        current_hand.is_doubled = True
                        current_hand.add_card(self._deal_card())
                    else:
                        # Can't double, hit instead
                        current_hand.add_card(self._deal_card())
                elif action == Action.SPLIT:
                    if len(current_hand.cards) == 2 and current_hand.is_pair:
                        if current_hand.bet <= self.bankroll and len(hands) < 4:
                            self.stats.splits += 1
                            self.stats.total_wagered += current_hand.bet
                            # Create new hand
                            second_card = current_hand.cards.pop()
                            new_hand = Hand(bet=current_hand.bet)
                            new_hand.add_card(second_card)
                            new_hand.is_split_hand = True
                            current_hand.is_split_hand = True
                            # Deal to each hand
                            current_hand.add_card(self._deal_card())
                            new_hand.add_card(self._deal_card())
                            hands.append(new_hand)
                            continue
                    # Can't split, use next best action
                    current_hand.add_card(self._deal_card())
                elif action == Action.SURRENDER:
                    if len(current_hand.cards) == 2 and not current_hand.is_split_hand:
                        self.stats.surrenders += 1
                        self.stats.total_won += current_hand.bet / 2
                        self.bankroll -= current_hand.bet / 2
                        current_hand.is_surrendered = True
                        break
                    else:
                        current_hand.add_card(self._deal_card())

            hand_index += 1

        # Count the hole card
        self._count_card(dealer_hole)

        # Check if all hands busted or surrendered
        all_done = all(h.is_busted or h.is_surrendered for h in hands)
        if all_done:
            for hand in hands:
                if hand.is_busted:
                    self.stats.hands_lost += 1
                    if hand.is_doubled:
                        self.stats.doubles_lost += 1
            self.stats.hands_played += 1
            self._record_bankroll()
            return

        # Dealer turn
        while self._dealer_should_hit(dealer_hand):
            dealer_hand.add_card(self._deal_card())

        # Resolve hands
        for hand in hands:
            if hand.is_surrendered or hand.is_busted:
                continue

            outcome = evaluate_hands(hand, dealer_hand)
            if outcome == 1:  # Win
                self.stats.hands_won += 1
                self.stats.total_won += hand.bet * 2
                self.bankroll += hand.bet
                if hand.is_doubled:
                    self.stats.doubles_won += 1
            elif outcome == -1:  # Lose
                self.stats.hands_lost += 1
                self.bankroll -= hand.bet
                if hand.is_doubled:
                    self.stats.doubles_lost += 1
            else:  # Push
                self.stats.hands_pushed += 1
                self.stats.total_won += hand.bet

        self.stats.hands_played += 1
        self._record_bankroll()

    def _deal_card(self) -> Card:
        """Deal and count a card."""
        card = self.shoe.draw()
        self._count_card(card)
        return card

    def _count_card(self, card: Card) -> None:
        """Count a card if counting is enabled."""
        if self.counter:
            self.counter.count_card(card)

    def _get_best_action(self, hand: Hand, dealer_upcard: Card) -> Action:
        """Get the best action using basic strategy."""
        dealer_value = 11 if dealer_upcard.is_ace else (10 if dealer_upcard.is_ten else dealer_upcard.rank.value)

        # Check for pair
        is_pair = hand.is_pair
        pair_rank = None
        if is_pair:
            card = hand.cards[0]
            pair_rank = 11 if card.is_ace else (10 if card.is_ten else card.rank.value)

        return self.strategy.get_action(
            player_total=hand.value,
            dealer_upcard=dealer_value,
            is_soft=hand.is_soft,
            is_pair=is_pair,
            pair_rank=pair_rank,
            can_double=len(hand.cards) == 2,
            can_surrender=len(hand.cards) == 2 and not hand.is_split_hand,
            can_split=is_pair and len(hand.cards) == 2,
        )

    def _dealer_should_hit(self, hand: Hand) -> bool:
        """Determine if dealer should hit."""
        if hand.value < 17:
            return True
        if hand.value == 17 and hand.is_soft and self.rules.dealer_hits_soft_17:
            return True
        return False

    def _record_bankroll(self) -> None:
        """Record bankroll for history."""
        self.stats.peak_bankroll = max(self.stats.peak_bankroll, self.bankroll)
        self.stats.low_bankroll = min(self.stats.low_bankroll, self.bankroll)
        # Sample every N hands to keep history manageable
        sample_rate = max(1, self.config.num_hands // 200)
        if self.stats.hands_played % sample_rate == 0:
            self.stats.bankroll_history.append(self.bankroll)


class SimulationScene(BaseScene):
    """Scene for running blackjack simulations."""

    def __init__(self):
        super().__init__()

        self.crt_filter = CRTFilter(
            scanline_alpha=25,
            vignette_strength=0.25,
            enabled=True,
        )

        # State
        self.state = SimState.SETUP
        self.config = SimulationConfig()
        self.engine: Optional[SimulationEngine] = None

        # UI components
        self.panel: Optional[Panel] = None
        self.start_button: Optional[Button] = None
        self.pause_button: Optional[Button] = None
        self.back_button: Optional[Button] = None
        self.progress_bar: Optional[SimpleProgressBar] = None

        # Config buttons
        self.config_buttons: List[Button] = []

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._font: Optional[pygame.font.Font] = None
        self._small_font: Optional[pygame.font.Font] = None

        # Animation
        self._hands_per_frame = 10
        self._time_accumulator = 0.0

    def _init_fonts(self) -> None:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 48)
            self._font = pygame.font.Font(None, 32)
            self._small_font = pygame.font.Font(None, 24)

    def on_enter(self) -> None:
        super().on_enter()
        self._init_fonts()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        center_x = DIMENSIONS.CENTER_X

        # Panel
        self.panel = Panel(
            x=center_x,
            y=DIMENSIONS.CENTER_Y,
            width=700,
            height=450,
        )

        # Progress bar
        self.progress_bar = SimpleProgressBar(
            x=center_x,
            y=DIMENSIONS.CENTER_Y + 140,
            width=500,
            height=24,
        )

        # Start button
        self.start_button = Button(
            x=center_x - 120,
            y=DIMENSIONS.SCREEN_HEIGHT - 100,
            text="START",
            font_size=32,
            on_click=self._start_simulation,
            bg_color=(60, 100, 60),
            hover_color=(80, 130, 80),
            width=150,
            height=50,
        )

        # Pause button
        self.pause_button = Button(
            x=center_x,
            y=DIMENSIONS.SCREEN_HEIGHT - 100,
            text="PAUSE",
            font_size=32,
            on_click=self._toggle_pause,
            bg_color=(100, 100, 60),
            hover_color=(130, 130, 80),
            width=150,
            height=50,
        )
        self.pause_button.set_enabled(False)

        # Back button
        self.back_button = Button(
            x=center_x + 120,
            y=DIMENSIONS.SCREEN_HEIGHT - 100,
            text="BACK",
            font_size=32,
            on_click=self._go_back,
            bg_color=(100, 60, 60),
            hover_color=(130, 80, 80),
            width=150,
            height=50,
        )

        self._setup_config_buttons()

    def _setup_config_buttons(self) -> None:
        """Setup configuration buttons."""
        center_x = DIMENSIONS.CENTER_X
        start_y = DIMENSIONS.CENTER_Y - 120

        # Number of hands options
        hands_options = [100, 1000, 10000, 100000]
        hands_buttons = []
        for i, num in enumerate(hands_options):
            btn = Button(
                x=center_x - 150 + i * 100,
                y=start_y,
                text=f"{num:,}" if num < 10000 else f"{num // 1000}k",
                font_size=24,
                on_click=lambda n=num: self._set_num_hands(n),
                bg_color=(50, 70, 50) if num == self.config.num_hands else (40, 40, 45),
                hover_color=(70, 100, 70),
                width=90,
                height=36,
            )
            hands_buttons.append(btn)

        # Counting toggle
        counting_btn = Button(
            x=center_x - 100,
            y=start_y + 50,
            text="Count: ON" if self.config.use_counting else "Count: OFF",
            font_size=24,
            on_click=self._toggle_counting,
            bg_color=(60, 80, 60) if self.config.use_counting else (60, 60, 60),
            hover_color=(80, 110, 80),
            width=140,
            height=36,
        )

        # Bet spread options
        spread_btn = Button(
            x=center_x + 100,
            y=start_y + 50,
            text=f"Spread: 1-{self.config.bet_spread}",
            font_size=24,
            on_click=self._cycle_spread,
            bg_color=(50, 70, 80),
            hover_color=(70, 100, 110),
            width=140,
            height=36,
        )

        # Speed options
        speed_options = [10, 100, 1000, 10000]
        speed_buttons = []
        for i, spd in enumerate(speed_options):
            label = f"{spd}/s" if spd < 1000 else f"{spd // 1000}k/s"
            btn = Button(
                x=center_x - 150 + i * 100,
                y=start_y + 100,
                text=label,
                font_size=24,
                on_click=lambda s=spd: self._set_speed(s),
                bg_color=(50, 50, 70) if spd == self.config.speed else (40, 40, 45),
                hover_color=(70, 70, 100),
                width=90,
                height=36,
            )
            speed_buttons.append(btn)

        self.config_buttons = hands_buttons + [counting_btn, spread_btn] + speed_buttons

    def _set_num_hands(self, num: int) -> None:
        self.config.num_hands = num
        play_sound("button_click")
        self._setup_config_buttons()

    def _toggle_counting(self) -> None:
        self.config.use_counting = not self.config.use_counting
        play_sound("button_click")
        self._setup_config_buttons()

    def _cycle_spread(self) -> None:
        spreads = [4, 8, 12, 16]
        current_idx = spreads.index(self.config.bet_spread) if self.config.bet_spread in spreads else 0
        self.config.bet_spread = spreads[(current_idx + 1) % len(spreads)]
        play_sound("button_click")
        self._setup_config_buttons()

    def _set_speed(self, speed: int) -> None:
        self.config.speed = speed
        play_sound("button_click")
        self._setup_config_buttons()

    def _start_simulation(self) -> None:
        """Start or restart the simulation."""
        play_sound("button_click")

        # Get rules from settings
        settings = get_settings_manager()
        table_rules = settings.table_rules
        rules = RuleSet(
            num_decks=table_rules.num_decks,
            dealer_hits_soft_17=table_rules.dealer_hits_soft_17,
            blackjack_payout=table_rules.blackjack_payout,
            double_after_split=table_rules.double_after_split,
            double_on=table_rules.double_on,
            resplit_aces=table_rules.resplit_aces,
            max_splits=table_rules.max_splits,
            surrender=table_rules.surrender,
        )

        self.engine = SimulationEngine(self.config, rules)
        self.state = SimState.RUNNING
        self.start_button.text = "RESTART"
        self.pause_button.set_enabled(True)
        self.pause_button.text = "PAUSE"

    def _toggle_pause(self) -> None:
        """Toggle pause state."""
        play_sound("button_click")
        if self.state == SimState.RUNNING:
            self.state = SimState.PAUSED
            self.pause_button.text = "RESUME"
        elif self.state == SimState.PAUSED:
            self.state = SimState.RUNNING
            self.pause_button.text = "PAUSE"

    def _go_back(self) -> None:
        play_sound("button_click")
        self.change_scene("title", transition=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        # Config buttons (only in setup or complete state)
        if self.state in (SimState.SETUP, SimState.COMPLETE):
            for btn in self.config_buttons:
                if btn.handle_event(event):
                    return True

        # Control buttons
        if self.start_button and self.start_button.handle_event(event):
            return True
        if self.pause_button and self.pause_button.handle_event(event):
            return True
        if self.back_button and self.back_button.handle_event(event):
            return True

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
                return True
            elif event.key == pygame.K_SPACE:
                if self.state == SimState.SETUP:
                    self._start_simulation()
                elif self.state in (SimState.RUNNING, SimState.PAUSED):
                    self._toggle_pause()
                return True

        return False

    def update(self, dt: float) -> None:
        # Update buttons
        if self.start_button:
            self.start_button.update(dt)
        if self.pause_button:
            self.pause_button.update(dt)
        if self.back_button:
            self.back_button.update(dt)
        for btn in self.config_buttons:
            btn.update(dt)

        # Run simulation
        if self.state == SimState.RUNNING and self.engine:
            self._time_accumulator += dt
            hands_this_frame = int(self._time_accumulator * self.config.speed)

            if hands_this_frame > 0:
                self._time_accumulator = 0.0
                for _ in range(min(hands_this_frame, 1000)):  # Cap per frame
                    if self.engine.stats.hands_played >= self.config.num_hands:
                        self.state = SimState.COMPLETE
                        self.pause_button.set_enabled(False)
                        break
                    if self.engine.bankroll <= 0:
                        self.state = SimState.COMPLETE
                        self.pause_button.set_enabled(False)
                        break
                    self.engine.play_hand()

            # Update progress bar
            if self.progress_bar:
                progress = self.engine.stats.hands_played / self.config.num_hands
                self.progress_bar.set_progress(
                    progress,
                    f"{self.engine.stats.hands_played:,} / {self.config.num_hands:,}",
                )

    def draw(self, surface: pygame.Surface) -> None:
        self._init_fonts()

        # Background
        surface.fill(COLORS.BACKGROUND)

        # Panel
        if self.panel:
            self.panel.draw(surface)

        # Title
        title = self._title_font.render("SIMULATION", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 60))
        surface.blit(title, title_rect)

        if self.state == SimState.SETUP:
            self._draw_setup(surface)
        else:
            self._draw_stats(surface)

        # Progress bar
        if self.progress_bar and self.state != SimState.SETUP:
            self.progress_bar.draw(surface)

        # Buttons
        if self.start_button:
            self.start_button.draw(surface)
        if self.pause_button:
            self.pause_button.draw(surface)
        if self.back_button:
            self.back_button.draw(surface)

        # Instructions
        inst = "SPACE: Start/Pause | ESC: Back"
        inst_surface = self._small_font.render(inst, True, COLORS.TEXT_MUTED)
        inst_rect = inst_surface.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 30))
        surface.blit(inst_surface, inst_rect)

        self.crt_filter.apply(surface)

    def _draw_setup(self, surface: pygame.Surface) -> None:
        """Draw setup screen."""
        center_x = DIMENSIONS.CENTER_X
        start_y = DIMENSIONS.CENTER_Y - 150

        # Labels
        labels = [
            (start_y - 25, "Number of Hands:"),
            (start_y + 25, "Strategy:"),
            (start_y + 75, "Speed:"),
        ]
        for y, text in labels:
            label = self._font.render(text, True, COLORS.TEXT_WHITE)
            rect = label.get_rect(midleft=(center_x - 280, y))
            surface.blit(label, rect)

        # Draw config buttons
        for btn in self.config_buttons:
            btn.draw(surface)

        # Show current config summary
        summary_y = DIMENSIONS.CENTER_Y + 60
        settings = get_settings_manager()
        rules = settings.table_rules
        summary_lines = [
            f"Table Rules: {rules.num_decks} decks, {'H17' if rules.dealer_hits_soft_17 else 'S17'}, "
            f"{'3:2' if rules.blackjack_payout == 1.5 else '6:5'} BJ",
            f"Starting Bankroll: ${self.config.initial_bankroll:,} | Base Bet: ${self.config.base_bet}",
        ]
        for i, line in enumerate(summary_lines):
            text = self._small_font.render(line, True, COLORS.TEXT_MUTED)
            rect = text.get_rect(center=(center_x, summary_y + i * 25))
            surface.blit(text, rect)

    def _draw_stats(self, surface: pygame.Surface) -> None:
        """Draw simulation statistics."""
        if not self.engine:
            return

        center_x = DIMENSIONS.CENTER_X
        stats = self.engine.stats
        bankroll = self.engine.bankroll

        # Draw bankroll graph
        self._draw_bankroll_graph(surface, DIMENSIONS.CENTER_X - 280, DIMENSIONS.CENTER_Y - 120, 560, 150)

        # Stats columns
        left_x = center_x - 200
        right_x = center_x + 50
        start_y = DIMENSIONS.CENTER_Y + 50

        left_stats = [
            ("Hands Played:", f"{stats.hands_played:,}"),
            ("Win Rate:", f"{stats.win_rate:.1f}%"),
            ("Blackjacks:", f"{stats.blackjacks:,}"),
            ("Doubles W/L:", f"{stats.doubles_won}/{stats.doubles_lost}"),
        ]

        right_stats = [
            ("Current Bankroll:", f"${bankroll:,.0f}"),
            ("Net Profit:", f"${stats.net_profit:+,.0f}"),
            ("Peak:", f"${stats.peak_bankroll:,.0f}"),
            ("EV/Hand:", f"${stats.ev_per_hand:+.2f}"),
        ]

        for i, (label, value) in enumerate(left_stats):
            label_surf = self._small_font.render(label, True, COLORS.TEXT_MUTED)
            value_surf = self._small_font.render(value, True, COLORS.TEXT_WHITE)
            surface.blit(label_surf, (left_x, start_y + i * 22))
            surface.blit(value_surf, (left_x + 120, start_y + i * 22))

        for i, (label, value) in enumerate(right_stats):
            label_surf = self._small_font.render(label, True, COLORS.TEXT_MUTED)
            # Color code profit
            if "Profit" in label or "EV" in label:
                val_num = stats.net_profit if "Profit" in label else stats.ev_per_hand
                color = (100, 200, 100) if val_num >= 0 else (200, 100, 100)
            else:
                color = COLORS.TEXT_WHITE
            value_surf = self._small_font.render(value, True, color)
            surface.blit(label_surf, (right_x, start_y + i * 22))
            surface.blit(value_surf, (right_x + 140, start_y + i * 22))

    def _draw_bankroll_graph(self, surface: pygame.Surface, x: int, y: int, width: int, height: int) -> None:
        """Draw bankroll history graph."""
        if not self.engine or len(self.engine.stats.bankroll_history) < 2:
            return

        history = self.engine.stats.bankroll_history
        initial = self.config.initial_bankroll

        # Calculate bounds
        min_val = min(history)
        max_val = max(history)
        if max_val == min_val:
            max_val = min_val + 1

        # Draw background
        graph_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(surface, (30, 30, 35), graph_rect, border_radius=4)
        pygame.draw.rect(surface, COLORS.TEXT_MUTED, graph_rect, width=1, border_radius=4)

        # Draw zero line (initial bankroll)
        if min_val < initial < max_val:
            zero_y = y + height - int((initial - min_val) / (max_val - min_val) * height)
            pygame.draw.line(surface, (80, 80, 80), (x, zero_y), (x + width, zero_y), 1)

        # Draw line graph
        if len(history) > 1:
            points = []
            for i, val in enumerate(history):
                px = x + int(i / (len(history) - 1) * width)
                py = y + height - int((val - min_val) / (max_val - min_val) * height)
                points.append((px, py))

            # Color based on profit
            color = (80, 180, 80) if history[-1] >= initial else (180, 80, 80)
            pygame.draw.lines(surface, color, False, points, 2)

        # Labels
        max_label = self._small_font.render(f"${max_val:,.0f}", True, COLORS.TEXT_MUTED)
        min_label = self._small_font.render(f"${min_val:,.0f}", True, COLORS.TEXT_MUTED)
        surface.blit(max_label, (x + 5, y + 5))
        surface.blit(min_label, (x + 5, y + height - 20))
