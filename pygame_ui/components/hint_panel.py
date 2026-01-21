"""Hint panel components for strategy and betting advice."""

import math
from typing import Optional, Tuple

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from pygame_ui.components.panel import Panel


class BestPlayHint(Panel):
    """Panel displaying the recommended play during PLAYER_TURN.

    Shows the basic strategy action and highlights when a deviation applies.
    """

    def __init__(
        self,
        x: float,
        y: float,
        width: float = 200,
        **kwargs,
    ):
        kwargs.setdefault("bg_color", (35, 38, 48))
        kwargs.setdefault("bg_alpha", 220)
        kwargs.setdefault("border_color", COLORS.SILVER)
        super().__init__(x, y, width, 100, **kwargs)

        self.visible = False
        self.action_name = ""
        self.reason = ""
        self.is_deviation = False
        self.deviation_description = ""

        # Animation state
        self._glow_time = 0.0
        self._pulse_scale = 1.0

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._action_font: Optional[pygame.font.Font] = None
        self._detail_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 24)
        return self._title_font

    @property
    def action_font(self) -> pygame.font.Font:
        if self._action_font is None:
            self._action_font = pygame.font.Font(None, 36)
        return self._action_font

    @property
    def detail_font(self) -> pygame.font.Font:
        if self._detail_font is None:
            self._detail_font = pygame.font.Font(None, 20)
        return self._detail_font

    def set_recommendation(
        self,
        action_name: str,
        reason: str = "",
        is_deviation: bool = False,
        deviation_description: str = "",
    ) -> None:
        """Set the current recommendation to display.

        Args:
            action_name: The action to recommend (HIT, STAND, DOUBLE, etc.)
            reason: Brief reason for the action
            is_deviation: Whether this is a count-based deviation
            deviation_description: Description of the deviation if applicable
        """
        self.action_name = action_name
        self.reason = reason
        self.is_deviation = is_deviation
        self.deviation_description = deviation_description
        self._needs_redraw = True

        # Calculate height based on content
        base_height = 85
        if is_deviation and deviation_description:
            base_height += 25
        self.set_size(self.width, base_height)

    def show(self) -> None:
        """Show the hint panel."""
        self.visible = True

    def hide(self) -> None:
        """Hide the hint panel."""
        self.visible = False

    def update(self, dt: float) -> None:
        """Update animation state."""
        self._glow_time += dt

        # Pulsing effect for deviations
        if self.is_deviation:
            self._pulse_scale = 1.0 + 0.02 * math.sin(self._glow_time * 4)

    def _get_action_color(self) -> Tuple[int, int, int]:
        """Get color based on action type."""
        action_upper = self.action_name.upper()
        if action_upper == "HIT":
            return (100, 180, 100)  # Green
        elif action_upper == "STAND":
            return (180, 180, 180)  # Gray
        elif action_upper == "DOUBLE":
            return (100, 150, 220)  # Blue
        elif action_upper == "SPLIT":
            return (220, 150, 80)  # Orange
        elif action_upper == "SURRENDER":
            return (180, 80, 80)  # Red
        return COLORS.TEXT_WHITE

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the hint panel."""
        if not self.visible:
            return

        # Draw base panel
        super().draw(surface)

        y_offset = int(self.y) + DIMENSIONS.PANEL_PADDING

        # Title with optional deviation badge
        title_text = "BEST PLAY"
        if self.is_deviation:
            title_text = "DEVIATION"
            # Glow effect for deviation
            glow_alpha = int(100 + 50 * math.sin(self._glow_time * 3))
            glow_color = (*COLORS.GOLD, glow_alpha)
            glow_rect = pygame.Rect(
                int(self.x) - 2, int(self.y) - 2,
                int(self.width) + 4, int(self.height) + 4
            )
            glow_surface = pygame.Surface(
                (glow_rect.width, glow_rect.height), pygame.SRCALPHA
            )
            pygame.draw.rect(
                glow_surface, glow_color, glow_surface.get_rect(),
                width=3, border_radius=self.corner_radius + 2
            )
            surface.blit(glow_surface, glow_rect.topleft)

        title_color = COLORS.GOLD if self.is_deviation else COLORS.TEXT_MUTED
        title_rendered = self.title_font.render(title_text, True, title_color)
        title_rect = title_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(title_rendered, title_rect)
        y_offset += 24

        # Action name (large, colored)
        action_color = self._get_action_color()
        action_rendered = self.action_font.render(self.action_name.upper(), True, action_color)
        action_rect = action_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(action_rendered, action_rect)
        y_offset += 35

        # Reason or deviation description
        if self.is_deviation and self.deviation_description:
            detail_rendered = self.detail_font.render(
                self.deviation_description, True, COLORS.GOLD
            )
            detail_rect = detail_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
            surface.blit(detail_rendered, detail_rect)
        elif self.reason:
            detail_rendered = self.detail_font.render(self.reason, True, COLORS.TEXT_MUTED)
            detail_rect = detail_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
            surface.blit(detail_rendered, detail_rect)


class BettingHint(Panel):
    """Panel displaying betting recommendations based on true count.

    Shows recommended bet units and player edge during WAITING_FOR_BET.
    """

    def __init__(
        self,
        x: float,
        y: float,
        width: float = 180,
        **kwargs,
    ):
        kwargs.setdefault("bg_color", (35, 38, 48))
        kwargs.setdefault("bg_alpha", 220)
        kwargs.setdefault("border_color", COLORS.SILVER)
        super().__init__(x, y, width, 130, **kwargs)

        self.visible = False
        self.true_count = 0.0
        self.recommended_units = 1
        self.edge_percentage = 0.0
        self.base_bet = 100
        self.current_bet = 100  # User's current bet amount

        # Animation
        self._pulse_time = 0.0

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._units_font: Optional[pygame.font.Font] = None
        self._detail_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 24)
        return self._title_font

    @property
    def units_font(self) -> pygame.font.Font:
        if self._units_font is None:
            self._units_font = pygame.font.Font(None, 42)
        return self._units_font

    @property
    def detail_font(self) -> pygame.font.Font:
        if self._detail_font is None:
            self._detail_font = pygame.font.Font(None, 22)
        return self._detail_font

    def calculate_recommendation(
        self, true_count: float, base_bet: int = 100, current_bet: int = 100
    ) -> None:
        """Calculate betting recommendation based on true count.

        Uses a simple TC-based spread:
        - TC < 1: 1 unit (no advantage)
        - TC 1-2: 2 units
        - TC 2-3: 4 units
        - TC 3-4: 6 units
        - TC 4-5: 8 units
        - TC 5+: 10-12 units

        Edge approximation: ~0.5% per true count above 0
        """
        self.true_count = true_count
        self.base_bet = base_bet
        self.current_bet = current_bet

        # Calculate units
        if true_count < 1:
            self.recommended_units = 1
        elif true_count < 2:
            self.recommended_units = 2
        elif true_count < 3:
            self.recommended_units = 4
        elif true_count < 4:
            self.recommended_units = 6
        elif true_count < 5:
            self.recommended_units = 8
        elif true_count < 6:
            self.recommended_units = 10
        else:
            self.recommended_units = 12

        # Approximate player edge (rough: 0.5% per TC above 0, minus ~0.5% house edge)
        self.edge_percentage = (true_count - 1) * 0.5

        self._needs_redraw = True

    def show(self) -> None:
        """Show the betting hint panel."""
        self.visible = True

    def hide(self) -> None:
        """Hide the betting hint panel."""
        self.visible = False

    def update(self, dt: float) -> None:
        """Update animation state."""
        self._pulse_time += dt

    def _get_advantage_color(self) -> Tuple[int, int, int]:
        """Get color based on advantage level."""
        if self.edge_percentage <= -0.5:
            return (180, 80, 80)  # Red - disadvantage
        elif self.edge_percentage < 0.5:
            return (200, 180, 80)  # Yellow - neutral
        elif self.edge_percentage < 1.5:
            return (100, 180, 100)  # Green - small advantage
        else:
            return COLORS.GOLD  # Gold - significant advantage

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the betting hint panel."""
        if not self.visible:
            return

        # Pulsing glow for high advantage
        if self.edge_percentage >= 1.5:
            glow_alpha = int(80 + 40 * math.sin(self._pulse_time * 3))
            glow_color = (*COLORS.GOLD, glow_alpha)
            glow_rect = pygame.Rect(
                int(self.x) - 3, int(self.y) - 3,
                int(self.width) + 6, int(self.height) + 6
            )
            glow_surface = pygame.Surface(
                (glow_rect.width, glow_rect.height), pygame.SRCALPHA
            )
            pygame.draw.rect(
                glow_surface, glow_color, glow_surface.get_rect(),
                width=4, border_radius=self.corner_radius + 3
            )
            surface.blit(glow_surface, glow_rect.topleft)

        # Draw base panel
        super().draw(surface)

        y_offset = int(self.y) + DIMENSIONS.PANEL_PADDING - 2

        # Title
        title_rendered = self.title_font.render("BET ADVICE", True, COLORS.TEXT_MUTED)
        title_rect = title_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(title_rendered, title_rect)
        y_offset += 22

        # Current bet in units
        current_units = self.current_bet // self.base_bet if self.base_bet > 0 else 1
        current_bet_text = f"Your bet: {current_units} unit{'s' if current_units != 1 else ''}"
        current_bet_rendered = self.detail_font.render(current_bet_text, True, COLORS.TEXT_WHITE)
        current_bet_rect = current_bet_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(current_bet_rendered, current_bet_rect)
        y_offset += 20

        # Recommended units (large)
        advantage_color = self._get_advantage_color()
        units_text = f"Bet {self.recommended_units} unit{'s' if self.recommended_units != 1 else ''}"
        units_rendered = self.units_font.render(units_text, True, advantage_color)
        units_rect = units_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(units_rendered, units_rect)
        y_offset += 34

        # Dollar amount
        amount = self.recommended_units * self.base_bet
        amount_text = f"(${amount:,})"
        amount_rendered = self.detail_font.render(amount_text, True, COLORS.TEXT_WHITE)
        amount_rect = amount_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(amount_rendered, amount_rect)
        y_offset += 22

        # Edge percentage
        edge_sign = "+" if self.edge_percentage >= 0 else ""
        edge_text = f"Edge: {edge_sign}{self.edge_percentage:.1f}%"
        edge_rendered = self.detail_font.render(edge_text, True, advantage_color)
        edge_rect = edge_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(edge_rendered, edge_rect)


class InsurancePrompt(Panel):
    """Panel prompting for insurance decision when dealer shows Ace."""

    def __init__(
        self,
        x: float,
        y: float,
        **kwargs,
    ):
        kwargs.setdefault("bg_color", (40, 35, 35))
        kwargs.setdefault("bg_alpha", 230)
        kwargs.setdefault("border_color", COLORS.GOLD)
        kwargs.setdefault("border_width", 3)
        super().__init__(x, y, 280, 100, **kwargs)

        self.visible = False
        self.true_count = 0.0
        self.recommend_insurance = False

        # Animation
        self._pulse_time = 0.0

        # Fonts
        self._title_font: Optional[pygame.font.Font] = None
        self._detail_font: Optional[pygame.font.Font] = None

    @property
    def title_font(self) -> pygame.font.Font:
        if self._title_font is None:
            self._title_font = pygame.font.Font(None, 28)
        return self._title_font

    @property
    def detail_font(self) -> pygame.font.Font:
        if self._detail_font is None:
            self._detail_font = pygame.font.Font(None, 22)
        return self._detail_font

    def set_true_count(self, true_count: float) -> None:
        """Set the true count and determine insurance recommendation.

        Insurance is recommended at TC +3 or higher (Illustrious 18 #1).
        """
        self.true_count = true_count
        self.recommend_insurance = true_count >= 3.0
        self._needs_redraw = True

    def show(self) -> None:
        """Show the insurance prompt."""
        self.visible = True

    def hide(self) -> None:
        """Hide the insurance prompt."""
        self.visible = False

    def update(self, dt: float) -> None:
        """Update animation state."""
        self._pulse_time += dt

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the insurance prompt panel."""
        if not self.visible:
            return

        # Draw base panel
        super().draw(surface)

        y_offset = int(self.y) + DIMENSIONS.PANEL_PADDING

        # Title
        title_text = "INSURANCE?"
        title_rendered = self.title_font.render(title_text, True, COLORS.GOLD)
        title_rect = title_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(title_rendered, title_rect)
        y_offset += 30

        # Recommendation
        if self.recommend_insurance:
            rec_text = "TAKE INSURANCE"
            rec_color = COLORS.COUNT_POSITIVE
            reason = f"TC {self.true_count:+.1f} >= +3"
        else:
            rec_text = "DECLINE INSURANCE"
            rec_color = COLORS.COUNT_NEGATIVE
            reason = f"TC {self.true_count:+.1f} < +3"

        rec_rendered = self.title_font.render(rec_text, True, rec_color)
        rec_rect = rec_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(rec_rendered, rec_rect)
        y_offset += 28

        # Reason
        reason_rendered = self.detail_font.render(reason, True, COLORS.TEXT_MUTED)
        reason_rect = reason_rendered.get_rect(centerx=int(self.center_x), top=y_offset)
        surface.blit(reason_rendered, reason_rect)
