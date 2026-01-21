"""Basic strategy tables for blackjack."""

from enum import Enum, auto
from typing import Mapping

from core.strategy.rules import RuleSet


class Action(Enum):
    """Possible player actions."""

    HIT = auto()
    STAND = auto()
    DOUBLE = auto()
    SPLIT = auto()
    SURRENDER = auto()

    # Conditional actions (fallback if primary not allowed)
    DOUBLE_OR_HIT = auto()  # Double if allowed, else hit
    DOUBLE_OR_STAND = auto()  # Double if allowed, else stand
    SURRENDER_OR_HIT = auto()  # Surrender if allowed, else hit
    SURRENDER_OR_STAND = auto()  # Surrender if allowed, else stand
    SURRENDER_OR_SPLIT = auto()  # Surrender if allowed, else split

    def __str__(self) -> str:
        return self.name.replace("_", "/")


# Type aliases for clarity
DealerUpcard = int  # 2-11 (11 = Ace)
PlayerTotal = int  # Hard total or soft total value
HandKey = tuple[str, int]  # ("hard", 16) or ("soft", 17) or ("pair", 8)


class BasicStrategy:
    """
    Basic strategy lookup tables.

    Pre-computed dictionaries for O(1) lookup.
    Tables vary based on rule set (H17/S17, DAS, surrender, etc.)
    """

    def __init__(self, rules: RuleSet | None = None) -> None:
        """
        Initialize basic strategy for given rules.

        Args:
            rules: Rule set to generate strategy for. Uses default if None.
        """
        self.rules = rules or RuleSet()
        self._hard_table = self._build_hard_table()
        self._soft_table = self._build_soft_table()
        self._pair_table = self._build_pair_table()

    def get_action(
        self,
        player_total: int,
        dealer_upcard: int,
        is_soft: bool = False,
        is_pair: bool = False,
        pair_rank: int | None = None,
        can_double: bool = True,
        can_surrender: bool = True,
        can_split: bool = True,
    ) -> Action:
        """
        Get the basic strategy action.

        Args:
            player_total: Player's hand total
            dealer_upcard: Dealer's upcard value (2-11, Ace=11)
            is_soft: Whether the hand is soft
            is_pair: Whether the hand is a pair
            pair_rank: The rank value of the pair (for pair decisions)
            can_double: Whether doubling is allowed
            can_surrender: Whether surrender is allowed
            can_split: Whether splitting is allowed

        Returns:
            The recommended action
        """
        # Check for pairs first
        if is_pair and can_split and pair_rank is not None:
            action = self._pair_table.get((pair_rank, dealer_upcard))
            if action:
                return self._resolve_action(
                    action, can_double, can_surrender, can_split
                )

        # Check soft hands
        if is_soft:
            action = self._soft_table.get((player_total, dealer_upcard))
            if action:
                return self._resolve_action(
                    action, can_double, can_surrender, can_split=False
                )

        # Hard hands
        action = self._hard_table.get((player_total, dealer_upcard))
        if action:
            return self._resolve_action(
                action, can_double, can_surrender, can_split=False
            )

        # Default actions for edge cases
        if player_total >= 17:
            return Action.STAND
        return Action.HIT

    def _resolve_action(
        self,
        action: Action,
        can_double: bool,
        can_surrender: bool,
        can_split: bool,
    ) -> Action:
        """Resolve conditional actions based on what's allowed."""
        if action == Action.DOUBLE_OR_HIT:
            return Action.DOUBLE if can_double else Action.HIT
        if action == Action.DOUBLE_OR_STAND:
            return Action.DOUBLE if can_double else Action.STAND
        if action == Action.SURRENDER_OR_HIT:
            return Action.SURRENDER if can_surrender else Action.HIT
        if action == Action.SURRENDER_OR_STAND:
            return Action.SURRENDER if can_surrender else Action.STAND
        if action == Action.SURRENDER_OR_SPLIT:
            return Action.SURRENDER if can_surrender else Action.SPLIT
        if action == Action.SPLIT and not can_split:
            return Action.HIT
        if action == Action.DOUBLE and not can_double:
            return Action.HIT
        if action == Action.SURRENDER and not can_surrender:
            return Action.HIT
        return action

    def _build_hard_table(self) -> Mapping[tuple[int, int], Action]:
        """Build hard totals strategy table."""
        H = Action.HIT
        S = Action.STAND
        D = Action.DOUBLE_OR_HIT
        Ds = Action.DOUBLE_OR_STAND
        Rh = Action.SURRENDER_OR_HIT
        Rs = Action.SURRENDER_OR_STAND

        # Dealer upcards: 2, 3, 4, 5, 6, 7, 8, 9, 10, A(11)
        table: dict[tuple[int, int], Action] = {}

        # Hard 5-8: Always hit
        for total in range(5, 9):
            for dealer in range(2, 12):
                table[(total, dealer)] = H

        # Hard 9
        for dealer in [2, 7, 8, 9, 10, 11]:
            table[(9, dealer)] = H
        for dealer in [3, 4, 5, 6]:
            table[(9, dealer)] = D

        # Hard 10
        for dealer in [10, 11]:
            table[(10, dealer)] = H
        for dealer in range(2, 10):
            table[(10, dealer)] = D

        # Hard 11
        for dealer in range(2, 12):
            table[(11, dealer)] = D

        # Hard 12
        table[(12, 2)] = H
        table[(12, 3)] = H
        for dealer in [4, 5, 6]:
            table[(12, dealer)] = S
        for dealer in range(7, 12):
            table[(12, dealer)] = H

        # Hard 13-16
        for total in range(13, 17):
            for dealer in range(2, 7):
                table[(total, dealer)] = S
            for dealer in range(7, 12):
                table[(total, dealer)] = H

        # Surrender adjustments for 15 and 16 (if H17 rules)
        if self.rules.surrender != "none":
            if self.rules.dealer_hits_soft_17:
                table[(15, 10)] = Rh
                table[(15, 11)] = Rh  # Surrender vs Ace with H17
                table[(16, 9)] = Rh
                table[(16, 10)] = Rh
                table[(16, 11)] = Rh
            else:
                table[(15, 10)] = Rh
                table[(16, 9)] = Rh
                table[(16, 10)] = Rh
                table[(16, 11)] = Rh

        # Hard 17+: Always stand
        for total in range(17, 22):
            for dealer in range(2, 12):
                table[(total, dealer)] = S

        return table

    def _build_soft_table(self) -> Mapping[tuple[int, int], Action]:
        """Build soft totals strategy table."""
        H = Action.HIT
        S = Action.STAND
        D = Action.DOUBLE_OR_HIT
        Ds = Action.DOUBLE_OR_STAND

        table: dict[tuple[int, int], Action] = {}

        # Soft 13 (A,2)
        for dealer in [2, 3, 7, 8, 9, 10, 11]:
            table[(13, dealer)] = H
        for dealer in [5, 6]:
            table[(13, dealer)] = D
        table[(13, 4)] = H

        # Soft 14 (A,3)
        for dealer in [2, 3, 7, 8, 9, 10, 11]:
            table[(14, dealer)] = H
        for dealer in [5, 6]:
            table[(14, dealer)] = D
        table[(14, 4)] = H

        # Soft 15 (A,4)
        for dealer in [2, 3, 7, 8, 9, 10, 11]:
            table[(15, dealer)] = H
        for dealer in [4, 5, 6]:
            table[(15, dealer)] = D

        # Soft 16 (A,5)
        for dealer in [2, 3, 7, 8, 9, 10, 11]:
            table[(16, dealer)] = H
        for dealer in [4, 5, 6]:
            table[(16, dealer)] = D

        # Soft 17 (A,6)
        for dealer in [2, 7, 8, 9, 10, 11]:
            table[(17, dealer)] = H
        for dealer in [3, 4, 5, 6]:
            table[(17, dealer)] = D

        # Soft 18 (A,7)
        table[(18, 2)] = Ds
        for dealer in [3, 4, 5, 6]:
            table[(18, dealer)] = Ds
        for dealer in [7, 8]:
            table[(18, dealer)] = S
        for dealer in [9, 10, 11]:
            table[(18, dealer)] = H

        # Soft 19 (A,8)
        for dealer in range(2, 12):
            table[(19, dealer)] = S
        # Special case: Double vs 6 with some rules
        if self.rules.dealer_hits_soft_17:
            table[(19, 6)] = Ds

        # Soft 20 (A,9): Always stand
        for dealer in range(2, 12):
            table[(20, dealer)] = S

        # Soft 21 (A,10): Always stand (blackjack handled separately)
        for dealer in range(2, 12):
            table[(21, dealer)] = S

        return table

    def _build_pair_table(self) -> Mapping[tuple[int, int], Action]:
        """Build pair splitting strategy table."""
        H = Action.HIT
        S = Action.STAND
        P = Action.SPLIT
        D = Action.DOUBLE_OR_HIT
        Rp = Action.SURRENDER_OR_SPLIT

        table: dict[tuple[int, int], Action] = {}

        # Pair of 2s
        for dealer in [2, 3]:
            table[(2, dealer)] = P if self.rules.double_after_split else H
        for dealer in [4, 5, 6, 7]:
            table[(2, dealer)] = P
        for dealer in [8, 9, 10, 11]:
            table[(2, dealer)] = H

        # Pair of 3s
        for dealer in [2, 3]:
            table[(3, dealer)] = P if self.rules.double_after_split else H
        for dealer in [4, 5, 6, 7]:
            table[(3, dealer)] = P
        for dealer in [8, 9, 10, 11]:
            table[(3, dealer)] = H

        # Pair of 4s
        for dealer in [2, 3, 4, 7, 8, 9, 10, 11]:
            table[(4, dealer)] = H
        for dealer in [5, 6]:
            table[(4, dealer)] = P if self.rules.double_after_split else H

        # Pair of 5s: Never split, treat as hard 10
        for dealer in range(2, 12):
            table[(5, dealer)] = D

        # Pair of 6s
        for dealer in [2]:
            table[(6, dealer)] = P if self.rules.double_after_split else H
        for dealer in [3, 4, 5, 6]:
            table[(6, dealer)] = P
        for dealer in [7, 8, 9, 10, 11]:
            table[(6, dealer)] = H

        # Pair of 7s
        for dealer in range(2, 8):
            table[(7, dealer)] = P
        for dealer in [8, 9, 10, 11]:
            table[(7, dealer)] = H

        # Pair of 8s: Always split
        for dealer in range(2, 12):
            table[(8, dealer)] = P
        # Surrender vs 10, A if allowed
        if self.rules.surrender != "none":
            table[(8, 10)] = Rp if self.rules.dealer_hits_soft_17 else P
            table[(8, 11)] = Rp if self.rules.dealer_hits_soft_17 else P

        # Pair of 9s
        for dealer in [2, 3, 4, 5, 6, 8, 9]:
            table[(9, dealer)] = P
        for dealer in [7, 10, 11]:
            table[(9, dealer)] = S

        # Pair of 10s: Never split
        for dealer in range(2, 12):
            table[(10, dealer)] = S

        # Pair of Aces: Always split
        for dealer in range(2, 12):
            table[(11, dealer)] = P

        return table

    @property
    def hard_table(self) -> Mapping[tuple[int, int], Action]:
        """Return the hard totals strategy table."""
        return self._hard_table

    @property
    def soft_table(self) -> Mapping[tuple[int, int], Action]:
        """Return the soft totals strategy table."""
        return self._soft_table

    @property
    def pair_table(self) -> Mapping[tuple[int, int], Action]:
        """Return the pair splitting strategy table."""
        return self._pair_table
