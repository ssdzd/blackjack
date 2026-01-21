"""Tests for basic strategy tables."""

import pytest

from core.strategy import BasicStrategy, Action, RuleSet
from core.strategy.deviations import ILLUSTRIOUS_18, FAB_4, find_deviation


class TestBasicStrategy:
    """Tests for BasicStrategy class."""

    def test_hard_17_always_stand(self, basic_strategy):
        """Test that hard 17+ always stands."""
        for total in range(17, 22):
            for dealer_up in range(2, 12):
                action = basic_strategy.get_action(
                    player_total=total,
                    dealer_upcard=dealer_up,
                    is_soft=False,
                )
                assert action == Action.STAND

    def test_hard_11_always_double(self, basic_strategy):
        """Test that hard 11 always doubles."""
        for dealer_up in range(2, 12):
            action = basic_strategy.get_action(
                player_total=11,
                dealer_upcard=dealer_up,
                is_soft=False,
            )
            assert action == Action.DOUBLE

    def test_hard_8_always_hit(self, basic_strategy):
        """Test that hard 8 or less always hits."""
        for total in range(5, 9):
            for dealer_up in range(2, 12):
                action = basic_strategy.get_action(
                    player_total=total,
                    dealer_upcard=dealer_up,
                    is_soft=False,
                )
                assert action == Action.HIT

    def test_soft_20_always_stand(self, basic_strategy):
        """Test that soft 20 (A-9) always stands."""
        for dealer_up in range(2, 12):
            action = basic_strategy.get_action(
                player_total=20,
                dealer_upcard=dealer_up,
                is_soft=True,
            )
            assert action == Action.STAND

    def test_pair_aces_always_split(self, basic_strategy):
        """Test that pair of Aces always splits."""
        for dealer_up in range(2, 12):
            action = basic_strategy.get_action(
                player_total=22,  # A-A = 12 soft, but pair_rank is key
                dealer_upcard=dealer_up,
                is_pair=True,
                pair_rank=11,  # Ace value
            )
            assert action == Action.SPLIT

    def test_pair_8s_always_split(self, basic_strategy):
        """Test that pair of 8s always splits."""
        for dealer_up in range(2, 12):
            action = basic_strategy.get_action(
                player_total=16,
                dealer_upcard=dealer_up,
                is_pair=True,
                pair_rank=8,
            )
            # Note: might surrender vs 10/A with certain rules
            assert action in [Action.SPLIT, Action.SURRENDER]

    def test_pair_10s_never_split(self, basic_strategy):
        """Test that pair of 10s never splits."""
        for dealer_up in range(2, 12):
            action = basic_strategy.get_action(
                player_total=20,
                dealer_upcard=dealer_up,
                is_pair=True,
                pair_rank=10,
            )
            assert action == Action.STAND

    def test_pair_5s_never_split(self, basic_strategy):
        """Test that pair of 5s never splits (treat as 10)."""
        for dealer_up in range(2, 12):
            action = basic_strategy.get_action(
                player_total=10,
                dealer_upcard=dealer_up,
                is_pair=True,
                pair_rank=5,
            )
            # Should double, not split
            assert action in [Action.DOUBLE, Action.HIT]

    def test_conditional_double(self, basic_strategy):
        """Test conditional double resolution."""
        # Hard 10 vs 10 - should be DOUBLE_OR_HIT
        action_can_double = basic_strategy.get_action(
            player_total=10,
            dealer_upcard=10,
            is_soft=False,
            can_double=True,
        )
        assert action_can_double == Action.HIT  # Actually hit vs 10

        action_cant_double = basic_strategy.get_action(
            player_total=10,
            dealer_upcard=10,
            is_soft=False,
            can_double=False,
        )
        assert action_cant_double == Action.HIT

    def test_hard_12_vs_dealer(self, basic_strategy):
        """Test hard 12 strategy."""
        # 12 vs 2-3: Hit
        assert basic_strategy.get_action(12, 2, is_soft=False) == Action.HIT
        assert basic_strategy.get_action(12, 3, is_soft=False) == Action.HIT

        # 12 vs 4-6: Stand
        assert basic_strategy.get_action(12, 4, is_soft=False) == Action.STAND
        assert basic_strategy.get_action(12, 5, is_soft=False) == Action.STAND
        assert basic_strategy.get_action(12, 6, is_soft=False) == Action.STAND

        # 12 vs 7+: Hit
        for dealer in range(7, 12):
            assert basic_strategy.get_action(12, dealer, is_soft=False) == Action.HIT

    def test_surrender_16_vs_10(self):
        """Test surrender with 16 vs 10."""
        rules = RuleSet(surrender="late", dealer_hits_soft_17=True)
        strategy = BasicStrategy(rules)

        action = strategy.get_action(
            player_total=16,
            dealer_upcard=10,
            is_soft=False,
            can_surrender=True,
        )
        assert action == Action.SURRENDER

        # Without surrender allowed
        action_no_surr = strategy.get_action(
            player_total=16,
            dealer_upcard=10,
            is_soft=False,
            can_surrender=False,
        )
        assert action_no_surr == Action.HIT


class TestIllustrious18:
    """Tests for Illustrious 18 deviations."""

    def test_all_18_deviations_exist(self):
        """Verify all 18 Illustrious deviations are defined."""
        assert len(ILLUSTRIOUS_18) == 18

    def test_insurance_deviation(self):
        """Test insurance at TC +3."""
        # First deviation is insurance
        insurance = ILLUSTRIOUS_18[0]
        assert insurance.index == 3.0
        assert not insurance.should_deviate(2.5)
        assert insurance.should_deviate(3.0)
        assert insurance.should_deviate(4.0)

    def test_16_vs_10_deviation(self):
        """Test 16 vs 10: Stand at TC 0+."""
        deviation = next(
            d for d in ILLUSTRIOUS_18
            if d.player_total == 16 and d.dealer_upcard == 10 and not d.is_pair
        )
        assert deviation.index == 0.0
        assert deviation.basic_action == Action.HIT
        assert deviation.deviation_action == Action.STAND

        assert deviation.get_action(-1.0) == Action.HIT
        assert deviation.get_action(0.0) == Action.STAND
        assert deviation.get_action(2.0) == Action.STAND

    def test_12_vs_2_deviation(self):
        """Test 12 vs 2: Stand at TC +3."""
        deviation = next(
            d for d in ILLUSTRIOUS_18
            if d.player_total == 12 and d.dealer_upcard == 2
        )
        assert deviation.index == 3.0
        assert deviation.basic_action == Action.HIT
        assert deviation.deviation_action == Action.STAND

    def test_negative_index_deviation(self):
        """Test negative index (hit at low count)."""
        # 13 vs 2: Hit at TC -1 or below
        deviation = next(
            d for d in ILLUSTRIOUS_18
            if d.player_total == 13 and d.dealer_upcard == 2
        )
        assert deviation.index == -1.0
        assert deviation.direction == "at_or_below"
        assert deviation.basic_action == Action.STAND
        assert deviation.deviation_action == Action.HIT

        assert deviation.get_action(0.0) == Action.STAND
        assert deviation.get_action(-1.0) == Action.HIT
        assert deviation.get_action(-2.0) == Action.HIT


class TestFab4:
    """Tests for Fab 4 surrender deviations."""

    def test_all_4_deviations_exist(self):
        """Verify all 4 Fab 4 deviations are defined."""
        assert len(FAB_4) == 4

    def test_14_vs_10_surrender(self):
        """Test 14 vs 10: Surrender at TC +3."""
        deviation = next(
            d for d in FAB_4
            if d.player_total == 14 and d.dealer_upcard == 10
        )
        assert deviation.index == 3.0
        assert deviation.deviation_action == Action.SURRENDER

    def test_15_vs_9_surrender(self):
        """Test 15 vs 9: Surrender at TC +2."""
        deviation = next(
            d for d in FAB_4
            if d.player_total == 15 and d.dealer_upcard == 9
        )
        assert deviation.index == 2.0
        assert deviation.deviation_action == Action.SURRENDER


class TestFindDeviation:
    """Tests for deviation finder."""

    def test_find_existing_deviation(self):
        """Test finding an applicable deviation."""
        deviation = find_deviation(
            player_total=16,
            is_soft=False,
            is_pair=False,
            dealer_upcard=10,
            true_count=0.0,
        )
        assert deviation is not None
        assert deviation.deviation_action == Action.STAND

    def test_find_no_deviation_below_index(self):
        """Test no deviation found when TC is below index."""
        deviation = find_deviation(
            player_total=15,
            is_soft=False,
            is_pair=False,
            dealer_upcard=10,
            true_count=3.0,  # Need TC +4 for this deviation
        )
        assert deviation is None

    def test_find_no_deviation_for_non_illustrious(self):
        """Test no deviation found for hands not in Illustrious 18."""
        deviation = find_deviation(
            player_total=17,  # Not in Illustrious 18
            is_soft=False,
            is_pair=False,
            dealer_upcard=7,
            true_count=5.0,
        )
        assert deviation is None
