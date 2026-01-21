"""Tests for performance stats persistence (serialization/deserialization)."""

import pytest

from api.routes.stats import (
    _serialize_performance_stats,
    _deserialize_performance_stats,
)
from api.schemas import PerformanceStats, SessionHistoryEntry


class TestStatsSerialization:
    """Tests for performance stats serialization."""

    def test_serialize_performance_stats(self):
        """Test that performance stats are serialized correctly."""
        stats = PerformanceStats(
            hands_played=50,
            wins=25,
            losses=20,
            pushes=5,
            blackjacks=3,
            total_wagered=5000.0,
            net_result=250.0,
            count_drills_attempted=100,
            count_drills_correct=85,
            count_average_error=0.5,
            strategy_drills_attempted=75,
            strategy_drills_correct=70,
        )

        serialized = _serialize_performance_stats(stats)

        assert serialized["hands_played"] == 50
        assert serialized["wins"] == 25
        assert serialized["losses"] == 20
        assert serialized["pushes"] == 5
        assert serialized["blackjacks"] == 3
        assert serialized["total_wagered"] == 5000.0
        assert serialized["net_result"] == 250.0
        assert serialized["count_drills_attempted"] == 100
        assert serialized["count_drills_correct"] == 85
        assert serialized["count_average_error"] == 0.5
        assert serialized["strategy_drills_attempted"] == 75
        assert serialized["strategy_drills_correct"] == 70

    def test_deserialize_performance_stats(self):
        """Test that performance stats are deserialized correctly."""
        data = {
            "hands_played": 30,
            "wins": 15,
            "losses": 12,
            "pushes": 3,
            "blackjacks": 2,
            "total_wagered": 3000.0,
            "net_result": 150.0,
            "count_drills_attempted": 50,
            "count_drills_correct": 45,
            "count_average_error": 0.3,
            "strategy_drills_attempted": 40,
            "strategy_drills_correct": 38,
            "deviation_drills_attempted": 20,
            "deviation_drills_correct": 18,
            "speed_drills_attempted": 10,
            "speed_drills_correct": 8,
            "speed_drill_best_score": 95,
            "speed_drill_best_time_ms": 15000,
            "history": [],
        }

        stats = _deserialize_performance_stats(data)

        assert stats.hands_played == 30
        assert stats.wins == 15
        assert stats.losses == 12
        assert stats.pushes == 3
        assert stats.blackjacks == 2
        assert stats.total_wagered == 3000.0
        assert stats.net_result == 150.0
        assert stats.count_drills_attempted == 50
        assert stats.count_drills_correct == 45
        assert stats.count_average_error == 0.3
        assert stats.strategy_drills_attempted == 40
        assert stats.strategy_drills_correct == 38
        assert stats.deviation_drills_attempted == 20
        assert stats.deviation_drills_correct == 18
        assert stats.speed_drills_attempted == 10
        assert stats.speed_drills_correct == 8
        assert stats.speed_drill_best_score == 95
        assert stats.speed_drill_best_time_ms == 15000

    def test_stats_roundtrip_preserves_history(self):
        """Test that history is preserved through roundtrip."""
        history = [
            SessionHistoryEntry(
                timestamp=1000000,
                bankroll=1050.0,
                event_type="hand_result",
                details={"outcome": "win"},
            ),
            SessionHistoryEntry(
                timestamp=1000100,
                bankroll=1000.0,
                event_type="hand_result",
                details={"outcome": "loss"},
            ),
            SessionHistoryEntry(
                timestamp=1000200,
                bankroll=1100.0,
                running_count=5,
                true_count=2.5,
                event_type="drill_result",
                details={"correct": True},
            ),
        ]
        stats = PerformanceStats(
            hands_played=3,
            wins=1,
            losses=1,
            pushes=1,
            history=history,
        )

        serialized = _serialize_performance_stats(stats)
        restored = _deserialize_performance_stats(serialized)

        assert len(restored.history) == 3
        assert restored.history[0].timestamp == 1000000
        assert restored.history[0].bankroll == 1050.0
        assert restored.history[0].event_type == "hand_result"
        assert restored.history[0].details == {"outcome": "win"}

        assert restored.history[2].running_count == 5
        assert restored.history[2].true_count == 2.5

    def test_deserialize_with_missing_fields_uses_defaults(self):
        """Test that missing fields get default values."""
        # Minimal data
        data = {
            "hands_played": 10,
            "wins": 5,
        }

        stats = _deserialize_performance_stats(data)

        assert stats.hands_played == 10
        assert stats.wins == 5
        assert stats.losses == 0  # Default
        assert stats.pushes == 0  # Default
        assert stats.blackjacks == 0  # Default
        assert stats.total_wagered == 0.0  # Default
        assert stats.net_result == 0.0  # Default
        assert stats.count_drills_attempted == 0  # Default
        assert stats.count_drills_correct == 0  # Default
        assert stats.count_average_error == 0.0  # Default
        assert stats.strategy_drills_attempted == 0  # Default
        assert stats.strategy_drills_correct == 0  # Default
        assert stats.history == []  # Default

    def test_serialize_empty_stats(self):
        """Test serializing empty (default) stats."""
        stats = PerformanceStats()

        serialized = _serialize_performance_stats(stats)

        assert serialized["hands_played"] == 0
        assert serialized["wins"] == 0
        assert serialized["losses"] == 0
        assert serialized["history"] == []

    def test_roundtrip_preserves_speed_drill_stats(self):
        """Test that speed drill stats are preserved."""
        stats = PerformanceStats(
            speed_drills_attempted=25,
            speed_drills_correct=20,
            speed_drill_best_score=98,
            speed_drill_best_time_ms=12500,
        )

        serialized = _serialize_performance_stats(stats)
        restored = _deserialize_performance_stats(serialized)

        assert restored.speed_drills_attempted == 25
        assert restored.speed_drills_correct == 20
        assert restored.speed_drill_best_score == 98
        assert restored.speed_drill_best_time_ms == 12500

    def test_roundtrip_with_none_speed_time(self):
        """Test roundtrip when speed_drill_best_time_ms is None."""
        stats = PerformanceStats(
            speed_drills_attempted=5,
            speed_drills_correct=3,
            speed_drill_best_score=50,
            speed_drill_best_time_ms=None,
        )

        serialized = _serialize_performance_stats(stats)
        restored = _deserialize_performance_stats(serialized)

        assert restored.speed_drill_best_time_ms is None


class TestSessionStatsCalculations:
    """Tests for session stats calculations."""

    def test_win_rate_calculation(self):
        """Test win rate calculation logic."""
        # Test basic win rate calculation
        hands_played = 100
        wins = 45

        win_rate = wins / hands_played if hands_played > 0 else 0.0

        assert win_rate == 0.45

    def test_win_rate_zero_hands(self):
        """Test win rate when no hands played."""
        hands_played = 0
        wins = 0

        win_rate = wins / hands_played if hands_played > 0 else 0.0

        assert win_rate == 0.0

    def test_counting_accuracy_calculation(self):
        """Test counting accuracy calculation."""
        count_drills_attempted = 80
        count_drills_correct = 72

        counting_accuracy = None
        if count_drills_attempted > 0:
            counting_accuracy = count_drills_correct / count_drills_attempted

        assert counting_accuracy == 0.9

    def test_counting_accuracy_none_when_no_attempts(self):
        """Test counting accuracy is None when no attempts."""
        count_drills_attempted = 0
        count_drills_correct = 0

        counting_accuracy = None
        if count_drills_attempted > 0:
            counting_accuracy = count_drills_correct / count_drills_attempted

        assert counting_accuracy is None

    def test_strategy_accuracy_none_when_no_attempts(self):
        """Test strategy accuracy is None when no attempts."""
        strategy_drills_attempted = 0
        strategy_drills_correct = 0

        strategy_accuracy = None
        if strategy_drills_attempted > 0:
            strategy_accuracy = strategy_drills_correct / strategy_drills_attempted

        assert strategy_accuracy is None

    def test_strategy_accuracy_calculation(self):
        """Test strategy accuracy calculation."""
        strategy_drills_attempted = 50
        strategy_drills_correct = 48

        strategy_accuracy = None
        if strategy_drills_attempted > 0:
            strategy_accuracy = strategy_drills_correct / strategy_drills_attempted

        assert strategy_accuracy == 0.96


class TestHistoryEntryPersistence:
    """Tests for SessionHistoryEntry persistence."""

    def test_history_entry_with_all_fields(self):
        """Test history entry with all optional fields."""
        entry = SessionHistoryEntry(
            timestamp=1705500000000,
            bankroll=1250.50,
            running_count=8,
            true_count=3.2,
            event_type="hand_result",
            details={"outcome": "win", "hand_value": 21},
        )

        # Serialize through model_dump (used in _serialize_performance_stats)
        dumped = entry.model_dump()

        assert dumped["timestamp"] == 1705500000000
        assert dumped["bankroll"] == 1250.50
        assert dumped["running_count"] == 8
        assert dumped["true_count"] == 3.2
        assert dumped["event_type"] == "hand_result"
        assert dumped["details"]["outcome"] == "win"

    def test_history_entry_with_minimal_fields(self):
        """Test history entry with only required fields."""
        entry = SessionHistoryEntry(
            timestamp=1705500000000,
            bankroll=1000.0,
            event_type="session_start",
        )

        dumped = entry.model_dump()

        assert dumped["timestamp"] == 1705500000000
        assert dumped["bankroll"] == 1000.0
        assert dumped["event_type"] == "session_start"
        assert dumped["running_count"] is None
        assert dumped["true_count"] is None
        assert dumped["details"] is None

    def test_history_entry_roundtrip(self):
        """Test history entry roundtrip through dict."""
        original = SessionHistoryEntry(
            timestamp=1705500000000,
            bankroll=900.0,
            running_count=-2,
            true_count=-0.8,
            event_type="drill_result",
            details={"drill_type": "counting", "correct": False},
        )

        # Simulate roundtrip
        dumped = original.model_dump()
        restored = SessionHistoryEntry(**dumped)

        assert restored.timestamp == original.timestamp
        assert restored.bankroll == original.bankroll
        assert restored.running_count == original.running_count
        assert restored.true_count == original.true_count
        assert restored.event_type == original.event_type
        assert restored.details == original.details
