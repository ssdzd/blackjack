"""Tests for the daily challenge: determinism, scoring, sharing."""

from datetime import date
from decimal import Decimal
from random import Random

from api.game_session import TrainingGameSession
from core.progression.daily import (
    challenge_for_date,
    emoji_grid,
    score_daily,
    share_payload,
)


class TestDeterminism:
    def test_same_date_same_seed(self):
        a = challenge_for_date(date(2026, 7, 9))
        b = challenge_for_date(date(2026, 7, 9))
        assert a.seed == b.seed
        assert a.number == b.number

    def test_different_dates_differ(self):
        a = challenge_for_date(date(2026, 7, 9))
        b = challenge_for_date(date(2026, 7, 10))
        assert a.seed != b.seed
        assert b.number == a.number + 1

    def test_seeded_games_deal_identical_sequences(self):
        challenge = challenge_for_date(date(2026, 7, 9))

        def draw_cards(seed):
            session = TrainingGameSession(
                rules=challenge.rules,
                initial_bankroll=Decimal(challenge.bankroll),
                rng=Random(seed),
            )
            return [str(session.game.shoe.draw()) for _ in range(100)]

        assert draw_cards(challenge.seed) == draw_cards(challenge.seed)

    def test_twenty_rounds_fit_before_cut_card(self):
        challenge = challenge_for_date(date(2026, 7, 9))
        session = TrainingGameSession(
            rules=challenge.rules,
            initial_bankroll=Decimal(challenge.bankroll),
            rng=Random(challenge.seed),
        )
        game = session.game
        shuffles = 0

        def watch(event):
            nonlocal shuffles
            if event.event_type.name == "SHOE_SHUFFLED":
                shuffles += 1

        game.subscribe(watch)
        rounds = 0
        while rounds < 20 and game.state.name == "WAITING_FOR_BET":
            if not game.bet(10):
                break
            if game.state.name == "OFFERING_INSURANCE":
                game.decline_insurance()
            while game.state.name == "PLAYER_TURN":
                game.stand()
            rounds += 1
        assert rounds == 20
        assert shuffles == 0  # a mid-challenge reshuffle would fork shared fate


class TestScoring:
    def test_perfect_run(self):
        score = score_daily([True] * 30, [True, True, True], net=120.0)
        assert score.score == 1000
        assert score.grade == "S"

    def test_skill_dominates_money(self):
        skilled_loser = score_daily([True] * 30, [True] * 3, net=-200.0)
        lucky_fumbler = score_daily([False] * 30, [False] * 3, net=500.0)
        assert skilled_loser.score > lucky_fumbler.score
        assert skilled_loser.score == 900  # everything except the money bucket

    def test_push_gets_half_money_bucket(self):
        pushed = score_daily([True] * 10, [True], net=0.0)
        assert pushed.breakdown["bankroll"] == 50

    def test_grades_band(self):
        assert score_daily([True] * 9 + [False], [True] * 3, net=1).grade in ("A", "S")
        assert score_daily([False] * 10, [False] * 3, net=-10).grade == "F"

    def test_empty_decisions_scores_zero_decisions(self):
        score = score_daily([], [], net=0.0)
        assert score.decisions_pct == 0.0
        assert score.breakdown["decisions"] == 0


class TestSharing:
    def test_emoji_grid_rows_of_five(self):
        grid = emoji_grid(["perfect"] * 5 + ["mixed"] * 5 + ["wrong"] * 5 + ["none"] * 5)
        rows = grid.split("\n")
        assert len(rows) == 4
        assert rows[0] == "🟩🟩🟩🟩🟩"
        assert rows[1] == "🟨🟨🟨🟨🟨"
        assert rows[2] == "🟥🟥🟥🟥🟥"
        assert rows[3] == "⬜⬜⬜⬜⬜"

    def test_share_text_contains_essentials(self):
        challenge = challenge_for_date(date(2026, 7, 9))
        score = score_daily([True] * 18 + [False] * 2, [True, True, False], net=45.0)
        payload = share_payload(challenge, score, ["perfect"] * 20)
        assert f"Daily #{challenge.number}" in payload["share_text"]
        assert str(score.score) in payload["share_text"]
        assert "🟩" in payload["share_text"]
