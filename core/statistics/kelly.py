"""Kelly criterion calculations for optimal bet sizing."""

from decimal import Decimal


class KellyCalculator:
    """
    Calculate optimal bet sizes using the Kelly criterion.

    The Kelly criterion maximizes the expected logarithm of wealth,
    providing the optimal bet size for long-term bankroll growth.
    """

    def __init__(
        self,
        bankroll: Decimal,
        min_bet: Decimal,
        max_bet: Decimal,
        kelly_fraction: float = 1.0,
    ) -> None:
        """
        Initialize the Kelly calculator.

        Args:
            bankroll: Current bankroll
            min_bet: Table minimum bet
            max_bet: Table maximum bet
            kelly_fraction: Fraction of Kelly to use (0.5 = half Kelly)
        """
        self.bankroll = bankroll
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.kelly_fraction = kelly_fraction

    def optimal_bet(
        self,
        player_edge: Decimal,
        win_probability: Decimal | None = None,
    ) -> Decimal:
        """
        Calculate the Kelly-optimal bet size.

        For blackjack with approximately even-money payouts:
        Kelly bet = edge * bankroll

        Args:
            player_edge: Player's edge as a decimal (e.g., 0.01 for 1%)
            win_probability: Optional win probability (uses edge/2 + 0.5 if not provided)

        Returns:
            Optimal bet size
        """
        if player_edge <= 0:
            return self.min_bet

        # Full Kelly for even-money bets: edge * bankroll
        # For general case: (bp - q) / b where b=payout, p=win prob, q=lose prob
        # For blackjack, approximate as edge * bankroll
        full_kelly = player_edge * self.bankroll

        # Apply Kelly fraction
        optimal = full_kelly * Decimal(str(self.kelly_fraction))

        # Clamp to table limits
        optimal = max(self.min_bet, min(optimal, self.max_bet))

        return optimal.quantize(Decimal("1"))  # Round to whole units

    def kelly_with_variance(
        self,
        player_edge: Decimal,
        variance: Decimal = Decimal("1.3"),
    ) -> Decimal:
        """
        Calculate Kelly bet accounting for blackjack variance.

        Blackjack has higher variance than a simple coin flip due to
        doubles, splits, and blackjack payouts. Variance is typically ~1.3.

        Args:
            player_edge: Player's edge as a decimal
            variance: Game variance (default 1.3 for blackjack)

        Returns:
            Variance-adjusted optimal bet
        """
        if player_edge <= 0:
            return self.min_bet

        # Variance-adjusted Kelly: edge / variance * bankroll
        full_kelly = (player_edge / variance) * self.bankroll
        optimal = full_kelly * Decimal(str(self.kelly_fraction))

        return max(self.min_bet, min(optimal, self.max_bet)).quantize(Decimal("1"))

    def bet_for_true_count(
        self,
        true_count: float,
        base_house_edge: Decimal = Decimal("0.005"),
    ) -> Decimal:
        """
        Calculate optimal bet for a given true count.

        Args:
            true_count: Current true count
            base_house_edge: House edge at TC 0 (default 0.5%)

        Returns:
            Optimal bet size
        """
        # Player edge = TC * 0.5% - house edge
        edge_per_tc = Decimal("0.005")
        player_edge = Decimal(str(true_count)) * edge_per_tc - base_house_edge

        return self.optimal_bet(player_edge)

    def recommended_bankroll(
        self,
        desired_bet_spread: int,
        base_unit: Decimal,
        risk_of_ruin_target: float = 0.01,
    ) -> Decimal:
        """
        Calculate recommended bankroll for a given bet spread.

        Args:
            desired_bet_spread: Maximum bet in units (e.g., 12 for 1-12 spread)
            base_unit: Base betting unit
            risk_of_ruin_target: Target risk of ruin (default 1%)

        Returns:
            Recommended bankroll
        """
        # Rule of thumb: 200-400 max bets for 1% RoR with card counting
        # More conservative estimate using 300 max bets
        max_bet = Decimal(str(desired_bet_spread)) * base_unit
        return max_bet * Decimal("300")

    def update_bankroll(self, new_bankroll: Decimal) -> None:
        """Update the bankroll amount."""
        self.bankroll = new_bankroll


def kelly_criterion(
    win_probability: float,
    win_amount: float,
    lose_amount: float = 1.0,
) -> float:
    """
    Calculate the Kelly criterion fraction.

    Formula: f* = (bp - q) / b
    where:
        f* = fraction of bankroll to bet
        b = odds received on the bet (win amount / lose amount)
        p = probability of winning
        q = probability of losing (1 - p)

    Args:
        win_probability: Probability of winning (0-1)
        win_amount: Amount won per unit bet
        lose_amount: Amount lost per unit bet (default 1)

    Returns:
        Optimal fraction of bankroll to bet
    """
    if win_probability <= 0 or win_probability >= 1:
        return 0.0

    p = win_probability
    q = 1 - p
    b = win_amount / lose_amount

    kelly = (b * p - q) / b

    return max(0.0, kelly)  # Never bet negative
