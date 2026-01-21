"""Strategy deviations based on true count (Illustrious 18, Fab 4)."""

from dataclasses import dataclass
from typing import Literal

from core.strategy.basic import Action


@dataclass(frozen=True)
class IndexPlay:
    """
    An index play (strategy deviation based on count).

    When the true count meets or exceeds the index, deviate from basic strategy.
    """

    # Hand description
    player_total: int
    is_soft: bool
    is_pair: bool
    dealer_upcard: int  # 2-11 (11 = Ace)

    # Basic strategy action (what you'd normally do)
    basic_action: Action

    # Deviation action (what to do at/above the index)
    deviation_action: Action

    # True count threshold
    index: float

    # Direction: deviate when TC is >= index ("at_or_above") or <= index ("at_or_below")
    direction: Literal["at_or_above", "at_or_below"] = "at_or_above"

    # Description for training
    description: str = ""

    def should_deviate(self, true_count: float) -> bool:
        """
        Check if the deviation should be taken at the given true count.

        Args:
            true_count: The current true count

        Returns:
            True if the deviation should be taken
        """
        if self.direction == "at_or_above":
            return true_count >= self.index
        return true_count <= self.index

    def get_action(self, true_count: float) -> Action:
        """
        Get the correct action for the given true count.

        Args:
            true_count: The current true count

        Returns:
            The recommended action
        """
        if self.should_deviate(true_count):
            return self.deviation_action
        return self.basic_action


# The Illustrious 18 - Most valuable playing deviations
# Based on Don Schlesinger's work
# Ordered by expected value gain (most valuable first)

ILLUSTRIOUS_18: list[IndexPlay] = [
    # 1. Insurance (most valuable)
    IndexPlay(
        player_total=0,  # N/A for insurance
        is_soft=False,
        is_pair=False,
        dealer_upcard=11,
        basic_action=Action.STAND,  # Placeholder - no insurance
        deviation_action=Action.STAND,  # Take insurance
        index=3.0,
        description="Take insurance at TC +3 or higher",
    ),
    # 2. 16 vs 10: Stand at 0+
    IndexPlay(
        player_total=16,
        is_soft=False,
        is_pair=False,
        dealer_upcard=10,
        basic_action=Action.HIT,
        deviation_action=Action.STAND,
        index=0.0,
        description="Stand on 16 vs 10 at TC 0 or higher",
    ),
    # 3. 15 vs 10: Stand at +4
    IndexPlay(
        player_total=15,
        is_soft=False,
        is_pair=False,
        dealer_upcard=10,
        basic_action=Action.HIT,
        deviation_action=Action.STAND,
        index=4.0,
        description="Stand on 15 vs 10 at TC +4 or higher",
    ),
    # 4. 10,10 vs 5: Split at +5
    IndexPlay(
        player_total=20,
        is_soft=False,
        is_pair=True,
        dealer_upcard=5,
        basic_action=Action.STAND,
        deviation_action=Action.SPLIT,
        index=5.0,
        description="Split 10s vs 5 at TC +5 or higher",
    ),
    # 5. 10,10 vs 6: Split at +4
    IndexPlay(
        player_total=20,
        is_soft=False,
        is_pair=True,
        dealer_upcard=6,
        basic_action=Action.STAND,
        deviation_action=Action.SPLIT,
        index=4.0,
        description="Split 10s vs 6 at TC +4 or higher",
    ),
    # 6. 10 vs 10: Double at +4
    IndexPlay(
        player_total=10,
        is_soft=False,
        is_pair=False,
        dealer_upcard=10,
        basic_action=Action.HIT,
        deviation_action=Action.DOUBLE,
        index=4.0,
        description="Double 10 vs 10 at TC +4 or higher",
    ),
    # 7. 12 vs 3: Stand at +2
    IndexPlay(
        player_total=12,
        is_soft=False,
        is_pair=False,
        dealer_upcard=3,
        basic_action=Action.HIT,
        deviation_action=Action.STAND,
        index=2.0,
        description="Stand on 12 vs 3 at TC +2 or higher",
    ),
    # 8. 12 vs 2: Stand at +3
    IndexPlay(
        player_total=12,
        is_soft=False,
        is_pair=False,
        dealer_upcard=2,
        basic_action=Action.HIT,
        deviation_action=Action.STAND,
        index=3.0,
        description="Stand on 12 vs 2 at TC +3 or higher",
    ),
    # 9. 11 vs A: Double at +1
    IndexPlay(
        player_total=11,
        is_soft=False,
        is_pair=False,
        dealer_upcard=11,
        basic_action=Action.HIT,
        deviation_action=Action.DOUBLE,
        index=1.0,
        description="Double 11 vs A at TC +1 or higher",
    ),
    # 10. 9 vs 2: Double at +1
    IndexPlay(
        player_total=9,
        is_soft=False,
        is_pair=False,
        dealer_upcard=2,
        basic_action=Action.HIT,
        deviation_action=Action.DOUBLE,
        index=1.0,
        description="Double 9 vs 2 at TC +1 or higher",
    ),
    # 11. 10 vs A: Double at +4
    IndexPlay(
        player_total=10,
        is_soft=False,
        is_pair=False,
        dealer_upcard=11,
        basic_action=Action.HIT,
        deviation_action=Action.DOUBLE,
        index=4.0,
        description="Double 10 vs A at TC +4 or higher",
    ),
    # 12. 9 vs 7: Double at +3
    IndexPlay(
        player_total=9,
        is_soft=False,
        is_pair=False,
        dealer_upcard=7,
        basic_action=Action.HIT,
        deviation_action=Action.DOUBLE,
        index=3.0,
        description="Double 9 vs 7 at TC +3 or higher",
    ),
    # 13. 16 vs 9: Stand at +5
    IndexPlay(
        player_total=16,
        is_soft=False,
        is_pair=False,
        dealer_upcard=9,
        basic_action=Action.HIT,
        deviation_action=Action.STAND,
        index=5.0,
        description="Stand on 16 vs 9 at TC +5 or higher",
    ),
    # 14. 13 vs 2: Hit at -1 or below
    IndexPlay(
        player_total=13,
        is_soft=False,
        is_pair=False,
        dealer_upcard=2,
        basic_action=Action.STAND,
        deviation_action=Action.HIT,
        index=-1.0,
        direction="at_or_below",
        description="Hit 13 vs 2 at TC -1 or lower",
    ),
    # 15. 12 vs 4: Hit at 0 or below
    IndexPlay(
        player_total=12,
        is_soft=False,
        is_pair=False,
        dealer_upcard=4,
        basic_action=Action.STAND,
        deviation_action=Action.HIT,
        index=0.0,
        direction="at_or_below",
        description="Hit 12 vs 4 at TC 0 or lower",
    ),
    # 16. 12 vs 5: Hit at -2 or below
    IndexPlay(
        player_total=12,
        is_soft=False,
        is_pair=False,
        dealer_upcard=5,
        basic_action=Action.STAND,
        deviation_action=Action.HIT,
        index=-2.0,
        direction="at_or_below",
        description="Hit 12 vs 5 at TC -2 or lower",
    ),
    # 17. 12 vs 6: Hit at -1 or below
    IndexPlay(
        player_total=12,
        is_soft=False,
        is_pair=False,
        dealer_upcard=6,
        basic_action=Action.STAND,
        deviation_action=Action.HIT,
        index=-1.0,
        direction="at_or_below",
        description="Hit 12 vs 6 at TC -1 or lower",
    ),
    # 18. 13 vs 3: Hit at -2 or below
    IndexPlay(
        player_total=13,
        is_soft=False,
        is_pair=False,
        dealer_upcard=3,
        basic_action=Action.STAND,
        deviation_action=Action.HIT,
        index=-2.0,
        direction="at_or_below",
        description="Hit 13 vs 3 at TC -2 or lower",
    ),
]


# The Fab 4 - Surrender deviations
# Most valuable surrender plays based on true count

FAB_4: list[IndexPlay] = [
    # 1. 14 vs 10: Surrender at +3
    IndexPlay(
        player_total=14,
        is_soft=False,
        is_pair=False,
        dealer_upcard=10,
        basic_action=Action.HIT,
        deviation_action=Action.SURRENDER,
        index=3.0,
        description="Surrender 14 vs 10 at TC +3 or higher",
    ),
    # 2. 15 vs 9: Surrender at +2
    IndexPlay(
        player_total=15,
        is_soft=False,
        is_pair=False,
        dealer_upcard=9,
        basic_action=Action.HIT,
        deviation_action=Action.SURRENDER,
        index=2.0,
        description="Surrender 15 vs 9 at TC +2 or higher",
    ),
    # 3. 15 vs A: Surrender at +1 (with H17)
    IndexPlay(
        player_total=15,
        is_soft=False,
        is_pair=False,
        dealer_upcard=11,
        basic_action=Action.HIT,
        deviation_action=Action.SURRENDER,
        index=1.0,
        description="Surrender 15 vs A at TC +1 or higher (H17)",
    ),
    # 4. 14 vs A: Surrender at +3 (with H17)
    IndexPlay(
        player_total=14,
        is_soft=False,
        is_pair=False,
        dealer_upcard=11,
        basic_action=Action.HIT,
        deviation_action=Action.SURRENDER,
        index=3.0,
        description="Surrender 14 vs A at TC +3 or higher (H17)",
    ),
]


def find_deviation(
    player_total: int,
    is_soft: bool,
    is_pair: bool,
    dealer_upcard: int,
    true_count: float,
    include_surrender: bool = True,
) -> IndexPlay | None:
    """
    Find any applicable deviation for the given situation.

    Args:
        player_total: Player's hand total
        is_soft: Whether the hand is soft
        is_pair: Whether the hand is a pair
        dealer_upcard: Dealer's upcard (2-11)
        true_count: Current true count
        include_surrender: Whether to include Fab 4 surrender plays

    Returns:
        The applicable IndexPlay if found and TC meets threshold, else None
    """
    all_plays = ILLUSTRIOUS_18.copy()
    if include_surrender:
        all_plays.extend(FAB_4)

    for play in all_plays:
        if (
            play.player_total == player_total
            and play.is_soft == is_soft
            and play.is_pair == is_pair
            and play.dealer_upcard == dealer_upcard
            and play.should_deviate(true_count)
        ):
            return play

    return None
