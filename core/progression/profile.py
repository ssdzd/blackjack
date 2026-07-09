"""Player profile and the single progression entry point.

The API layer translates graded gameplay into events and calls
`apply_event(profile, event_type, payload, today=...)`. Everything else —
XP, streaks, windows, badges, skill-tree state — updates from that one
call, and the returned ProgressionDelta is what gets pushed to the client.

Event types and payloads:

- "decision":        {correct, is_deviation, visibility, fab4?}
- "insurance":       {correct, correct_action}
- "bet":             {in_band}
- "checkin":         {exact, close}
- "drill":           {drill_key, correct, num_cards?, time_ms?, system?}
- "round":           {result}
- "shoe_complete":   {checkins_exact, strategy_errors}
- "daily_complete":  {date, score, grade, decisions_pct, counts_pct, net}
- "venue_complete":  {venue_id, max_heat}
- "trap_walkaway":   {}
- "casino_shoe":     {clean}   (graduation-exam shoe)
"""

import time
from datetime import date, timedelta
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from core.progression.badges import evaluate_badges
from core.progression.skill_tree import recompute_tree
from core.progression.xp import XP_RULES, level_for_xp, title_for_level

WINDOW_CAP = 100


class AttemptRecord(BaseModel):
    ts: int
    correct: bool
    metric: float | None = None


class StreakState(BaseModel):
    current: int = 0
    best: int = 0
    last_active: str | None = None  # ISO date


class NodeState(BaseModel):
    status: Literal["locked", "available", "in_progress", "mastered"] = "locked"
    progress: float = 0.0
    attempts: int = 0


class CareerState(BaseModel):
    venue_id: str = "kitchen-table"
    unlocked: list[str] = Field(default_factory=lambda: ["kitchen-table"])
    completed: list[str] = Field(default_factory=list)
    venue_bankroll: str | None = None  # Decimal serialized as str
    hands_at_venue: int = 0
    heat: float = 0.0
    max_heat_this_attempt: float = 0.0
    backed_off_count: int = 0


class DailyRecord(BaseModel):
    date: str
    score: int
    grade: str
    decisions_pct: float
    counts_pct: float
    net: float


class ProfileSettings(BaseModel):
    counting_system: str = "hilo"
    visibility: str = "always"
    sound: bool = True
    rules_preset: str = "default"


class PlayerProfile(BaseModel):
    profile_id: str
    created_at: int
    xp: int = 0
    level: int = 1
    badges: dict[str, int] = Field(default_factory=dict)  # id -> awarded ts
    streak: StreakState = Field(default_factory=StreakState)
    drill_windows: dict[str, list[AttemptRecord]] = Field(default_factory=dict)
    lifetime: dict[str, int] = Field(default_factory=dict)
    nodes: dict[str, NodeState] = Field(default_factory=dict)
    career: CareerState = Field(default_factory=CareerState)
    daily: dict[str, DailyRecord] = Field(default_factory=dict)
    settings: ProfileSettings = Field(default_factory=ProfileSettings)

    @property
    def title(self) -> str:
        return title_for_level(self.level)


class ProgressionDelta(BaseModel):
    """What one event changed — pushed to the client for celebration."""

    xp_gained: int = 0
    xp_total: int = 0
    level: int = 1
    level_up: bool = False
    title: str = ""
    badges_awarded: list[str] = Field(default_factory=list)
    node_changes: dict[str, str] = Field(default_factory=dict)
    streak: int = 0


def new_profile(profile_id: str | None = None) -> PlayerProfile:
    profile = PlayerProfile(
        profile_id=profile_id or str(uuid4()),
        created_at=int(time.time()),
    )
    recompute_tree(profile)
    return profile


def _bump(profile: PlayerProfile, key: str, amount: int = 1) -> None:
    profile.lifetime[key] = profile.lifetime.get(key, 0) + amount


def _push_attempt(
    profile: PlayerProfile, key: str, correct: bool, metric: float | None = None
) -> None:
    window = profile.drill_windows.setdefault(key, [])
    window.append(AttemptRecord(ts=int(time.time()), correct=correct, metric=metric))
    if len(window) > WINDOW_CAP:
        del window[: len(window) - WINDOW_CAP]


def _touch_streak(profile: PlayerProfile, today: date) -> None:
    iso = today.isoformat()
    last = profile.streak.last_active
    if last == iso:
        return
    if last is not None and date.fromisoformat(last) == today - timedelta(days=1):
        profile.streak.current += 1
    else:
        profile.streak.current = 1
    profile.streak.best = max(profile.streak.best, profile.streak.current)
    profile.streak.last_active = iso


def apply_event(
    profile: PlayerProfile,
    event_type: str,
    payload: dict[str, Any] | None = None,
    today: date | None = None,
) -> ProgressionDelta:
    """Apply one progression event. Returns the delta for the client."""
    payload = payload or {}
    today = today or date.today()

    xp_gained = 0
    _touch_streak(profile, today)

    if event_type == "decision":
        _bump(profile, "decisions")
        if payload.get("correct"):
            _bump(profile, "decisions_correct")
            if payload.get("is_deviation"):
                _bump(profile, "deviations_correct")
                xp_gained += XP_RULES["deviation_correct"]
            elif payload.get("visibility") == "always":
                xp_gained += XP_RULES["correct_play"]
            else:
                xp_gained += XP_RULES["correct_play_hidden"]
            if payload.get("fab4"):
                _bump(profile, "fab4_correct")

    elif event_type == "insurance":
        _bump(profile, "insurance_decisions")
        if payload.get("correct"):
            _bump(profile, "insurance_correct")
            if payload.get("correct_action") == "take":
                xp_gained += XP_RULES["insurance_correct_take"]

    elif event_type == "bet":
        if payload.get("in_band"):
            _bump(profile, "kelly_streak")
            profile.lifetime["kelly_streak_best"] = max(
                profile.lifetime.get("kelly_streak_best", 0),
                profile.lifetime.get("kelly_streak", 0),
            )
            xp_gained += XP_RULES["kelly_bet_in_band"]
        else:
            profile.lifetime["kelly_streak"] = 0
        _push_attempt(profile, "bet", bool(payload.get("in_band")))

    elif event_type == "checkin":
        _bump(profile, "checkins")
        if payload.get("exact"):
            _bump(profile, "checkins_exact")
            xp_gained += XP_RULES["count_checkin_exact"]
        elif payload.get("close"):
            xp_gained += XP_RULES["count_checkin_close"]
        _push_attempt(profile, "checkin", bool(payload.get("exact") or payload.get("close")))

    elif event_type == "drill":
        drill_key = payload.get("drill_key", "counting")
        correct = bool(payload.get("correct"))
        _push_attempt(
            profile, drill_key, correct, metric=payload.get("time_ms")
        )
        _bump(profile, f"drill_{drill_key}")
        if correct:
            xp_gained += XP_RULES["drill_correct"]
            # A correct full-deck countdown at speed is its own milestone
            if (
                drill_key == "speed"
                and payload.get("num_cards", 0) >= 52
                and payload.get("time_ms")
            ):
                _bump(profile, "deck_countdown_pass")
                xp_gained += XP_RULES["deck_countdown_pass"]

    elif event_type == "round":
        _bump(profile, "hands")
        result = payload.get("result", 0)
        if result > 0:
            _bump(profile, "hands_won")
        # No XP for money. Ever.

    elif event_type == "shoe_complete":
        _bump(profile, "shoes_complete")

    elif event_type == "casino_shoe":
        if payload.get("clean"):
            _bump(profile, "casino_ready_shoes")

    elif event_type == "daily_complete":
        record = DailyRecord(
            date=payload.get("date", today.isoformat()),
            score=int(payload.get("score", 0)),
            grade=str(payload.get("grade", "-")),
            decisions_pct=float(payload.get("decisions_pct", 0)),
            counts_pct=float(payload.get("counts_pct", 0)),
            net=float(payload.get("net", 0)),
        )
        profile.daily[record.date] = record
        _bump(profile, "dailies_complete")
        xp_gained += XP_RULES["daily_complete"]

    elif event_type == "venue_complete":
        venue_id = payload.get("venue_id")
        if venue_id and venue_id not in profile.career.completed:
            profile.career.completed.append(venue_id)

    # Badges evaluate against the post-event profile
    badges = evaluate_badges(profile, event_type, payload)
    for badge_id in badges:
        profile.badges[badge_id] = int(time.time())
        xp_gained += XP_RULES["badge_awarded"]

    # Skill tree reacts to windows/counters
    node_changes = recompute_tree(profile)
    for node_id, status in node_changes.items():
        if status == "mastered":
            xp_gained += XP_RULES["node_mastered"]

    old_level = profile.level
    profile.xp += xp_gained
    profile.level = level_for_xp(profile.xp)

    return ProgressionDelta(
        xp_gained=xp_gained,
        xp_total=profile.xp,
        level=profile.level,
        level_up=profile.level > old_level,
        title=profile.title,
        badges_awarded=badges,
        node_changes=node_changes,
        streak=profile.streak.current,
    )
