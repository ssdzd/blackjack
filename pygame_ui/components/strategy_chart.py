"""Strategy chart grid component for displaying basic strategy tables."""

from typing import Optional, Tuple, List

import pygame

from pygame_ui.config import COLORS, DIMENSIONS
from core.strategy.basic import Action


# Color mapping for actions
ACTION_COLORS = {
    Action.HIT: (70, 130, 70),           # Green
    Action.STAND: (120, 120, 130),        # Gray
    Action.DOUBLE: (70, 100, 150),        # Blue
    Action.DOUBLE_OR_HIT: (70, 100, 150), # Blue
    Action.DOUBLE_OR_STAND: (70, 100, 150), # Blue
    Action.SPLIT: (180, 120, 50),         # Orange
    Action.SURRENDER: (150, 60, 60),      # Red
    Action.SURRENDER_OR_HIT: (150, 60, 60), # Red
    Action.SURRENDER_OR_STAND: (150, 60, 60), # Red
    Action.SURRENDER_OR_SPLIT: (150, 60, 60), # Red
}

# Short labels for actions
ACTION_LABELS = {
    Action.HIT: "H",
    Action.STAND: "S",
    Action.DOUBLE: "D",
    Action.DOUBLE_OR_HIT: "Dh",
    Action.DOUBLE_OR_STAND: "Ds",
    Action.SPLIT: "P",
    Action.SURRENDER: "R",
    Action.SURRENDER_OR_HIT: "Rh",
    Action.SURRENDER_OR_STAND: "Rs",
    Action.SURRENDER_OR_SPLIT: "Rp",
}


class StrategyChartGrid:
    """Grid component for displaying a basic strategy table.

    Displays a grid with dealer upcards on X-axis and player totals on Y-axis.
    Cells are color-coded by action type.
    """

    def __init__(
        self,
        x: float,
        y: float,
        cell_size: int = 35,
        centered: bool = True,
    ):
        """Initialize the strategy chart grid.

        Args:
            x: X position
            y: Y position
            cell_size: Size of each cell
            centered: Whether position is center of grid
        """
        self.cell_size = cell_size
        self.centered = centered
        self.padding = 8

        # Grid data
        self.table_type = "hard"  # "hard", "soft", "pairs"
        self.data: dict[Tuple[int, int], Action] = {}
        self.row_labels: List[str] = []
        self.col_labels: List[str] = []

        # Highlight
        self.highlight_cell: Optional[Tuple[int, int]] = None  # (row, col)

        # Position
        self._x = x
        self._y = y
        self._update_dimensions()

        # Fonts
        self._label_font: Optional[pygame.font.Font] = None
        self._cell_font: Optional[pygame.font.Font] = None

        # Cache
        self._surface: Optional[pygame.Surface] = None
        self._needs_redraw = True

    @property
    def label_font(self) -> pygame.font.Font:
        if self._label_font is None:
            self._label_font = pygame.font.Font(None, 20)
        return self._label_font

    @property
    def cell_font(self) -> pygame.font.Font:
        if self._cell_font is None:
            self._cell_font = pygame.font.Font(None, 22)
        return self._cell_font

    def _update_dimensions(self) -> None:
        """Update width/height based on grid dimensions."""
        num_cols = len(self.col_labels) + 1  # +1 for row labels
        num_rows = len(self.row_labels) + 1  # +1 for col labels
        self.width = num_cols * self.cell_size + self.padding * 2
        self.height = num_rows * self.cell_size + self.padding * 2

        if self.centered:
            self.x = self._x - self.width / 2
            self.y = self._y - self.height / 2
        else:
            self.x = self._x
            self.y = self._y

    def set_hard_table(self, table: dict[Tuple[int, int], Action]) -> None:
        """Set up for hard totals display.

        Args:
            table: Hard totals strategy table {(total, dealer): action}
        """
        self.table_type = "hard"
        self.data = table

        # Hard totals: 8-17 (or 5-17 for full range)
        self.row_labels = [str(t) for t in range(17, 7, -1)]  # 17 down to 8

        # Dealer upcards: 2-10, A
        self.col_labels = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "A"]

        self._update_dimensions()
        self._needs_redraw = True

    def set_soft_table(self, table: dict[Tuple[int, int], Action]) -> None:
        """Set up for soft totals display.

        Args:
            table: Soft totals strategy table {(total, dealer): action}
        """
        self.table_type = "soft"
        self.data = table

        # Soft totals: A,2 (13) to A,9 (20)
        self.row_labels = ["A,9", "A,8", "A,7", "A,6", "A,5", "A,4", "A,3", "A,2"]

        # Dealer upcards: 2-10, A
        self.col_labels = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "A"]

        self._update_dimensions()
        self._needs_redraw = True

    def set_pair_table(self, table: dict[Tuple[int, int], Action]) -> None:
        """Set up for pairs display.

        Args:
            table: Pairs strategy table {(rank, dealer): action}
        """
        self.table_type = "pairs"
        self.data = table

        # Pairs: A,A down to 2,2
        self.row_labels = ["A,A", "10,10", "9,9", "8,8", "7,7", "6,6", "5,5", "4,4", "3,3", "2,2"]

        # Dealer upcards: 2-10, A
        self.col_labels = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "A"]

        self._update_dimensions()
        self._needs_redraw = True

    def set_highlight(self, player_value: int, dealer_upcard: int, is_soft: bool = False, is_pair: bool = False) -> None:
        """Set the cell to highlight.

        Args:
            player_value: Player hand value or pair rank
            dealer_upcard: Dealer upcard value (2-11)
            is_soft: Whether it's a soft hand
            is_pair: Whether it's a pair
        """
        # Find row index
        row_idx = None
        if self.table_type == "hard":
            if 8 <= player_value <= 17:
                row_idx = 17 - player_value
        elif self.table_type == "soft":
            # Soft totals 13-20 map to rows
            if 13 <= player_value <= 20:
                row_idx = 20 - player_value
        elif self.table_type == "pairs":
            # Pair rank: 2-11
            pair_map = {11: 0, 10: 1, 9: 2, 8: 3, 7: 4, 6: 5, 5: 6, 4: 7, 3: 8, 2: 9}
            row_idx = pair_map.get(player_value)

        # Find col index (dealer upcard)
        col_idx = None
        if dealer_upcard == 11:  # Ace
            col_idx = 9
        elif 2 <= dealer_upcard <= 10:
            col_idx = dealer_upcard - 2

        if row_idx is not None and col_idx is not None:
            self.highlight_cell = (row_idx, col_idx)
        else:
            self.highlight_cell = None

        self._needs_redraw = True

    def clear_highlight(self) -> None:
        """Clear the highlight."""
        self.highlight_cell = None
        self._needs_redraw = True

    def _get_cell_action(self, row_idx: int, col_idx: int) -> Optional[Action]:
        """Get the action for a cell position."""
        # Convert row label to total/rank
        if self.table_type == "hard":
            total = 17 - row_idx
        elif self.table_type == "soft":
            total = 20 - row_idx
        elif self.table_type == "pairs":
            rank_map = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
            if row_idx < len(rank_map):
                total = rank_map[row_idx]
            else:
                return None
        else:
            return None

        # Convert col to dealer upcard
        if col_idx == 9:
            dealer = 11  # Ace
        else:
            dealer = col_idx + 2

        return self.data.get((total, dealer))

    def _render(self) -> pygame.Surface:
        """Render the chart to a surface."""
        surface = pygame.Surface((int(self.width), int(self.height)), pygame.SRCALPHA)

        # Background
        pygame.draw.rect(
            surface,
            (*COLORS.PANEL_BG, 230),
            surface.get_rect(),
            border_radius=8,
        )

        # Border
        pygame.draw.rect(
            surface,
            COLORS.PANEL_BORDER,
            surface.get_rect(),
            width=2,
            border_radius=8,
        )

        # Draw column headers
        for col_idx, label in enumerate(self.col_labels):
            cell_x = self.padding + (col_idx + 1) * self.cell_size
            cell_y = self.padding
            text = self.label_font.render(label, True, COLORS.GOLD)
            text_rect = text.get_rect(
                center=(cell_x + self.cell_size // 2, cell_y + self.cell_size // 2)
            )
            surface.blit(text, text_rect)

        # Draw row headers and cells
        for row_idx, row_label in enumerate(self.row_labels):
            row_y = self.padding + (row_idx + 1) * self.cell_size

            # Row label
            text = self.label_font.render(row_label, True, COLORS.GOLD)
            text_rect = text.get_rect(
                center=(self.padding + self.cell_size // 2, row_y + self.cell_size // 2)
            )
            surface.blit(text, text_rect)

            # Cells
            for col_idx in range(len(self.col_labels)):
                cell_x = self.padding + (col_idx + 1) * self.cell_size

                action = self._get_cell_action(row_idx, col_idx)
                if action:
                    # Cell background
                    cell_color = ACTION_COLORS.get(action, (80, 80, 80))
                    cell_rect = pygame.Rect(cell_x + 1, row_y + 1, self.cell_size - 2, self.cell_size - 2)
                    pygame.draw.rect(surface, cell_color, cell_rect, border_radius=3)

                    # Highlight border
                    if self.highlight_cell == (row_idx, col_idx):
                        pygame.draw.rect(
                            surface,
                            COLORS.GLOW_HIGHLIGHT,
                            cell_rect.inflate(4, 4),
                            width=3,
                            border_radius=4,
                        )

                    # Cell text
                    label = ACTION_LABELS.get(action, "?")
                    text = self.cell_font.render(label, True, COLORS.TEXT_WHITE)
                    text_rect = text.get_rect(
                        center=(cell_x + self.cell_size // 2, row_y + self.cell_size // 2)
                    )
                    surface.blit(text, text_rect)

        return surface

    def update(self, dt: float) -> None:
        """Update animation state."""
        pass

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the chart."""
        if self._needs_redraw or self._surface is None:
            self._surface = self._render()
            self._needs_redraw = False

        surface.blit(self._surface, (int(self.x), int(self.y)))


class StrategyChartTabs:
    """Tab bar for switching between chart types."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float = 400,
        height: float = 40,
    ):
        self.x = x - width / 2
        self.y = y
        self.width = width
        self.height = height

        self.tabs = ["HARD", "SOFT", "PAIRS"]
        self.selected_tab = 0

        self._font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 28)
        return self._font

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle click events on tabs.

        Returns:
            True if a tab was clicked
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.y <= my <= self.y + self.height:
                tab_width = self.width / len(self.tabs)
                for i in range(len(self.tabs)):
                    tab_x = self.x + i * tab_width
                    if tab_x <= mx <= tab_x + tab_width:
                        if self.selected_tab != i:
                            self.selected_tab = i
                            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the tab bar."""
        tab_width = self.width / len(self.tabs)

        for i, tab_name in enumerate(self.tabs):
            tab_x = self.x + i * tab_width
            tab_rect = pygame.Rect(tab_x, self.y, tab_width, self.height)

            # Background
            if i == self.selected_tab:
                color = COLORS.GOLD_DARK
            else:
                color = COLORS.PANEL_BG

            pygame.draw.rect(surface, color, tab_rect, border_radius=6)

            # Border
            pygame.draw.rect(
                surface, COLORS.PANEL_BORDER, tab_rect, width=1, border_radius=6
            )

            # Text
            text_color = COLORS.TEXT_WHITE if i == self.selected_tab else COLORS.TEXT_MUTED
            text = self.font.render(tab_name, True, text_color)
            text_rect = text.get_rect(center=tab_rect.center)
            surface.blit(text, text_rect)


class StrategyChartLegend:
    """Legend showing action color mappings."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self._font: Optional[pygame.font.Font] = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, 22)
        return self._font

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the legend."""
        items = [
            ("H", "Hit", Action.HIT),
            ("S", "Stand", Action.STAND),
            ("D", "Double", Action.DOUBLE),
            ("P", "Split", Action.SPLIT),
            ("R", "Surrender", Action.SURRENDER),
        ]

        spacing = 100
        start_x = self.x - (len(items) * spacing) / 2

        for i, (abbrev, name, action) in enumerate(items):
            item_x = start_x + i * spacing

            # Color box
            box_rect = pygame.Rect(item_x, self.y, 20, 20)
            pygame.draw.rect(
                surface,
                ACTION_COLORS.get(action, (80, 80, 80)),
                box_rect,
                border_radius=3,
            )

            # Label
            text = self.font.render(f"{abbrev}={name}", True, COLORS.TEXT_MUTED)
            surface.blit(text, (item_x + 25, self.y + 2))
