"""Heat map component for visualizing strategy accuracy."""

from typing import Dict, Optional, Tuple, Any, Callable

import pygame

from pygame_ui.config import COLORS


def accuracy_to_color(accuracy: float, total: int) -> Tuple[int, int, int]:
    """Convert accuracy to a color (red -> yellow -> green).

    Args:
        accuracy: Accuracy value 0.0-1.0
        total: Total number of attempts (affects saturation)

    Returns:
        RGB color tuple
    """
    if total == 0:
        return (60, 60, 60)  # Gray for no data

    # Clamp accuracy
    accuracy = max(0.0, min(1.0, accuracy))

    # Calculate saturation based on sample size (more samples = more saturated)
    saturation = min(1.0, total / 20)  # Full saturation at 20+ samples

    if accuracy >= 0.8:
        # Green zone (80-100%)
        intensity = 80 + int(120 * saturation)
        return (40, intensity, 40)
    elif accuracy >= 0.6:
        # Yellow-green zone (60-80%)
        green = 80 + int(120 * saturation)
        red = int(80 * saturation)
        return (red, green, 40)
    elif accuracy >= 0.4:
        # Yellow zone (40-60%)
        intensity = 80 + int(120 * saturation)
        return (intensity, intensity, 40)
    elif accuracy >= 0.2:
        # Orange zone (20-40%)
        red = 80 + int(120 * saturation)
        green = int(80 * saturation)
        return (red, green, 40)
    else:
        # Red zone (0-20%)
        intensity = 80 + int(120 * saturation)
        return (intensity, 40, 40)


class StrategyHeatMap:
    """Heat map showing accuracy for each strategy decision."""

    # Cell dimensions
    CELL_WIDTH = 32
    CELL_HEIGHT = 24
    HEADER_WIDTH = 50

    # Row labels for hard totals
    HARD_ROWS = list(range(20, 7, -1))  # 20 down to 8
    # Row labels for soft totals
    SOFT_ROWS = list(range(20, 12, -1))  # A9 down to A2
    # Row labels for pairs
    PAIR_ROWS = ["A,A", "10,10", "9,9", "8,8", "7,7", "6,6", "5,5", "4,4", "3,3", "2,2"]
    # Column labels (dealer upcards)
    DEALER_COLS = [2, 3, 4, 5, 6, 7, 8, 9, 10, "A"]

    def __init__(
        self,
        x: float,
        y: float,
        width: int = 450,
        height: int = 400,
        on_cell_click: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.on_cell_click = on_cell_click

        # Current display mode: "hard", "soft", "pair"
        self.mode = "hard"

        # Accuracy data: key = "player,dealer,soft,pair" -> stats dict
        self._data: Dict[str, Dict[str, Any]] = {}

        # Hovered cell
        self._hovered_cell: Optional[Tuple[int, int]] = None

        # Fonts
        self._font: Optional[pygame.font.Font] = None
        self._small_font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 20)
        return self._font

    @property
    def small_font(self) -> pygame.font.Font:
        if self._small_font is None:
            self._small_font = pygame.font.Font(None, 16)
        return self._small_font

    def set_data(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Set the accuracy data.

        Args:
            data: Dict mapping "player,dealer,soft,pair" to stats with accuracy, total
        """
        self._data = data

    def set_mode(self, mode: str) -> None:
        """Set display mode: 'hard', 'soft', or 'pair'."""
        if mode in ("hard", "soft", "pair"):
            self.mode = mode

    def _get_rows(self):
        """Get row labels based on current mode."""
        if self.mode == "hard":
            return self.HARD_ROWS
        elif self.mode == "soft":
            return self.SOFT_ROWS
        else:
            return self.PAIR_ROWS

    def _get_cell_key(self, row_idx: int, col_idx: int) -> str:
        """Get the data key for a cell."""
        rows = self._get_rows()
        row_val = rows[row_idx]
        col_val = self.DEALER_COLS[col_idx]

        # Convert to standardized key format
        if self.mode == "pair":
            # Parse pair (e.g., "8,8" -> player_total = 16)
            if row_val == "A,A":
                player_total = 12  # Two aces = soft 12
            elif row_val == "10,10":
                player_total = 20
            else:
                pair_val = int(row_val.split(",")[0])
                player_total = pair_val * 2
            is_soft = row_val == "A,A"
            is_pair = True
        elif self.mode == "soft":
            player_total = row_val
            is_soft = True
            is_pair = False
        else:  # hard
            player_total = row_val
            is_soft = False
            is_pair = False

        dealer_val = 11 if col_val == "A" else col_val

        return f"{player_total},{dealer_val},{is_soft},{is_pair}"

    def _get_cell_rect(self, row_idx: int, col_idx: int) -> pygame.Rect:
        """Get the rectangle for a cell."""
        start_x = self.x - self.width // 2 + self.HEADER_WIDTH
        start_y = self.y - self.height // 2 + 30  # Leave room for column headers

        return pygame.Rect(
            int(start_x + col_idx * self.CELL_WIDTH),
            int(start_y + row_idx * self.CELL_HEIGHT),
            self.CELL_WIDTH - 1,
            self.CELL_HEIGHT - 1,
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle input events."""
        if event.type == pygame.MOUSEMOTION:
            rows = self._get_rows()
            self._hovered_cell = None

            for row_idx in range(len(rows)):
                for col_idx in range(len(self.DEALER_COLS)):
                    rect = self._get_cell_rect(row_idx, col_idx)
                    if rect.collidepoint(event.pos):
                        self._hovered_cell = (row_idx, col_idx)
                        return True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._hovered_cell and self.on_cell_click:
                row_idx, col_idx = self._hovered_cell
                key = self._get_cell_key(row_idx, col_idx)
                if key in self._data:
                    self.on_cell_click(self._data[key])
                return True

        return False

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        rows = self._get_rows()
        start_x = self.x - self.width // 2
        start_y = self.y - self.height // 2

        # Draw column headers (dealer upcards)
        for col_idx, col_val in enumerate(self.DEALER_COLS):
            col_x = start_x + self.HEADER_WIDTH + col_idx * self.CELL_WIDTH + self.CELL_WIDTH // 2
            text = self.font.render(str(col_val), True, COLORS.TEXT_WHITE)
            rect = text.get_rect(center=(col_x, start_y + 15))
            surface.blit(text, rect)

        # Draw "Dealer" label
        dealer_label = self.small_font.render("Dealer", True, COLORS.TEXT_MUTED)
        surface.blit(dealer_label, (start_x + self.HEADER_WIDTH, start_y))

        # Draw row headers and cells
        for row_idx, row_val in enumerate(rows):
            row_y = start_y + 30 + row_idx * self.CELL_HEIGHT + self.CELL_HEIGHT // 2

            # Row header
            label = str(row_val)
            if self.mode == "soft" and isinstance(row_val, int):
                label = f"A{row_val - 11}"  # Soft 17 = A6

            text = self.font.render(label, True, COLORS.TEXT_WHITE)
            rect = text.get_rect(midright=(start_x + self.HEADER_WIDTH - 5, row_y))
            surface.blit(text, rect)

            # Cells
            for col_idx in range(len(self.DEALER_COLS)):
                cell_rect = self._get_cell_rect(row_idx, col_idx)
                key = self._get_cell_key(row_idx, col_idx)

                # Get accuracy data
                if key in self._data:
                    accuracy = self._data[key].get("accuracy", 1.0)
                    total = self._data[key].get("total", 0)
                else:
                    accuracy = 1.0
                    total = 0

                # Cell color based on accuracy
                color = accuracy_to_color(accuracy, total)
                pygame.draw.rect(surface, color, cell_rect)

                # Hover highlight
                if self._hovered_cell == (row_idx, col_idx):
                    pygame.draw.rect(surface, COLORS.GOLD, cell_rect, width=2)

                # Show accuracy percentage if enough data
                if total >= 3:
                    pct_text = f"{int(accuracy * 100)}"
                    pct_surf = self.small_font.render(pct_text, True, COLORS.TEXT_WHITE)
                    pct_rect = pct_surf.get_rect(center=cell_rect.center)
                    surface.blit(pct_surf, pct_rect)

        # Draw mode label
        mode_labels = {"hard": "Hard Totals", "soft": "Soft Totals", "pair": "Pairs"}
        mode_text = self.font.render(mode_labels[self.mode], True, COLORS.GOLD)
        mode_rect = mode_text.get_rect(center=(self.x, start_y - 15))
        surface.blit(mode_text, mode_rect)

        # Draw legend
        legend_y = start_y + len(rows) * self.CELL_HEIGHT + 50
        legend_items = [
            ((180, 40, 40), "0-20%"),
            ((160, 80, 40), "20-40%"),
            ((160, 160, 40), "40-60%"),
            ((80, 160, 40), "60-80%"),
            ((40, 180, 40), "80-100%"),
            ((60, 60, 60), "No data"),
        ]

        legend_x = start_x
        for color, label in legend_items:
            pygame.draw.rect(surface, color, (legend_x, legend_y, 15, 15))
            text = self.small_font.render(label, True, COLORS.TEXT_MUTED)
            surface.blit(text, (legend_x + 20, legend_y))
            legend_x += 70


class MiniHeatMap:
    """Compact heat map for summary display."""

    CELL_SIZE = 8

    def __init__(
        self,
        x: float,
        y: float,
        width: int = 120,
        height: int = 100,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self._data: Dict[str, Dict[str, Any]] = {}

    def set_data(self, data: Dict[str, Dict[str, Any]]) -> None:
        self._data = data

    def get_overall_accuracy(self) -> float:
        """Calculate overall accuracy across all situations."""
        total_correct = sum(d.get("correct", 0) for d in self._data.values())
        total_incorrect = sum(d.get("incorrect", 0) for d in self._data.values())
        total = total_correct + total_incorrect
        return total_correct / total if total > 0 else 1.0

    def draw(self, surface: pygame.Surface) -> None:
        # Draw a simplified 10x10 grid representing overall accuracy distribution
        start_x = self.x - self.width // 2
        start_y = self.y - self.height // 2

        # Group data by accuracy ranges
        ranges = [0, 0, 0, 0, 0]  # 0-20, 20-40, 40-60, 60-80, 80-100
        for stats in self._data.values():
            acc = stats.get("accuracy", 1.0)
            total = stats.get("total", 0)
            if total > 0:
                idx = min(4, int(acc * 5))
                ranges[idx] += 1

        # Draw as stacked bar
        total_situations = sum(ranges)
        if total_situations > 0:
            bar_x = start_x
            colors = [
                (180, 40, 40),
                (160, 80, 40),
                (160, 160, 40),
                (80, 160, 40),
                (40, 180, 40),
            ]
            for i, count in enumerate(ranges):
                bar_width = int(self.width * count / total_situations)
                if bar_width > 0:
                    pygame.draw.rect(
                        surface,
                        colors[i],
                        (bar_x, start_y, bar_width, 20),
                    )
                    bar_x += bar_width

            # Border
            pygame.draw.rect(
                surface,
                COLORS.TEXT_MUTED,
                (start_x, start_y, self.width, 20),
                width=1,
            )
