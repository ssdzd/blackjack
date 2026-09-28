"""Tests for career venues and the heat model."""

from datetime import date

from core.progression import (
    VENUES,
    apply_event,
    apply_heat,
    can_enter,
    gates_met,
    heat_events,
    is_backed_off,
    new_profile,
    next_venue_id,
)

TODAY = date(2026, 7, 9)


class TestVenues:
    def test_ladder_edges_rise_with_stakes_reasonably(self):
        for venue in VENUES.values():
            edge = venue.house_edge_pct
            if venue.trap:
                assert edge > 1.5, "the trap must be visibly terrible"
            else:
                assert -0.5 < edge < 1.0, f"{venue.id} edge {edge} out of band"

    def test_trap_is_six_to_five(self):
        trap = VENUES["neon-mirage"]
        assert trap.trap
        assert trap.target is None
        assert "6:5" in trap.rules_summary()

    def test_first_venue_open_others_locked(self):
        profile = new_profile()
        assert can_enter(VENUES["kitchen-table"], profile)
        assert not can_enter(VENUES["riverboat"], profile)  # not unlocked yet
        assert can_enter(VENUES["neon-mirage"], profile)  # traps are always open

    def test_completion_unlocks_next_rung(self):
        profile = new_profile()
        apply_event(profile, "venue_complete", {"venue_id": "kitchen-table"}, today=TODAY)
        assert "riverboat" in profile.career.unlocked
        # gates still gate: basic-strategy not mastered yet
        assert not can_enter(VENUES["riverboat"], profile)

        for _ in range(40):
            apply_event(
                profile, "drill",
                {"drill_key": "strategy", "correct": True},
                today=TODAY,
            )
        assert can_enter(VENUES["riverboat"], profile)

    def test_next_venue_order(self):
        assert next_venue_id("kitchen-table") == "riverboat"
        assert next_venue_id("high-limit-room") is None
        assert next_venue_id("neon-mirage") is None  # traps advance nothing

    def test_gates_met_reporting(self):
        profile = new_profile()
        gates = gates_met(VENUES["downtown-grind"], profile)
        assert {g["node"] for g in gates} == {"deck-countdown", "speed-counting"}
        assert all(not g["met"] for g in gates)

    def test_trap_walkaway_badge(self):
        profile = new_profile()
        delta = apply_event(profile, "trap_walkaway", {}, today=TODAY)
        assert "walks-away" in delta.badges_awarded


class TestHeat:
    def test_no_heat_at_tolerant_venues(self):
        assert heat_events(25, 5, 5.0, 5, 25, heat_tolerance=0.0) == []

    def test_bet_jump_on_spike_generates_readable_heat(self):
        events = heat_events(80, 10, 3.5, 10, 500, heat_tolerance=6.0)
        assert any(e.delta > 0.2 for e in events)
        assert any("jumped" in e.reason for e in events)

    def test_flat_betting_cools(self):
        events = heat_events(25, 25, 2.0, 10, 500, heat_tolerance=6.0)
        assert events and events[0].delta < 0

    def test_apply_and_backoff(self):
        heat = 0.0
        for _ in range(4):
            events = heat_events(80, 10, 4.0, 10, 500, heat_tolerance=6.0)
            heat = apply_heat(heat, events)
        assert is_backed_off(heat)

    def test_heat_clamped(self):
        assert apply_heat(0.02, heat_events(25, 25, 0.0, 10, 500, 6.0)) == 0.0
