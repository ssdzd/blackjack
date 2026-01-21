"""Probability calculations for blackjack."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Mapping

from core.strategy.rules import RuleSet


class DealerOutcome(Enum):
    """Possible dealer final outcomes."""

    BUST = auto()
    SEVENTEEN = auto()
    EIGHTEEN = auto()
    NINETEEN = auto()
    TWENTY = auto()
    TWENTY_ONE = auto()
    BLACKJACK = auto()


@dataclass(frozen=True)
class DealerProbabilities:
    """Dealer outcome probabilities for a given upcard."""

    upcard: int  # 2-11
    bust: float
    seventeen: float
    eighteen: float
    nineteen: float
    twenty: float
    twenty_one: float
    blackjack: float = 0.0

    def __post_init__(self) -> None:
        """Validate probabilities sum to 1."""
        total = (
            self.bust
            + self.seventeen
            + self.eighteen
            + self.nineteen
            + self.twenty
            + self.twenty_one
            + self.blackjack
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Probabilities must sum to 1.0, got {total}")

    def to_dict(self) -> dict[DealerOutcome, float]:
        """Convert to outcome dictionary."""
        return {
            DealerOutcome.BUST: self.bust,
            DealerOutcome.SEVENTEEN: self.seventeen,
            DealerOutcome.EIGHTEEN: self.eighteen,
            DealerOutcome.NINETEEN: self.nineteen,
            DealerOutcome.TWENTY: self.twenty,
            DealerOutcome.TWENTY_ONE: self.twenty_one,
            DealerOutcome.BLACKJACK: self.blackjack,
        }


class ProbabilityEngine:
    """
    Pre-computed probability tables for blackjack.

    Probabilities are calculated for an infinite deck assumption
    which is a good approximation for 6+ deck games.
    """

    # Dealer probabilities with S17 (Stand on Soft 17)
    # Based on infinite deck calculations
    _DEALER_PROBS_S17: dict[int, DealerProbabilities] = {
        2: DealerProbabilities(2, 0.3536, 0.1395, 0.1324, 0.1233, 0.1218, 0.1294),
        3: DealerProbabilities(3, 0.3723, 0.1305, 0.1260, 0.1199, 0.1184, 0.1329),
        4: DealerProbabilities(4, 0.3926, 0.1310, 0.1140, 0.1136, 0.1136, 0.1352),
        5: DealerProbabilities(5, 0.4168, 0.1228, 0.1097, 0.1085, 0.1092, 0.1330),
        6: DealerProbabilities(6, 0.4234, 0.1065, 0.1063, 0.1059, 0.1060, 0.1519),
        7: DealerProbabilities(7, 0.2618, 0.3686, 0.1379, 0.0786, 0.0786, 0.0745),
        8: DealerProbabilities(8, 0.2439, 0.1286, 0.3598, 0.1289, 0.0686, 0.0702),
        9: DealerProbabilities(9, 0.2278, 0.1198, 0.1082, 0.3544, 0.1210, 0.0688),
        10: DealerProbabilities(10, 0.2122, 0.1118, 0.1122, 0.1119, 0.3396, 0.0353, 0.0770),
        11: DealerProbabilities(11, 0.1169, 0.1307, 0.1307, 0.1307, 0.1307, 0.0294, 0.3309),
    }

    # Dealer probabilities with H17 (Hit on Soft 17)
    _DEALER_PROBS_H17: dict[int, DealerProbabilities] = {
        2: DealerProbabilities(2, 0.3551, 0.1380, 0.1320, 0.1228, 0.1217, 0.1304),
        3: DealerProbabilities(3, 0.3742, 0.1291, 0.1255, 0.1192, 0.1179, 0.1341),
        4: DealerProbabilities(4, 0.3946, 0.1296, 0.1134, 0.1127, 0.1129, 0.1368),
        5: DealerProbabilities(5, 0.4189, 0.1215, 0.1091, 0.1076, 0.1084, 0.1345),
        6: DealerProbabilities(6, 0.4256, 0.1050, 0.1057, 0.1050, 0.1051, 0.1536),
        7: DealerProbabilities(7, 0.2620, 0.3684, 0.1378, 0.0785, 0.0786, 0.0747),
        8: DealerProbabilities(8, 0.2442, 0.1284, 0.3597, 0.1288, 0.0685, 0.0704),
        9: DealerProbabilities(9, 0.2281, 0.1196, 0.1081, 0.3543, 0.1209, 0.0690),
        10: DealerProbabilities(10, 0.2124, 0.1116, 0.1121, 0.1118, 0.3394, 0.0357, 0.0770),
        11: DealerProbabilities(11, 0.1271, 0.1195, 0.1195, 0.1297, 0.1297, 0.0436, 0.3309),
    }

    def __init__(self, rules: RuleSet | None = None) -> None:
        """
        Initialize the probability engine.

        Args:
            rules: Rule set to use. Defaults to standard rules.
        """
        self.rules = rules or RuleSet()
        if self.rules.dealer_hits_soft_17:
            self._dealer_probs = self._DEALER_PROBS_H17
        else:
            self._dealer_probs = self._DEALER_PROBS_S17

    def dealer_probabilities(self, upcard: int) -> DealerProbabilities:
        """
        Get dealer outcome probabilities for a given upcard.

        Args:
            upcard: Dealer's upcard value (2-11, 11=Ace)

        Returns:
            DealerProbabilities for the upcard
        """
        if upcard < 2 or upcard > 11:
            raise ValueError(f"Invalid upcard: {upcard}")
        return self._dealer_probs[upcard]

    def dealer_bust_probability(self, upcard: int) -> float:
        """Get the probability that the dealer busts given an upcard."""
        return self._dealer_probs[upcard].bust

    def player_bust_probability(self, hard_total: int) -> float:
        """
        Get the probability of busting on the next hit.

        Args:
            hard_total: Current hard total

        Returns:
            Probability of busting (0-1)
        """
        if hard_total < 12:
            return 0.0
        if hard_total >= 21:
            return 1.0

        # Cards that will bust: those that make total > 21
        bust_cards = hard_total - 21 + 10  # Number of ranks that bust
        # Each rank has probability 1/13 (infinite deck)
        # 10-value cards (10, J, Q, K) count as one "rank" for busting purposes
        if hard_total == 12:
            return 4 / 13  # Only 10-value busts
        elif hard_total <= 21:
            safe_values = 21 - hard_total
            return (10 - safe_values) / 13 if safe_values < 10 else 4 / 13
        return 1.0

    def expected_value(
        self,
        player_total: int,
        dealer_upcard: int,
        action: str,
    ) -> float:
        """
        Calculate expected value for a given action.

        Args:
            player_total: Player's hand total
            dealer_upcard: Dealer's upcard (2-11)
            action: Action to take ("stand", "hit", "double")

        Returns:
            Expected value (-1 to +1 for basic bets)
        """
        dealer_probs = self.dealer_probabilities(dealer_upcard).to_dict()

        if action == "stand":
            ev = 0.0
            for outcome, prob in dealer_probs.items():
                dealer_total = self._outcome_to_total(outcome)
                if outcome == DealerOutcome.BUST:
                    ev += prob * 1.0  # Win
                elif dealer_total > player_total:
                    ev += prob * -1.0  # Lose
                elif dealer_total < player_total:
                    ev += prob * 1.0  # Win
                # Push: EV += 0
            return ev

        # For hit/double, would need recursive calculation
        # This is a simplified placeholder
        return 0.0

    def _outcome_to_total(self, outcome: DealerOutcome) -> int:
        """Convert a dealer outcome to a hand total."""
        return {
            DealerOutcome.BUST: 0,
            DealerOutcome.SEVENTEEN: 17,
            DealerOutcome.EIGHTEEN: 18,
            DealerOutcome.NINETEEN: 19,
            DealerOutcome.TWENTY: 20,
            DealerOutcome.TWENTY_ONE: 21,
            DealerOutcome.BLACKJACK: 21,
        }[outcome]

    @staticmethod
    def card_probability(rank_value: int, cards_seen: Mapping[int, int] | None = None) -> float:
        """
        Get probability of drawing a card of given value.

        Args:
            rank_value: Value of card (1-10, where 1=Ace and 10=10/J/Q/K)
            cards_seen: Optional mapping of rank values to counts seen

        Returns:
            Probability (0-1)
        """
        if cards_seen is None:
            # Infinite deck assumption
            if rank_value == 10:
                return 4 / 13  # Four 10-value ranks
            return 1 / 13

        # Finite deck calculation would go here
        return 1 / 13  # Placeholder
