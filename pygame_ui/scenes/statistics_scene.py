"""Statistics calculator scene with Kelly criterion, risk of ruin, and house edge tools."""

from decimal import Decimal
from typing import Optional, List, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.scenes.base_scene import BaseScene
from pygame_ui.components.button import Button
from pygame_ui.components.panel import Panel
from pygame_ui.effects.crt_filter import CRTFilter

from core.statistics.kelly import KellyCalculator
from core.statistics.bankroll import BankrollManager, RiskOfRuin
from core.statistics.house_edge import HouseEdgeCalculator
from core.strategy.rules import RuleSet


class InputField:
    """A simple numeric input field with label."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        label: str,
        value: float,
        min_val: float = 0,
        max_val: float = 100000,
        step: float = 10,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.label = label
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.height = 60

        self._label_font: Optional[pygame.font.Font] = None
        self._value_font: Optional[pygame.font.Font] = None

    @property
    def label_font(self) -> pygame.font.Font:
        if self._label_font is None:
            self._label_font = pygame.font.Font(None, 22)
        return self._label_font

    @property
    def value_font(self) -> pygame.font.Font:
        if self._value_font is None:
            self._value_font = pygame.font.Font(None, 28)
        return self._value_font

    def adjust(self, direction: int) -> None:
        """Adjust value by step amount."""
        new_val = self.value + (self.step * direction)
        self.value = max(self.min_val, min(self.max_val, new_val))

    def get_rect(self) -> pygame.Rect:
        """Get bounding rectangle."""
        return pygame.Rect(
            int(self.x - self.width / 2),
            int(self.y - self.height / 2),
            int(self.width),
            int(self.height),
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse wheel and click events."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            rect = self.get_rect()
            if rect.collidepoint(event.pos):
                if event.button == 4:  # Scroll up
                    self.adjust(1)
                    return True
                elif event.button == 5:  # Scroll down
                    self.adjust(-1)
                    return True
                elif event.button == 1:  # Left click - increase
                    self.adjust(1)
                    return True
                elif event.button == 3:  # Right click - decrease
                    self.adjust(-1)
                    return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the input field."""
        rect = self.get_rect()

        # Background
        pygame.draw.rect(surface, COLORS.PANEL_BG, rect, border_radius=6)
        pygame.draw.rect(surface, COLORS.PANEL_BORDER, rect, width=1, border_radius=6)

        # Label
        label_text = self.label_font.render(self.label, True, COLORS.TEXT_MUTED)
        label_rect = label_text.get_rect(centerx=int(self.x), top=int(self.y - 22))
        surface.blit(label_text, label_rect)

        # Value
        if isinstance(self.value, float) and self.value == int(self.value):
            val_str = f"{int(self.value):,}"
        else:
            val_str = f"{self.value:,.1f}"
        value_text = self.value_font.render(val_str, True, COLORS.TEXT_WHITE)
        value_rect = value_text.get_rect(centerx=int(self.x), centery=int(self.y + 8))
        surface.blit(value_text, value_rect)


class RuleToggle:
    """A toggleable rule option."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        label: str,
        enabled: bool = False,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.label = label
        self.enabled = enabled
        self.height = 30

        self._font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 22)
        return self._font

    def get_rect(self) -> pygame.Rect:
        """Get bounding rectangle."""
        return pygame.Rect(
            int(self.x - self.width / 2),
            int(self.y - self.height / 2),
            int(self.width),
            int(self.height),
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle click to toggle."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rect = self.get_rect()
            if rect.collidepoint(event.pos):
                self.enabled = not self.enabled
                return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the toggle."""
        rect = self.get_rect()

        # Background
        bg_color = COLORS.COUNT_POSITIVE if self.enabled else COLORS.PANEL_BG
        pygame.draw.rect(surface, bg_color, rect, border_radius=4)
        pygame.draw.rect(surface, COLORS.PANEL_BORDER, rect, width=1, border_radius=4)

        # Label
        text_color = COLORS.TEXT_WHITE if self.enabled else COLORS.TEXT_MUTED
        text = self.font.render(self.label, True, text_color)
        text_rect = text.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(text, text_rect)


class ResultDisplay:
    """Displays a calculated result with label."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        label: str,
        value: str = "",
        value_color: Tuple[int, int, int] = COLORS.TEXT_WHITE,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.label = label
        self.value = value
        self.value_color = value_color
        self.height = 50

        self._label_font: Optional[pygame.font.Font] = None
        self._value_font: Optional[pygame.font.Font] = None

    @property
    def label_font(self) -> pygame.font.Font:
        if self._label_font is None:
            self._label_font = pygame.font.Font(None, 22)
        return self._label_font

    @property
    def value_font(self) -> pygame.font.Font:
        if self._value_font is None:
            self._value_font = pygame.font.Font(None, 32)
        return self._value_font

    def set_value(self, value: str, color: Tuple[int, int, int] = None) -> None:
        """Update displayed value."""
        self.value = value
        if color:
            self.value_color = color

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the result display."""
        # Label
        label_text = self.label_font.render(self.label, True, COLORS.TEXT_MUTED)
        label_rect = label_text.get_rect(centerx=int(self.x), top=int(self.y))
        surface.blit(label_text, label_rect)

        # Value
        value_text = self.value_font.render(self.value, True, self.value_color)
        value_rect = value_text.get_rect(centerx=int(self.x), top=int(self.y + 20))
        surface.blit(value_text, value_rect)


class StatisticsScene(BaseScene):
    """Statistics calculator dashboard.

    Features:
    - Kelly criterion calculator for optimal bet sizing
    - Risk of ruin calculations
    - House edge analyzer with rule variations
    - Session recommendations (stop-loss, win goals)
    """

    def __init__(self):
        super().__init__()

        # UI Components
        self.back_button: Optional[Button] = None

        # Tab buttons
        self.tab_buttons: List[Button] = []
        self.active_tab = 0  # 0=Kelly, 1=RoR, 2=House Edge

        # Kelly calculator inputs
        self.kelly_inputs: List[InputField] = []
        self.kelly_results: List[ResultDisplay] = []

        # Risk of Ruin inputs
        self.ror_inputs: List[InputField] = []
        self.ror_results: List[ResultDisplay] = []

        # House Edge controls
        self.rule_toggles: List[RuleToggle] = []
        self.deck_buttons: List[Button] = []
        self.house_edge_results: List[ResultDisplay] = []
        self.selected_decks = 6

        # Visual effects
        self.crt_filter = CRTFilter(scanline_alpha=20, vignette_strength=0.2)

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._section_font: Optional[pygame.font.Font] = None
        self._help_font: Optional[pygame.font.Font] = None

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

    @property
    def help_font(self) -> pygame.font.Font:
        if self._help_font is None:
            self._help_font = pygame.font.Font(None, 20)
        return self._help_font

    def on_enter(self) -> None:
        """Initialize the scene."""
        super().on_enter()
        self._setup_ui()
        self._calculate_all()

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

        # Tab buttons
        tab_y = 100
        tab_width = 180
        tab_names = ["KELLY", "RISK OF RUIN", "HOUSE EDGE"]

        self.tab_buttons = []
        for i, name in enumerate(tab_names):
            btn = Button(
                x=DIMENSIONS.CENTER_X - tab_width + (i * tab_width),
                y=tab_y,
                text=name,
                font_size=22,
                on_click=lambda idx=i: self._set_tab(idx),
                bg_color=COLORS.BUTTON_DEFAULT,
                hover_color=COLORS.BUTTON_HOVER,
                width=tab_width - 10,
                height=36,
            )
            self.tab_buttons.append(btn)

        self._setup_kelly_panel()
        self._setup_ror_panel()
        self._setup_house_edge_panel()

    def _setup_kelly_panel(self) -> None:
        """Set up Kelly criterion calculator inputs."""
        base_y = 180
        spacing = 80

        self.kelly_inputs = [
            InputField(
                DIMENSIONS.CENTER_X - 200, base_y, 150,
                "BANKROLL ($)", 10000, 100, 1000000, 500
            ),
            InputField(
                DIMENSIONS.CENTER_X, base_y, 150,
                "TRUE COUNT", 2.0, -10, 20, 0.5
            ),
            InputField(
                DIMENSIONS.CENTER_X + 200, base_y, 150,
                "MIN BET ($)", 25, 5, 1000, 5
            ),
        ]

        # Results
        result_y = base_y + 100
        self.kelly_results = [
            ResultDisplay(DIMENSIONS.CENTER_X - 150, result_y, 200, "OPTIMAL BET"),
            ResultDisplay(DIMENSIONS.CENTER_X + 150, result_y, 200, "PLAYER EDGE"),
        ]

        # Session recommendations
        session_y = result_y + 100
        self.kelly_results.extend([
            ResultDisplay(DIMENSIONS.CENTER_X - 200, session_y, 180, "STOP LOSS"),
            ResultDisplay(DIMENSIONS.CENTER_X, session_y, 180, "WIN GOAL"),
            ResultDisplay(DIMENSIONS.CENTER_X + 200, session_y, 180, "UNIT SIZE"),
        ])

    def _setup_ror_panel(self) -> None:
        """Set up Risk of Ruin calculator inputs."""
        base_y = 180
        spacing = 80

        self.ror_inputs = [
            InputField(
                DIMENSIONS.CENTER_X - 200, base_y, 150,
                "BANKROLL ($)", 10000, 100, 1000000, 500
            ),
            InputField(
                DIMENSIONS.CENTER_X, base_y, 150,
                "AVG BET ($)", 50, 5, 10000, 10
            ),
            InputField(
                DIMENSIONS.CENTER_X + 200, base_y, 150,
                "EDGE (%)", 1.0, -2.0, 5.0, 0.1
            ),
        ]

        # Results
        result_y = base_y + 100
        self.ror_results = [
            ResultDisplay(DIMENSIONS.CENTER_X - 150, result_y, 200, "RISK OF RUIN"),
            ResultDisplay(DIMENSIONS.CENTER_X + 150, result_y, 200, "N-ZERO POINT"),
        ]

        # Additional info
        info_y = result_y + 100
        self.ror_results.extend([
            ResultDisplay(DIMENSIONS.CENTER_X - 150, info_y, 200, "HANDS TO DOUBLE"),
            ResultDisplay(DIMENSIONS.CENTER_X + 150, info_y, 200, "BANKROLL UNITS"),
        ])

    def _setup_house_edge_panel(self) -> None:
        """Set up House Edge analyzer."""
        base_y = 160

        # Deck selector
        deck_y = base_y + 20
        deck_options = [1, 2, 4, 6, 8]
        self.deck_buttons = []
        for i, decks in enumerate(deck_options):
            btn = Button(
                x=DIMENSIONS.CENTER_X - 180 + (i * 90),
                y=deck_y,
                text=f"{decks}D",
                font_size=20,
                on_click=lambda d=decks: self._set_decks(d),
                bg_color=COLORS.BUTTON_DEFAULT,
                hover_color=COLORS.BUTTON_HOVER,
                width=70,
                height=32,
            )
            self.deck_buttons.append(btn)

        # Rule toggles
        toggle_y = deck_y + 60
        toggle_spacing_x = 180
        toggle_spacing_y = 40

        rule_configs = [
            ("H17", False),     # Dealer hits soft 17
            ("6:5 BJ", False),  # 6:5 blackjack payout
            ("No DAS", False),  # No double after split
            ("RSA", False),     # Resplit aces
            ("No Surr", False), # No surrender
            ("No Peek", False), # European no hole card
        ]

        self.rule_toggles = []
        for i, (label, default) in enumerate(rule_configs):
            col = i % 3
            row = i // 3
            toggle = RuleToggle(
                DIMENSIONS.CENTER_X - toggle_spacing_x + (col * toggle_spacing_x),
                toggle_y + (row * toggle_spacing_y),
                150,
                label,
                default,
            )
            self.rule_toggles.append(toggle)

        # Results
        result_y = toggle_y + 120
        self.house_edge_results = [
            ResultDisplay(DIMENSIONS.CENTER_X - 150, result_y, 200, "HOUSE EDGE"),
            ResultDisplay(DIMENSIONS.CENTER_X + 150, result_y, 200, "PLAYER EDGE @ TC+2"),
        ]

        # Comparison presets
        preset_y = result_y + 100
        self.house_edge_results.extend([
            ResultDisplay(DIMENSIONS.CENTER_X - 200, preset_y, 150, "VEGAS STRIP"),
            ResultDisplay(DIMENSIONS.CENTER_X, preset_y, 150, "DOWNTOWN"),
            ResultDisplay(DIMENSIONS.CENTER_X + 200, preset_y, 150, "ATLANTIC CITY"),
        ])

    def _set_tab(self, idx: int) -> None:
        """Switch active tab."""
        self.active_tab = idx
        self._calculate_all()

    def _set_decks(self, decks: int) -> None:
        """Set number of decks."""
        self.selected_decks = decks
        self._calculate_house_edge()

    def _calculate_all(self) -> None:
        """Calculate all results for the active tab."""
        if self.active_tab == 0:
            self._calculate_kelly()
        elif self.active_tab == 1:
            self._calculate_ror()
        else:
            self._calculate_house_edge()

    def _calculate_kelly(self) -> None:
        """Calculate Kelly criterion results."""
        if not self.kelly_inputs:
            return

        bankroll = Decimal(str(self.kelly_inputs[0].value))
        true_count = self.kelly_inputs[1].value
        min_bet = Decimal(str(self.kelly_inputs[2].value))

        # Create Kelly calculator
        kelly = KellyCalculator(
            bankroll=bankroll,
            min_bet=min_bet,
            max_bet=bankroll / 10,  # 10% of bankroll as max
            kelly_fraction=0.5,  # Half Kelly for safety
        )

        # Calculate optimal bet for TC
        optimal_bet = kelly.bet_for_true_count(true_count)

        # Calculate player edge
        base_edge = Decimal("0.005")  # 0.5% house edge at TC 0
        edge_per_tc = Decimal("0.005")  # 0.5% per TC
        player_edge = Decimal(str(true_count)) * edge_per_tc - base_edge
        edge_pct = float(player_edge) * 100

        # Update results
        self.kelly_results[0].set_value(
            f"${optimal_bet:,.0f}",
            COLORS.COUNT_POSITIVE if player_edge > 0 else COLORS.TEXT_WHITE
        )

        edge_color = COLORS.COUNT_POSITIVE if edge_pct > 0 else COLORS.COUNT_NEGATIVE
        self.kelly_results[1].set_value(f"{edge_pct:+.2f}%", edge_color)

        # Session recommendations
        manager = BankrollManager(
            bankroll=bankroll,
            min_bet=min_bet,
            max_bet=bankroll / 10,
            player_edge=max(Decimal("0.005"), player_edge),
        )

        stop_loss = manager.session_stop_loss(0.1)
        win_goal = manager.session_win_goal(stop_loss, 1.5)
        unit_size = manager.recommended_unit_size(max_bet_spread=12)

        self.kelly_results[2].set_value(f"${stop_loss:,.0f}")
        self.kelly_results[3].set_value(f"${win_goal:,.0f}")
        self.kelly_results[4].set_value(f"${unit_size:,.0f}")

    def _calculate_ror(self) -> None:
        """Calculate risk of ruin results."""
        if not self.ror_inputs:
            return

        bankroll = Decimal(str(self.ror_inputs[0].value))
        avg_bet = Decimal(str(self.ror_inputs[1].value))
        edge_pct = self.ror_inputs[2].value
        player_edge = Decimal(str(edge_pct / 100))

        # Create bankroll manager
        manager = BankrollManager(
            bankroll=bankroll,
            min_bet=avg_bet,
            max_bet=avg_bet * 12,
            player_edge=player_edge,
        )

        # Calculate risk of ruin
        ror = manager.risk_of_ruin(average_bet=avg_bet)

        # Format risk of ruin
        ror_pct = ror.probability * 100
        if ror_pct < 0.01:
            ror_str = "<0.01%"
            ror_color = COLORS.COUNT_POSITIVE
        elif ror_pct > 99:
            ror_str = ">99%"
            ror_color = COLORS.COUNT_NEGATIVE
        else:
            ror_str = f"{ror_pct:.2f}%"
            ror_color = (
                COLORS.COUNT_POSITIVE if ror_pct < 5 else
                COLORS.COUNT_NEGATIVE if ror_pct > 20 else
                COLORS.GOLD
            )

        self.ror_results[0].set_value(ror_str, ror_color)

        # N-zero point
        n_zero = ror.n_zero_point
        if n_zero == float("inf"):
            n_zero_str = "N/A"
        else:
            n_zero_str = f"{n_zero:,.0f}"
        self.ror_results[1].set_value(n_zero_str)

        # Hands to double
        hands_double = ror.expected_hands_to_double
        self.ror_results[2].set_value(f"{hands_double:,}" if hands_double > 0 else "N/A")

        # Bankroll units
        units = manager.units_in_bankroll()
        self.ror_results[3].set_value(f"{units:,} units")

    def _calculate_house_edge(self) -> None:
        """Calculate house edge based on selected rules."""
        # Build rule set from toggles
        h17 = self.rule_toggles[0].enabled if self.rule_toggles else False
        bj_65 = self.rule_toggles[1].enabled if len(self.rule_toggles) > 1 else False
        no_das = self.rule_toggles[2].enabled if len(self.rule_toggles) > 2 else False
        rsa = self.rule_toggles[3].enabled if len(self.rule_toggles) > 3 else False
        no_surr = self.rule_toggles[4].enabled if len(self.rule_toggles) > 4 else False
        no_peek = self.rule_toggles[5].enabled if len(self.rule_toggles) > 5 else False

        rules = RuleSet(
            num_decks=self.selected_decks,
            dealer_hits_soft_17=h17,
            blackjack_payout=1.2 if bj_65 else 1.5,
            double_after_split=not no_das,
            resplit_aces=rsa,
            surrender="none" if no_surr else "late",
            dealer_peeks=not no_peek,
        )

        calc = HouseEdgeCalculator(rules)
        house_edge = calc.calculate()

        # Format house edge
        he_pct = float(house_edge)
        he_color = COLORS.COUNT_NEGATIVE if he_pct > 0.6 else COLORS.TEXT_WHITE
        self.house_edge_results[0].set_value(f"{he_pct:.2f}%", he_color)

        # Player edge at TC +2
        player_edge_tc2 = calc.player_advantage_with_count(2.0)
        pe_pct = float(player_edge_tc2)
        pe_color = COLORS.COUNT_POSITIVE if pe_pct > 0 else COLORS.COUNT_NEGATIVE
        self.house_edge_results[1].set_value(f"{pe_pct:+.2f}%", pe_color)

        # Presets for comparison
        presets = [
            ("Vegas Strip", RuleSet.vegas_strip()),
            ("Downtown", RuleSet.downtown_vegas()),
            ("Atlantic City", RuleSet.atlantic_city()),
        ]

        for i, (name, preset_rules) in enumerate(presets):
            preset_calc = HouseEdgeCalculator(preset_rules)
            preset_edge = preset_calc.calculate()
            self.house_edge_results[2 + i].set_value(f"{float(preset_edge):.2f}%")

    def _on_back(self) -> None:
        """Handle back button click."""
        self.change_scene("title", transition=True)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        # Back button
        if self.back_button and self.back_button.handle_event(event):
            return True

        # Tab buttons
        for i, btn in enumerate(self.tab_buttons):
            if btn.handle_event(event):
                self._set_tab(i)
                return True

        # Handle active tab inputs
        if self.active_tab == 0:
            for inp in self.kelly_inputs:
                if inp.handle_event(event):
                    self._calculate_kelly()
                    return True
        elif self.active_tab == 1:
            for inp in self.ror_inputs:
                if inp.handle_event(event):
                    self._calculate_ror()
                    return True
        else:
            # Deck buttons
            for i, btn in enumerate(self.deck_buttons):
                if btn.handle_event(event):
                    self._set_decks([1, 2, 4, 6, 8][i])
                    return True

            # Rule toggles
            for toggle in self.rule_toggles:
                if toggle.handle_event(event):
                    self._calculate_house_edge()
                    return True

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._on_back()
                return True
            elif event.key == pygame.K_1:
                self._set_tab(0)
                return True
            elif event.key == pygame.K_2:
                self._set_tab(1)
                return True
            elif event.key == pygame.K_3:
                self._set_tab(2)
                return True

        return False

    def update(self, dt: float) -> None:
        """Update scene."""
        if self.back_button:
            self.back_button.update(dt)

        for btn in self.tab_buttons:
            btn.update(dt)

        if self.active_tab == 2:
            for btn in self.deck_buttons:
                btn.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the scene."""
        # Background
        surface.fill(COLORS.BACKGROUND)

        # Title
        title = self.title_font.render("STATISTICS", True, COLORS.GOLD)
        title_rect = title.get_rect(center=(DIMENSIONS.CENTER_X, 45))
        surface.blit(title, title_rect)

        # Back button
        if self.back_button:
            self.back_button.draw(surface)

        # Tab buttons with active indicator
        for i, btn in enumerate(self.tab_buttons):
            if i == self.active_tab:
                btn.bg_color = COLORS.BUTTON_HOVER
            else:
                btn.bg_color = COLORS.BUTTON_DEFAULT
            btn.draw(surface)

        # Draw active tab content
        if self.active_tab == 0:
            self._draw_kelly_panel(surface)
        elif self.active_tab == 1:
            self._draw_ror_panel(surface)
        else:
            self._draw_house_edge_panel(surface)

        # Instructions
        instructions = "1/2/3: Switch tabs | Click/Scroll: Adjust values | ESC: Back"
        text = self.help_font.render(instructions, True, COLORS.TEXT_MUTED)
        text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, DIMENSIONS.SCREEN_HEIGHT - 20))
        surface.blit(text, text_rect)

        # Apply CRT filter
        self.crt_filter.apply(surface)

    def _draw_kelly_panel(self, surface: pygame.Surface) -> None:
        """Draw Kelly criterion calculator panel."""
        # Section title
        section = self.section_font.render("Kelly Criterion Calculator", True, COLORS.TEXT_WHITE)
        section_rect = section.get_rect(center=(DIMENSIONS.CENTER_X, 140))
        surface.blit(section, section_rect)

        # Inputs
        for inp in self.kelly_inputs:
            inp.draw(surface)

        # Results
        for result in self.kelly_results:
            result.draw(surface)

        # Help text
        help_lines = [
            "The Kelly criterion calculates optimal bet size based on your edge.",
            "Using Half-Kelly (50%) for safer bankroll management.",
            "Scroll or click fields to adjust values.",
        ]
        y = DIMENSIONS.SCREEN_HEIGHT - 100
        for line in help_lines:
            text = self.help_font.render(line, True, COLORS.TEXT_MUTED)
            text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, y))
            surface.blit(text, text_rect)
            y += 20

    def _draw_ror_panel(self, surface: pygame.Surface) -> None:
        """Draw Risk of Ruin panel."""
        # Section title
        section = self.section_font.render("Risk of Ruin Calculator", True, COLORS.TEXT_WHITE)
        section_rect = section.get_rect(center=(DIMENSIONS.CENTER_X, 140))
        surface.blit(section, section_rect)

        # Inputs
        for inp in self.ror_inputs:
            inp.draw(surface)

        # Results
        for result in self.ror_results:
            result.draw(surface)

        # Help text
        help_lines = [
            "Risk of Ruin is the probability of losing your entire bankroll.",
            "N-Zero is when long-term expectation dominates variance.",
            "Target RoR below 5% for professional play.",
        ]
        y = DIMENSIONS.SCREEN_HEIGHT - 100
        for line in help_lines:
            text = self.help_font.render(line, True, COLORS.TEXT_MUTED)
            text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, y))
            surface.blit(text, text_rect)
            y += 20

    def _draw_house_edge_panel(self, surface: pygame.Surface) -> None:
        """Draw House Edge analyzer panel."""
        # Section title
        section = self.section_font.render("House Edge Analyzer", True, COLORS.TEXT_WHITE)
        section_rect = section.get_rect(center=(DIMENSIONS.CENTER_X, 140))
        surface.blit(section, section_rect)

        # Deck label
        deck_label = self.help_font.render("NUMBER OF DECKS:", True, COLORS.TEXT_MUTED)
        deck_rect = deck_label.get_rect(right=DIMENSIONS.CENTER_X - 230, centery=180)
        surface.blit(deck_label, deck_rect)

        # Deck buttons with active indicator
        for i, btn in enumerate(self.deck_buttons):
            decks = [1, 2, 4, 6, 8][i]
            if decks == self.selected_decks:
                btn.bg_color = COLORS.COUNT_POSITIVE
            else:
                btn.bg_color = COLORS.BUTTON_DEFAULT
            btn.draw(surface)

        # Rule toggles label
        rules_label = self.help_font.render("RULE VARIATIONS (click to toggle):", True, COLORS.TEXT_MUTED)
        rules_rect = rules_label.get_rect(left=60, centery=220)
        surface.blit(rules_label, rules_rect)

        # Rule toggles
        for toggle in self.rule_toggles:
            toggle.draw(surface)

        # Results
        for result in self.house_edge_results:
            result.draw(surface)

        # Help text
        help_lines = [
            "H17=Hit Soft 17, DAS=Double After Split, RSA=Resplit Aces",
            "6:5 BJ increases edge by 1.39%. Always look for 3:2 tables.",
            "Each TC+1 is worth approximately 0.5% to the player.",
        ]
        y = DIMENSIONS.SCREEN_HEIGHT - 100
        for line in help_lines:
            text = self.help_font.render(line, True, COLORS.TEXT_MUTED)
            text_rect = text.get_rect(center=(DIMENSIONS.CENTER_X, y))
            surface.blit(text, text_rect)
            y += 20
