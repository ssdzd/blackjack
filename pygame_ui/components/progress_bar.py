"""Progress bar component for session goals and other progress tracking."""

from typing import Optional, Tuple

import pygame

from pygame_ui.config import COLORS


class SessionProgressBar:
    """Dual progress bar showing win goal and loss limit progress."""

    def __init__(
        self,
        x: float,
        y: float,
        width: int = 200,
        height: int = 16,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # Progress values (0-1)
        self.win_progress = 0.0
        self.loss_progress = 0.0

        # Goal values for display
        self.win_goal = 0
        self.loss_limit = 0
        self.current_profit = 0.0

        # Visual state
        self._visible = False
        self._pulse_time = 0.0

        # Font
        self._font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 20)
        return self._font

    def set_goals(self, win_goal: int, loss_limit: int) -> None:
        """Set the session goals."""
        self.win_goal = win_goal
        self.loss_limit = loss_limit
        self._visible = win_goal > 0 or loss_limit > 0

    def update_progress(self, profit: float) -> None:
        """Update progress based on current profit/loss."""
        self.current_profit = profit

        if self.win_goal > 0 and profit > 0:
            self.win_progress = min(1.0, profit / self.win_goal)
        else:
            self.win_progress = 0.0

        if self.loss_limit > 0 and profit < 0:
            self.loss_progress = min(1.0, abs(profit) / self.loss_limit)
        else:
            self.loss_progress = 0.0

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False

    def update(self, dt: float) -> None:
        self._pulse_time += dt

    def draw(self, surface: pygame.Surface) -> None:
        if not self._visible:
            return

        bar_y = self.y

        # Draw win progress (green, left side)
        if self.win_goal > 0:
            self._draw_single_bar(
                surface,
                self.x - self.width // 2 - 10,
                bar_y,
                self.width // 2,
                self.win_progress,
                (80, 180, 80),
                (40, 80, 40),
                f"+${self.win_goal}",
                align_right=True,
            )

        # Draw loss progress (red, right side)
        if self.loss_limit > 0:
            self._draw_single_bar(
                surface,
                self.x + 10,
                bar_y,
                self.width // 2,
                self.loss_progress,
                (180, 80, 80),
                (80, 40, 40),
                f"-${self.loss_limit}",
                align_right=False,
            )

        # Draw current profit/loss in center
        profit_color = (100, 200, 100) if self.current_profit >= 0 else (200, 100, 100)
        profit_text = f"${self.current_profit:+.0f}"
        profit_surface = self.font.render(profit_text, True, profit_color)
        profit_rect = profit_surface.get_rect(center=(self.x, bar_y))
        surface.blit(profit_surface, profit_rect)

    def _draw_single_bar(
        self,
        surface: pygame.Surface,
        x: float,
        y: float,
        width: int,
        progress: float,
        fill_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int],
        label: str,
        align_right: bool,
    ) -> None:
        """Draw a single progress bar."""
        bar_rect = pygame.Rect(int(x), int(y - self.height // 2), width, self.height)

        # Background
        pygame.draw.rect(surface, bg_color, bar_rect, border_radius=4)

        # Fill
        fill_width = int(width * progress)
        if fill_width > 0:
            if align_right:
                fill_rect = pygame.Rect(
                    int(x + width - fill_width),
                    int(y - self.height // 2),
                    fill_width,
                    self.height,
                )
            else:
                fill_rect = pygame.Rect(
                    int(x),
                    int(y - self.height // 2),
                    fill_width,
                    self.height,
                )
            pygame.draw.rect(surface, fill_color, fill_rect, border_radius=4)

        # Border
        pygame.draw.rect(surface, COLORS.TEXT_MUTED, bar_rect, width=1, border_radius=4)

        # Pulsing effect when approaching limit (80%+)
        if progress >= 0.8:
            pulse = abs(pygame.math.Vector2(1, 0).rotate(self._pulse_time * 360).x)
            highlight = (
                min(255, fill_color[0] + int(75 * pulse)),
                min(255, fill_color[1] + int(75 * pulse)),
                min(255, fill_color[2] + int(75 * pulse)),
            )
            pygame.draw.rect(surface, highlight, bar_rect, width=2, border_radius=4)

        # Label
        if align_right:
            label_pos = (x - 5, y)
            label_surface = self.font.render(label, True, COLORS.TEXT_MUTED)
            label_rect = label_surface.get_rect(midright=label_pos)
        else:
            label_pos = (x + width + 5, y)
            label_surface = self.font.render(label, True, COLORS.TEXT_MUTED)
            label_rect = label_surface.get_rect(midleft=label_pos)
        surface.blit(label_surface, label_rect)


class SimpleProgressBar:
    """Simple single progress bar for general use."""

    def __init__(
        self,
        x: float,
        y: float,
        width: int = 200,
        height: int = 20,
        fill_color: Tuple[int, int, int] = (80, 130, 80),
        bg_color: Tuple[int, int, int] = (40, 40, 45),
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.bg_color = bg_color

        self.progress = 0.0
        self.label = ""
        self._visible = True

        self._font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 24)
        return self._font

    def set_progress(self, progress: float, label: str = "") -> None:
        """Set progress (0-1) and optional label."""
        self.progress = max(0, min(1, progress))
        self.label = label

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        if not self._visible:
            return

        bar_rect = pygame.Rect(
            int(self.x - self.width // 2),
            int(self.y - self.height // 2),
            self.width,
            self.height,
        )

        # Background
        pygame.draw.rect(surface, self.bg_color, bar_rect, border_radius=4)

        # Fill
        fill_width = int(self.width * self.progress)
        if fill_width > 0:
            fill_rect = pygame.Rect(
                int(self.x - self.width // 2),
                int(self.y - self.height // 2),
                fill_width,
                self.height,
            )
            pygame.draw.rect(surface, self.fill_color, fill_rect, border_radius=4)

        # Border
        pygame.draw.rect(surface, COLORS.TEXT_MUTED, bar_rect, width=1, border_radius=4)

        # Label (centered)
        if self.label:
            label_surface = self.font.render(self.label, True, COLORS.TEXT_WHITE)
            label_rect = label_surface.get_rect(center=(self.x, self.y))
            surface.blit(label_surface, label_rect)
