"""Bankroll management utilities."""

from dataclasses import dataclass
from decimal import Decimal
import math


@dataclass
class RiskOfRuin:
    """Risk of ruin calculation result."""

    probability: float
    expected_hands_to_double: int
    expected_hands_to_ruin: int
    n_zero_point: float  # Hands where risk stabilizes


class BankrollManager:
    """
    Bankroll management and risk analysis.

    Provides tools for calculating risk of ruin, session goals,
    and stop-loss limits.
    """

    def __init__(
        self,
        bankroll: Decimal,
        min_bet: Decimal,
        max_bet: Decimal,
        player_edge: Decimal = Decimal("0.01"),
        variance: Decimal = Decimal("1.3"),
    ) -> None:
        """
        Initialize bankroll manager.

        Args:
            bankroll: Total bankroll
            min_bet: Minimum table bet
            max_bet: Maximum table bet
            player_edge: Player's expected edge (e.g., 0.01 for 1%)
            variance: Game variance (default 1.3 for blackjack)
        """
        self.bankroll = bankroll
        self.min_bet = min_bet
        self.max_bet = max_bet
        self.player_edge = player_edge
        self.variance = variance

    def risk_of_ruin(
        self,
        target_bankroll: Decimal | None = None,
        average_bet: Decimal | None = None,
    ) -> RiskOfRuin:
        """
        Calculate risk of ruin.

        Risk of ruin is the probability of losing the entire bankroll
        before reaching a target (or infinity if no target).

        Args:
            target_bankroll: Target bankroll to reach (None = infinite horizon)
            average_bet: Average bet size (uses min_bet if not provided)

        Returns:
            RiskOfRuin result
        """
        avg_bet = average_bet or self.min_bet
        edge = float(self.player_edge)
        var = float(self.variance)
        bank = float(self.bankroll / avg_bet)  # Bankroll in betting units

        if edge <= 0:
            # Negative expectation game
            return RiskOfRuin(
                probability=1.0,
                expected_hands_to_double=0,
                expected_hands_to_ruin=int(bank / abs(edge)) if edge != 0 else 0,
                n_zero_point=0,
            )

        # Risk of ruin formula for positive expectation
        # RoR = ((1 - edge) / (1 + edge)) ^ (bankroll / variance)
        # Simplified: RoR ≈ e^(-2 * edge * bankroll / variance)

        exponent = -2 * edge * bank / var
        ror = math.exp(exponent) if exponent > -700 else 0.0

        if target_bankroll is not None:
            target = float(target_bankroll / avg_bet)
            # With target, RoR is reduced
            target_ratio = bank / target
            ror = ror * target_ratio if target > bank else ror

        # Expected hands to double bankroll
        hands_to_double = int(bank / edge) if edge > 0 else 0

        # N0 point: hands where long-term expectation dominates variance
        n_zero = var / (edge ** 2) if edge > 0 else float("inf")

        # Expected hands to ruin (if it happens)
        hands_to_ruin = int(bank / edge) if edge > 0 else int(bank / 0.01)

        return RiskOfRuin(
            probability=min(1.0, max(0.0, ror)),
            expected_hands_to_double=hands_to_double,
            expected_hands_to_ruin=hands_to_ruin,
            n_zero_point=n_zero,
        )

    def session_stop_loss(self, session_bankroll_fraction: float = 0.1) -> Decimal:
        """
        Calculate recommended session stop-loss.

        Args:
            session_bankroll_fraction: Fraction of bankroll to risk per session

        Returns:
            Stop-loss amount
        """
        return (self.bankroll * Decimal(str(session_bankroll_fraction))).quantize(
            Decimal("1")
        )

    def session_win_goal(
        self,
        stop_loss: Decimal | None = None,
        win_ratio: float = 1.5,
    ) -> Decimal:
        """
        Calculate session win goal.

        Args:
            stop_loss: Session stop-loss (calculated if not provided)
            win_ratio: Win goal as multiple of stop loss

        Returns:
            Win goal amount
        """
        sl = stop_loss or self.session_stop_loss()
        return (sl * Decimal(str(win_ratio))).quantize(Decimal("1"))

    def units_in_bankroll(self, unit_size: Decimal | None = None) -> int:
        """
        Calculate number of betting units in bankroll.

        Args:
            unit_size: Betting unit (uses min_bet if not provided)

        Returns:
            Number of units
        """
        unit = unit_size or self.min_bet
        return int(self.bankroll / unit)

    def recommended_unit_size(
        self,
        max_bet_spread: int = 12,
        bankroll_units: int = 400,
    ) -> Decimal:
        """
        Calculate recommended betting unit size.

        Args:
            max_bet_spread: Maximum bet spread (e.g., 1-12)
            bankroll_units: Target bankroll in max bet units

        Returns:
            Recommended unit size
        """
        # Bankroll should be able to handle variance
        # Rule: bankroll = spread * unit * multiplier
        max_bet_multiplier = Decimal(str(bankroll_units / max_bet_spread))
        unit = self.bankroll / max_bet_multiplier / Decimal(str(max_bet_spread))
        return unit.quantize(Decimal("1"))

    def bet_ramp(
        self,
        true_count: float,
        unit_size: Decimal,
        tc_threshold: float = 1.0,
        max_spread: int = 12,
    ) -> Decimal:
        """
        Calculate bet for a given true count using a ramp.

        Args:
            true_count: Current true count
            unit_size: Base betting unit
            tc_threshold: TC at which to start increasing bets
            max_spread: Maximum spread (units)

        Returns:
            Recommended bet
        """
        if true_count < tc_threshold:
            return self.min_bet

        # Linear ramp: 1 unit per TC above threshold
        units = int(true_count - tc_threshold + 1)
        units = min(units, max_spread)
        bet = unit_size * Decimal(str(units))

        return min(bet, self.max_bet).quantize(Decimal("1"))

    def update_bankroll(self, result: Decimal) -> None:
        """
        Update bankroll after a hand result.

        Args:
            result: Amount won (positive) or lost (negative)
        """
        self.bankroll += result
