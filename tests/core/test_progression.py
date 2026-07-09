"""Tests for core/progression: XP, profile events, badges, skill tree."""

from datetime import date, timedelta

import pytest

from core.progression import (
    BADGES,
    SKILL_TREE,
    apply_event,
    evaluate_badges,
    level_for_xp,
    new_profile,
    recompute_tree,
    title_for_level,
    xp_to_reach_level,
)
from core.progression.profile import PlayerProfile

TODAY = date(2026, 7, 9)


class TestXP:
    def test_level_curve_monotonic(self):
        costs = [xp_to_reach_level(n) for n in range(1, 30)]
        assert costs == sorted(costs)
        assert costs[0] == 0  # level 1 is free

    def test_level_for_xp_roundtrip(self):
        for level in (1, 2, 5, 10, 20):
            xp = xp_to_reach_level(level)
            assert level_for_xp(xp) == level
            if level > 1:
                assert level_for_xp(xp - 1) == level - 1

    def test_titles_progress(self):
        assert title_for_level(1) == "Tourist"
        assert title_for_level(100) == "Legend of the Strip"


class TestApplyEvent:
    def test_correct_deviation_beats_plain_play(self):
        p1 = new_profile()
        d1 = apply_event(
            p1, "decision",
            {"correct": True, "is_deviation": True, "visibility": "hidden"},
            today=TODAY,
        )
        p2 = new_profile()
        d2 = apply_event(
            p2, "decision",
            {"correct": True, "is_deviation": False, "visibility": "hidden"},
            today=TODAY,
        )
        assert d1.xp_gained > d2.xp_gained

    def test_hidden_play_beats_visible_play(self):
        p1 = new_profile()
        d1 = apply_event(
            p1, "decision",
            {"correct": True, "visibility": "hidden"},
            today=TODAY,
        )
        p2 = new_profile()
        d2 = apply_event(
            p2, "decision",
            {"correct": True, "visibility": "always"},
            today=TODAY,
        )
        assert d1.xp_gained > d2.xp_gained

    def test_no_xp_for_money(self):
        profile = new_profile()
        delta = apply_event(profile, "round", {"result": 500}, today=TODAY)
        assert delta.xp_gained == 0
        assert profile.lifetime["hands_won"] == 1

    def test_wrong_decision_no_xp(self):
        profile = new_profile()
        delta = apply_event(
            profile, "decision",
            {"correct": False, "visibility": "hidden"},
            today=TODAY,
        )
        assert delta.xp_gained == 0
        assert profile.lifetime["decisions"] == 1

    def test_streak_counts_consecutive_days(self):
        profile = new_profile()
        apply_event(profile, "decision", {"correct": True}, today=TODAY)
        assert profile.streak.current == 1
        apply_event(profile, "decision", {"correct": True}, today=TODAY)
        assert profile.streak.current == 1  # same day
        apply_event(
            profile, "decision", {"correct": True},
            today=TODAY + timedelta(days=1),
        )
        assert profile.streak.current == 2
        # A gap resets
        apply_event(
            profile, "decision", {"correct": True},
            today=TODAY + timedelta(days=5),
        )
        assert profile.streak.current == 1
        assert profile.streak.best == 2

    def test_kelly_streak_tracks_consecutive_in_band(self):
        profile = new_profile()
        for _ in range(5):
            apply_event(profile, "bet", {"in_band": True}, today=TODAY)
        assert profile.lifetime["kelly_streak"] == 5
        apply_event(profile, "bet", {"in_band": False}, today=TODAY)
        assert profile.lifetime["kelly_streak"] == 0
        assert profile.lifetime["kelly_streak_best"] == 5

    def test_drill_windows_bounded(self):
        profile = new_profile()
        for _ in range(150):
            apply_event(
                profile, "drill",
                {"drill_key": "strategy", "correct": True},
                today=TODAY,
            )
        assert len(profile.drill_windows["strategy"]) == 100

    def test_daily_complete_recorded(self):
        profile = new_profile()
        delta = apply_event(
            profile, "daily_complete",
            {
                "date": "2026-07-09", "score": 812, "grade": "A",
                "decisions_pct": 90.0, "counts_pct": 100.0, "net": 55.0,
            },
            today=TODAY,
        )
        assert delta.xp_gained >= 50
        assert profile.daily["2026-07-09"].score == 812

    def test_level_up_flag(self):
        profile = new_profile()
        delta = None
        for _ in range(30):
            delta = apply_event(
                profile, "checkin", {"exact": True}, today=TODAY
            )
            if delta.level_up:
                break
        assert profile.level >= 2


class TestBadges:
    def test_no_outcome_badges(self):
        """Winning money is luck, not skill — no badge may trigger on it."""
        profile = new_profile()
        delta = apply_event(profile, "round", {"result": 500}, today=TODAY)
        assert delta.badges_awarded == []

    def test_twenty_second_deck(self):
        profile = new_profile()
        delta = apply_event(
            profile, "drill",
            {"drill_key": "speed", "correct": True, "num_cards": 52, "time_ms": 19500},
            today=TODAY,
        )
        assert "twenty-second-deck" in delta.badges_awarded

    def test_slow_deck_no_badge(self):
        profile = new_profile()
        delta = apply_event(
            profile, "drill",
            {"drill_key": "speed", "correct": True, "num_cards": 52, "time_ms": 31000},
            today=TODAY,
        )
        assert "twenty-second-deck" not in delta.badges_awarded

    def test_index_play_expert_needs_full_window(self):
        profile = new_profile()
        # 49 perfect attempts: window not full yet
        for _ in range(49):
            delta = apply_event(
                profile, "drill",
                {"drill_key": "deviation", "correct": True},
                today=TODAY,
            )
            assert "index-play-expert" not in delta.badges_awarded
        delta = apply_event(
            profile, "drill",
            {"drill_key": "deviation", "correct": True},
            today=TODAY,
        )
        assert "index-play-expert" in delta.badges_awarded

    def test_iron_streak(self):
        profile = new_profile()
        delta = None
        for offset in range(7):
            delta = apply_event(
                profile, "decision", {"correct": True},
                today=TODAY + timedelta(days=offset),
            )
        assert "iron-streak-7" in delta.badges_awarded

    def test_badges_award_xp(self):
        profile = new_profile()
        delta = apply_event(
            profile, "drill",
            {"drill_key": "speed", "correct": True, "num_cards": 52, "time_ms": 18000},
            today=TODAY,
        )
        assert "twenty-second-deck" in delta.badges_awarded
        assert delta.xp_gained >= 25  # includes the badge bonus

    def test_all_predicates_have_defs(self):
        from core.progression.badges import PREDICATES

        assert set(PREDICATES) == set(BADGES)


class TestSkillTree:
    def test_first_node_available_on_new_profile(self):
        profile = new_profile()
        assert profile.nodes["basic-strategy"].status == "available"
        assert profile.nodes["card-values"].status == "locked"

    def test_mastery_unlocks_dependents(self):
        profile = new_profile()
        for _ in range(40):
            apply_event(
                profile, "drill",
                {"drill_key": "strategy", "correct": True},
                today=TODAY,
            )
        assert profile.nodes["basic-strategy"].status == "mastered"
        assert profile.nodes["card-values"].status in ("available", "in_progress")

    def test_mastery_is_sticky(self):
        profile = new_profile()
        for _ in range(40):
            apply_event(
                profile, "drill",
                {"drill_key": "strategy", "correct": True},
                today=TODAY,
            )
        assert profile.nodes["basic-strategy"].status == "mastered"
        # A cold streak cannot demote a mastered node
        for _ in range(40):
            apply_event(
                profile, "drill",
                {"drill_key": "strategy", "correct": False},
                today=TODAY,
            )
        assert profile.nodes["basic-strategy"].status == "mastered"

    def test_below_threshold_not_mastered(self):
        profile = new_profile()
        for i in range(40):
            apply_event(
                profile, "drill",
                {"drill_key": "strategy", "correct": i % 2 == 0},  # 50%
                today=TODAY,
            )
        assert profile.nodes["basic-strategy"].status == "in_progress"
        assert profile.nodes["basic-strategy"].progress < 1.0

    def test_node_mastery_awards_xp(self):
        profile = new_profile()
        total = 0
        for _ in range(40):
            delta = apply_event(
                profile, "drill",
                {"drill_key": "strategy", "correct": True},
                today=TODAY,
            )
            total += delta.xp_gained
            if "basic-strategy" in delta.node_changes and delta.node_changes["basic-strategy"] == "mastered":
                assert delta.xp_gained >= 100
                return
        pytest.fail("basic-strategy never mastered")

    def test_counter_node(self):
        profile = new_profile()
        # Master prerequisites' chain is irrelevant for progress tracking;
        # deck-countdown progress accrues from the lifetime counter
        for _ in range(3):
            apply_event(
                profile, "drill",
                {"drill_key": "speed", "correct": True, "num_cards": 52, "time_ms": 25000},
                today=TODAY,
            )
        assert profile.lifetime["deck_countdown_pass"] == 3

    def test_tree_definitions_consistent(self):
        for node in SKILL_TREE.values():
            for prereq in node.prerequisites:
                assert prereq in SKILL_TREE, f"{node.id} requires unknown {prereq}"
            if node.mastery.metric == "accuracy":
                assert node.mastery.window > 0
                assert node.mastery.min_attempts > 0
            else:
                assert node.mastery.counter_key


class TestSerialization:
    def test_profile_round_trip(self):
        profile = new_profile()
        apply_event(profile, "round", {"result": 25}, today=TODAY)
        apply_event(
            profile, "drill",
            {"drill_key": "strategy", "correct": True},
            today=TODAY,
        )
        data = profile.model_dump()
        restored = PlayerProfile.model_validate(data)
        assert restored.xp == profile.xp
        assert restored.badges == profile.badges
        assert restored.nodes["basic-strategy"].status == profile.nodes["basic-strategy"].status
        assert restored.streak.current == profile.streak.current

    def test_json_round_trip(self):
        profile = new_profile()
        apply_event(profile, "checkin", {"exact": True}, today=TODAY)
        raw = profile.model_dump_json()
        restored = PlayerProfile.model_validate_json(raw)
        assert restored.xp == profile.xp
