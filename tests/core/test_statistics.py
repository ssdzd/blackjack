"""Tests for statistics calculations."""

import pytest
from decimal import Decimal

from core.statistics.probability import ProbabilityEngine, DealerOutcome
from core.statistics.house_edge import HouseEdgeCalculator
from core.statistics.kelly import KellyCalculator, kelly_criterion
from core.statistics.bankroll import BankrollManager
from core.strategy.rules import RuleSet


class TestProbabilityEngine:
    """Tests for probability calculations."""

    def test_dealer_probabilities_sum_to_one(self):
        """Verify all dealer probabilities sum to 1.0."""
        engine = ProbabilityEngine()

        for upcard in range(2, 12):
            probs = engine.dealer_probabilities(upcard)
            total = (
                probs.bust + probs.seventeen + probs.eighteen +
                probs.nineteen + probs.twenty + probs.twenty_one +
                probs.blackjack
            )
            assert abs(total - 1.0) < 0.001, f"Upcard {upcard}: probs sum to {total}"

    def test_dealer_bust_highest_with_6(self):
        """Verify dealer busts most often with 6 showing."""
        engine = ProbabilityEngine()

        bust_probs = {up: engine.dealer_bust_probability(up) for up in range(2, 12)}

        # 6 should have highest bust probability among non-ace cards
        non_ace_busts = {k: v for k, v in bust_probs.items() if k != 11}
        max_bust_upcard = max(non_ace_busts, key=non_ace_busts.get)
        assert max_bust_upcard == 6

    def test_player_bust_probability(self):
        """Test player bust probability calculation."""
        engine = ProbabilityEngine()

        # Hard 11 or less: can't bust
        assert engine.player_bust_probability(11) == 0.0
        assert engine.player_bust_probability(8) == 0.0

        # Hard 21: always bust
        assert engine.player_bust_probability(21) == 1.0

        # Hard 12: bust on 10 only (4/13)
        prob_12 = engine.player_bust_probability(12)
        assert abs(prob_12 - 4/13) < 0.01

    def test_h17_vs_s17_differences(self):
        """Test H17 and S17 produce different probabilities."""
        h17_rules = RuleSet(dealer_hits_soft_17=True)
        s17_rules = RuleSet(dealer_hits_soft_17=False)

        h17_engine = ProbabilityEngine(h17_rules)
        s17_engine = ProbabilityEngine(s17_rules)

        # Probabilities should differ for ace showing
        h17_probs = h17_engine.dealer_probabilities(11)
        s17_probs = s17_engine.dealer_probabilities(11)

        # H17 should have slightly different bust rate for soft hands
        assert h17_probs.bust != s17_probs.bust


class TestHouseEdgeCalculator:
    """Tests for house edge calculations."""

    def test_baseline_edge(self):
        """Test baseline house edge is reasonable."""
        rules = RuleSet()
        calc = HouseEdgeCalculator(rules)
        edge = calc.calculate()

        # Should be around 0.4-0.6% for standard rules
        assert Decimal("0.3") < edge < Decimal("0.8")

    def test_6_5_blackjack_increases_edge(self):
        """Test 6:5 blackjack significantly increases house edge."""
        rules_3_2 = RuleSet(blackjack_payout=1.5)
        rules_6_5 = RuleSet(blackjack_payout=1.2)

        edge_3_2 = HouseEdgeCalculator(rules_3_2).calculate()
        edge_6_5 = HouseEdgeCalculator(rules_6_5).calculate()

        # 6:5 should add about 1.4% to house edge
        difference = edge_6_5 - edge_3_2
        assert Decimal("1.3") < difference < Decimal("1.5")

    def test_h17_increases_edge(self):
        """Test H17 increases house edge vs S17."""
        rules_s17 = RuleSet(dealer_hits_soft_17=False)
        rules_h17 = RuleSet(dealer_hits_soft_17=True)

        edge_s17 = HouseEdgeCalculator(rules_s17).calculate()
        edge_h17 = HouseEdgeCalculator(rules_h17).calculate()

        # H17 should add about 0.2%
        assert edge_h17 > edge_s17
        difference = edge_h17 - edge_s17
        assert Decimal("0.15") < difference < Decimal("0.25")

    def test_single_deck_lower_edge(self):
        """Test single deck has lower house edge."""
        rules_1_deck = RuleSet(num_decks=1)
        rules_6_deck = RuleSet(num_decks=6)

        edge_1 = HouseEdgeCalculator(rules_1_deck).calculate()
        edge_6 = HouseEdgeCalculator(rules_6_deck).calculate()

        assert edge_1 < edge_6

    def test_player_advantage_with_count(self):
        """Test player advantage calculation with true count."""
        rules = RuleSet()
        calc = HouseEdgeCalculator(rules)
        base_edge = calc.calculate()

        # At TC 0, player has negative advantage (house edge)
        adv_0 = calc.player_advantage_with_count(0, base_edge)
        assert adv_0 < 0

        # At high TC, player has positive advantage
        adv_4 = calc.player_advantage_with_count(4, base_edge)
        assert adv_4 > 0

        # Each TC point worth ~0.5%
        tc_value = adv_4 - calc.player_advantage_with_count(3, base_edge)
        assert Decimal("0.45") < tc_value < Decimal("0.55")


class TestKellyCalculator:
    """Tests for Kelly criterion calculations."""

    def test_kelly_criterion_formula(self):
        """Test basic Kelly criterion formula."""
        # 60% win rate, even money
        kelly = kelly_criterion(0.6, 1.0, 1.0)
        # Should be (1*0.6 - 0.4) / 1 = 0.2
        assert abs(kelly - 0.2) < 0.01

    def test_kelly_no_bet_negative_ev(self):
        """Test Kelly returns 0 for negative EV."""
        kelly = kelly_criterion(0.4, 1.0, 1.0)  # 40% win = negative EV
        assert kelly == 0.0

    def test_kelly_calculator_optimal_bet(self):
        """Test KellyCalculator optimal bet."""
        calc = KellyCalculator(
            bankroll=Decimal("10000"),
            min_bet=Decimal("10"),
            max_bet=Decimal("500"),
            kelly_fraction=1.0,
        )

        # 1% edge = 100 unit bet with full Kelly
        bet = calc.optimal_bet(Decimal("0.01"))
        assert bet == Decimal("100")

    def test_half_kelly(self):
        """Test half Kelly fraction."""
        calc = KellyCalculator(
            bankroll=Decimal("10000"),
            min_bet=Decimal("10"),
            max_bet=Decimal("500"),
            kelly_fraction=0.5,  # Half Kelly
        )

        bet = calc.optimal_bet(Decimal("0.01"))
        assert bet == Decimal("50")  # Half of 100

    def test_kelly_respects_table_limits(self):
        """Test Kelly respects min/max bet."""
        calc = KellyCalculator(
            bankroll=Decimal("10000"),
            min_bet=Decimal("25"),
            max_bet=Decimal("100"),
            kelly_fraction=1.0,
        )

        # 2% edge would suggest 200 bet, but max is 100
        bet = calc.optimal_bet(Decimal("0.02"))
        assert bet == Decimal("100")

        # Negative edge still bets minimum
        bet_neg = calc.optimal_bet(Decimal("-0.01"))
        assert bet_neg == Decimal("25")


class TestBankrollManager:
    """Tests for bankroll management."""

    def test_risk_of_ruin_positive_edge(self):
        """Test RoR is low with positive edge."""
        manager = BankrollManager(
            bankroll=Decimal("10000"),
            min_bet=Decimal("10"),
            max_bet=Decimal("100"),
            player_edge=Decimal("0.01"),  # 1% edge
        )

        ror = manager.risk_of_ruin()
        assert ror.probability < 0.05  # Should be very low

    def test_risk_of_ruin_negative_edge(self):
        """Test RoR is 100% with negative edge."""
        manager = BankrollManager(
            bankroll=Decimal("10000"),
            min_bet=Decimal("10"),
            max_bet=Decimal("100"),
            player_edge=Decimal("-0.01"),  # -1% edge
        )

        ror = manager.risk_of_ruin()
        assert ror.probability == 1.0

    def test_session_stop_loss(self):
        """Test session stop-loss calculation."""
        manager = BankrollManager(
            bankroll=Decimal("10000"),
            min_bet=Decimal("10"),
            max_bet=Decimal("100"),
        )

        stop_loss = manager.session_stop_loss(0.1)  # 10% of bankroll
        assert stop_loss == Decimal("1000")

    def test_units_in_bankroll(self):
        """Test betting units calculation."""
        manager = BankrollManager(
            bankroll=Decimal("10000"),
            min_bet=Decimal("25"),
            max_bet=Decimal("100"),
        )

        units = manager.units_in_bankroll()
        assert units == 400  # 10000 / 25

    def test_bet_ramp(self):
        """Test bet ramp based on true count."""
        manager = BankrollManager(
            bankroll=Decimal("10000"),
            min_bet=Decimal("10"),
            max_bet=Decimal("200"),
        )

        # Below threshold: min bet
        assert manager.bet_ramp(-1.0, Decimal("10")) == Decimal("10")
        assert manager.bet_ramp(0.5, Decimal("10")) == Decimal("10")

        # At threshold: 1 unit
        assert manager.bet_ramp(1.0, Decimal("10")) == Decimal("10")

        # Above threshold: increasing
        assert manager.bet_ramp(2.0, Decimal("10")) == Decimal("20")
        assert manager.bet_ramp(5.0, Decimal("10")) == Decimal("50")
