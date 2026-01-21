"""House edge calculations."""

from decimal import Decimal

from core.strategy.rules import RuleSet


class HouseEdgeCalculator:
    """
    Calculate house edge based on rule variations.

    Uses the standard baseline of approximately 0.5% for typical rules,
    with adjustments for each rule variation.
    """

    # Rule effects on house edge (in percentage points)
    # Positive = increases house edge (bad for player)
    # Negative = decreases house edge (good for player)
    _RULE_EFFECTS = {
        # Number of decks (baseline is 6)
        "single_deck": Decimal("-0.48"),
        "double_deck": Decimal("-0.19"),
        "four_deck": Decimal("-0.06"),
        "six_deck": Decimal("0.00"),  # Baseline
        "eight_deck": Decimal("+0.02"),
        # Dealer rules
        "h17": Decimal("+0.22"),  # Hit soft 17 vs stand
        # Blackjack payout
        "bj_6_5": Decimal("+1.39"),  # 6:5 vs 3:2
        "bj_1_1": Decimal("+2.27"),  # Even money vs 3:2
        # Double rules
        "no_das": Decimal("+0.14"),  # No double after split
        "double_10_11_only": Decimal("+0.18"),
        "double_9_11_only": Decimal("+0.09"),
        # Split rules
        "no_resplit": Decimal("+0.03"),
        "resplit_aces": Decimal("-0.08"),
        "hit_split_aces": Decimal("-0.19"),
        # Surrender
        "late_surrender": Decimal("-0.08"),
        "early_surrender": Decimal("-0.39"),
        # Other
        "dealer_no_peek": Decimal("+0.11"),  # ENHC rules
    }

    # Baseline house edge with standard Vegas rules
    _BASELINE = Decimal("0.50")  # 0.50% with 6 decks, S17, 3:2 BJ, DAS

    def __init__(self, rules: RuleSet) -> None:
        """
        Initialize calculator with rule set.

        Args:
            rules: The rule set to calculate edge for
        """
        self.rules = rules

    def calculate(self) -> Decimal:
        """
        Calculate the house edge for the configured rules.

        Returns:
            House edge as a percentage (e.g., 0.50 for 0.50%)
        """
        edge = self._BASELINE

        # Deck adjustments
        deck_effects = {
            1: self._RULE_EFFECTS["single_deck"],
            2: self._RULE_EFFECTS["double_deck"],
            4: self._RULE_EFFECTS["four_deck"],
            6: self._RULE_EFFECTS["six_deck"],
            8: self._RULE_EFFECTS["eight_deck"],
        }
        edge += deck_effects.get(self.rules.num_decks, Decimal("0"))

        # H17 vs S17
        if self.rules.dealer_hits_soft_17:
            edge += self._RULE_EFFECTS["h17"]

        # Blackjack payout
        if self.rules.blackjack_payout <= 1.2:  # 6:5
            edge += self._RULE_EFFECTS["bj_6_5"]
        elif self.rules.blackjack_payout <= 1.0:  # Even money
            edge += self._RULE_EFFECTS["bj_1_1"]

        # Double after split
        if not self.rules.double_after_split:
            edge += self._RULE_EFFECTS["no_das"]

        # Double restrictions
        if self.rules.double_on == "10-11":
            edge += self._RULE_EFFECTS["double_10_11_only"]
        elif self.rules.double_on == "9-11":
            edge += self._RULE_EFFECTS["double_9_11_only"]

        # Split rules
        if self.rules.resplit_aces:
            edge += self._RULE_EFFECTS["resplit_aces"]
        if self.rules.hit_split_aces:
            edge += self._RULE_EFFECTS["hit_split_aces"]

        # Surrender
        if self.rules.surrender == "late":
            edge += self._RULE_EFFECTS["late_surrender"]
        elif self.rules.surrender == "early":
            edge += self._RULE_EFFECTS["early_surrender"]

        # Dealer peek
        if not self.rules.dealer_peeks:
            edge += self._RULE_EFFECTS["dealer_no_peek"]

        return edge

    def player_advantage_with_count(
        self,
        true_count: float,
        base_edge: Decimal | None = None,
    ) -> Decimal:
        """
        Calculate player advantage for a given true count.

        Each +1 true count is worth approximately 0.5% to the player.

        Args:
            true_count: The current true count
            base_edge: Base house edge (calculated if not provided)

        Returns:
            Player advantage (positive = player advantage, negative = house edge)
        """
        if base_edge is None:
            base_edge = self.calculate()

        # Each true count point is worth ~0.5%
        tc_value = Decimal("0.5")
        player_advantage = Decimal(str(true_count)) * tc_value - base_edge

        return player_advantage

    def bet_spread_edge(
        self,
        true_count: float,
        min_bet: int,
        max_bet: int,
        spread_tc_threshold: float = 2.0,
    ) -> tuple[int, Decimal]:
        """
        Get optimal bet and expected edge for a given count.

        Args:
            true_count: Current true count
            min_bet: Minimum bet
            max_bet: Maximum bet
            spread_tc_threshold: TC at which to start spreading

        Returns:
            Tuple of (optimal bet, expected edge)
        """
        base_edge = self.calculate()
        player_advantage = self.player_advantage_with_count(true_count, base_edge)

        if true_count < spread_tc_threshold:
            return min_bet, player_advantage

        # Simple bet ramp: 1 unit per true count above threshold
        units = int(true_count - spread_tc_threshold + 1)
        units = min(units, max_bet // min_bet)  # Cap at max spread
        bet = min(units * min_bet, max_bet)

        return bet, player_advantage
