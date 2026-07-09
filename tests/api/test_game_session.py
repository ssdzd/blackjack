"""Tests for the server-authoritative TrainingGameSession."""

from decimal import Decimal
from random import Random

import pytest

from api.game_session import TrainingGameSession, RULE_PRESETS
from core.cards import Rank
from core.strategy.rules import RuleSet

HILO_TAGS = {
    Rank.TWO: 1, Rank.THREE: 1, Rank.FOUR: 1, Rank.FIVE: 1, Rank.SIX: 1,
    Rank.SEVEN: 0, Rank.EIGHT: 0, Rank.NINE: 0,
    Rank.TEN: -1, Rank.JACK: -1, Rank.QUEEN: -1, Rank.KING: -1, Rank.ACE: -1,
}


def make_session(seed: int | None = None, **kwargs) -> TrainingGameSession:
    rng = Random(seed) if seed is not None else None
    return TrainingGameSession(rng=rng, **kwargs)


def visible_cards(session):
    """All cards on the table after a resolved round (first round of shoe)."""
    cards = list(session.game.dealer_hand.cards)
    for hand in session.game.player.hands:
        cards.extend(hand.cards)
    return cards


def play_round_stand(session) -> bool:
    """Bet and stand through one round. Returns True if a round resolved."""
    game = session.game
    if not game.bet(10):
        return False
    # Insurance offer or instant blackjack may occur
    if game.state.name == "OFFERING_INSURANCE":
        game.decline_insurance()
    if game.state.name == "PLAYER_TURN":
        game.stand()
    return game.state.name in ("WAITING_FOR_BET", "ROUND_COMPLETE", "GAME_OVER")


class TestServerCounting:
    """The counter must track exactly the cards a player could see."""

    def test_full_round_counts_every_visible_card(self):
        session = make_session(seed=7)
        assert play_round_stand(session)

        expected = sum(HILO_TAGS[c.rank] for c in visible_cards(session))
        assert session.counter.running_count == expected
        assert session.counter.cards_seen == len(visible_cards(session))

    def test_hole_card_counted_exactly_once_across_rounds(self):
        session = make_session(seed=11)
        for _ in range(5):
            play_round_stand(session)
        # cards_seen must equal cards dealt from the shoe (all are visible
        # once rounds resolve)
        assert session.counter.cards_seen == session.game.shoe.cards_dealt

    def test_hole_card_counted_when_player_busts_all(self):
        """Bust-out rounds never emit DEALER_REVEALS; the sweep must count
        the hole card at round end anyway."""
        for seed in range(300):
            session = make_session(seed=seed)
            game = session.game
            if not game.bet(10):
                continue
            if game.state.name == "OFFERING_INSURANCE":
                game.decline_insurance()
            busted = False
            while game.state.name == "PLAYER_TURN":
                game.hit()
                if all(h.is_busted for h in game.player.hands):
                    busted = True
            if not busted or len(game.dealer_hand.cards) != 2:
                continue
            expected = sum(HILO_TAGS[c.rank] for c in visible_cards(session))
            assert session.counter.running_count == expected
            assert session.counter.cards_seen == len(visible_cards(session))
            return
        pytest.fail("no bust-out round found in 300 seeds")

    def test_shuffle_resets_count(self):
        session = make_session(seed=3)
        # Play until the cut card forces a reshuffle
        for _ in range(80):
            play_round_stand(session)
            if session.counter.cards_seen < 10:
                # A shuffle happened recently; count restarted mid-stream
                break
        assert session.counter.cards_seen <= session.game.shoe.cards_dealt

    def test_ko_initial_running_count(self):
        session = make_session(counting_system="ko")
        # KO IRC for 6 decks: 4 - 4*6 = -20
        assert session.counter.running_count == -20
        assert session.true_count is None  # unbalanced: no TC

    def test_true_count_uses_decks_remaining(self):
        session = make_session(seed=5)
        play_round_stand(session)
        rc = session.counter.running_count
        expected_tc = rc / session.game.shoe.decks_remaining
        assert session.true_count == pytest.approx(expected_tc)


class TestGrading:
    def _hunt(self, predicate, max_seeds=500, **session_kwargs):
        """Find a seeded session whose first deal matches a predicate."""
        for seed in range(max_seeds):
            session = make_session(seed=seed, **session_kwargs)
            game = session.game
            if not game.bet(10):
                continue
            if game.state.name != "PLAYER_TURN":
                continue
            hand = game.player.current_hand
            upcard = game.dealer_hand.cards[0].value
            if predicate(hand, upcard, game):
                return session
        pytest.fail("no matching deal found")

    def test_hard_16_vs_10_grades_surrender_then_deviates_to_stand(self):
        session = self._hunt(
            lambda hand, up, game: (
                hand.value == 16
                and not hand.is_soft
                and not hand.is_pair
                and up == 10
                and game.can_surrender
            )
        )

        # Force a clearly negative count: basic strategy applies (surrender)
        session.counter._running_count = -12.0
        grade = session.grade_action("hit")
        assert grade is not None
        assert grade.correct_action == "surrender"
        assert grade.is_correct is False
        assert grade.is_deviation is False

        # Force TC >= 0: Illustrious 18 says stand 16 vs 10
        session.counter._running_count = 6.0
        grade = session.grade_action("stand")
        assert grade.correct_action == "stand"
        assert grade.is_correct is True
        assert grade.is_deviation is True
        assert grade.deviation is not None
        assert "16" in grade.deviation["description"]

    def test_grade_includes_dealer_bust_probability(self):
        session = self._hunt(lambda hand, up, game: up == 6)
        grade = session.grade_action("stand")
        assert grade.why["dealer_bust_pct"] > 30  # 6 is the bust card

    def test_grade_action_none_outside_player_turn(self):
        session = make_session(seed=2)
        assert session.grade_action("hit") is None

    def test_insurance_grading_by_count(self):
        session = make_session(seed=2)
        session.counter._running_count = 30.0  # TC ~ +5
        grade = session.grade_insurance(True)
        assert grade.correct_action == "take"
        assert grade.is_correct is True

        session.counter._running_count = 0.0
        grade = session.grade_insurance(True)
        assert grade.correct_action == "decline"
        assert grade.is_correct is False

    def test_bet_grading_band(self):
        session = make_session(seed=2)
        # Negative edge: optimal collapses to table minimum
        grade = session.grade_bet(10)
        assert grade.is_correct is True
        assert int(grade.correct_action) == session.rules.min_bet

        # Rich count: min bet is under-betting the edge
        session.counter._running_count = 36.0  # TC ~ +6
        grade = session.grade_bet(10)
        assert int(grade.correct_action) > session.rules.min_bet

    def test_count_checkin_grading(self):
        session = make_session(seed=4)
        play_round_stand(session)
        actual = session.counter.running_count
        exact = session.grade_count_checkin(actual)
        assert exact["correct"] is True
        near = session.grade_count_checkin(actual + 1)
        assert near["correct"] is False
        assert near["close"] is True
        far = session.grade_count_checkin(actual + 5)
        assert far["close"] is False


class TestQuantSnapshot:
    def test_snapshot_keys_and_ranges(self):
        session = make_session(seed=9)
        play_round_stand(session)
        snap = session.quant_snapshot()

        assert snap["house_edge_pct"] > 0
        assert isinstance(snap["kelly_bet"], int)
        assert snap["kelly_bet"] >= session.rules.min_bet
        assert 0 <= snap["risk_of_ruin_pct"] <= 100
        assert snap["dealer_upcard"] in range(2, 12)
        assert 0 < snap["dealer_bust_pct"] < 100

    def test_positive_count_improves_edge(self):
        session = make_session(seed=9)
        base = session.quant_snapshot()["player_edge_pct"]
        session.counter._running_count = 18.0
        rich = session.quant_snapshot()["player_edge_pct"]
        assert rich > base


class TestStatePayload:
    def test_v2_payload_keeps_legacy_fields(self):
        session = make_session(seed=1)
        payload = session.state_payload()

        # Legacy contract (v1 clients)
        for key in (
            "state", "player_hands", "current_hand_index", "dealer_hand",
            "dealer_showing", "bankroll", "can_hit", "can_stand", "can_double",
            "can_split", "can_surrender", "can_insure", "insurance_bet",
            "shoe_cards_remaining", "shoe_decks_remaining",
        ):
            assert key in payload

        # v2 additions
        assert payload["v"] == 2
        assert payload["rules"]["min_bet"] == session.rules.min_bet
        assert payload["rules"]["house_edge_pct"] > 0

    def test_visibility_gates_count(self):
        always = make_session(seed=1, visibility="always")
        assert "count" in always.state_payload()
        assert "quant" in always.state_payload()

        hidden = make_session(seed=1, visibility="hidden")
        payload = hidden.state_payload()
        assert "count" not in payload
        assert "quant" not in payload

        # Explicit reveal (on_request flow)
        assert "count" in hidden.state_payload(include_count=True)

    def test_hole_card_hidden_during_player_turn(self):
        for seed in range(100):
            session = make_session(seed=seed)
            if not session.game.bet(10):
                continue
            if session.game.state.name != "PLAYER_TURN":
                continue
            payload = session.state_payload()
            assert payload["dealer_hand"]["cards"][1]["hidden"] is True
            return
        pytest.fail("no plain player turn found")

    def test_rules_presets_change_payload(self):
        session = TrainingGameSession(rules=RULE_PRESETS["single_deck"]())
        payload = session.state_payload()
        assert payload["rules"]["num_decks"] == 1
        assert payload["shoe_cards_remaining"] <= 52


class TestConfiguration:
    def test_set_counting_system_resets_count(self):
        session = make_session(seed=6)
        play_round_stand(session)
        assert session.counter.cards_seen > 0

        session.set_counting_system("omega2")
        assert session.counting_system_name == "omega2"
        assert session.counter.cards_seen == 0

    def test_set_counting_system_ko_gets_irc(self):
        session = make_session(seed=6)
        session.set_counting_system("ko")
        assert session.counter.running_count == -20

    def test_shoe_sized_from_rules(self):
        session = TrainingGameSession(rules=RuleSet(num_decks=8))
        assert session.game.shoe.total_cards == 8 * 52

    def test_seeded_sessions_deal_identically(self):
        a = make_session(seed=42)
        b = make_session(seed=42)
        play_round_stand(a)
        play_round_stand(b)
        assert [str(c) for c in visible_cards(a)] == [str(c) for c in visible_cards(b)]
