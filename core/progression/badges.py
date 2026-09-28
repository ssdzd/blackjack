"""Skill-based badges.

Per the vision doc: badges certify demonstrated ability ("20-Second Deck
Master", "Perfect Shoe") — never attendance. Money won is never a badge.
"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class BadgeDef:
    id: str
    name: str
    flavor: str
    category: str  # "counting" | "strategy" | "betting" | "discipline" | "career"
    secret: bool = False


BADGES: dict[str, BadgeDef] = {
    badge.id: badge
    for badge in [
        BadgeDef(
            "perfect-shoe",
            "Perfect Shoe",
            "A full shoe with every count check-in exact and zero strategy errors.",
            "counting",
        ),
        BadgeDef(
            "twenty-second-deck",
            "20-Second Deck",
            "Count down a full 52-card deck, correctly, in 20 seconds or less.",
            "counting",
        ),
        BadgeDef(
            "index-play-expert",
            "Index Play Expert",
            "95% on Illustrious 18 situations over your last 50.",
            "strategy",
        ),
        BadgeDef(
            "fab-four",
            "Fab Four",
            "Master all four surrender indices.",
            "strategy",
        ),
        BadgeDef(
            "kellys-disciple",
            "Kelly's Disciple",
            "Twenty consecutive bets sized inside the Kelly band.",
            "betting",
        ),
        BadgeDef(
            "iron-streak-7",
            "Iron Streak",
            "Practice seven days in a row.",
            "discipline",
        ),
        BadgeDef(
            "iron-streak-30",
            "Iron Will",
            "Practice thirty days in a row.",
            "discipline",
        ),
        BadgeDef(
            "casino-ready",
            "Casino Ready",
            "Pass the graduation exam: a clean full shoe with the count hidden.",
            "career",
        ),
        BadgeDef(
            "daily-perfect",
            "Daily Perfect",
            "A daily challenge with every decision and every check-in correct.",
            "strategy",
        ),
        BadgeDef(
            "walks-away",
            "Reads the Fine Print",
            "Check the house edge at the Neon Mirage — and walk away.",
            "career",
            secret=True,
        ),
        BadgeDef(
            "heat-proof",
            "Heat Proof",
            "Clear a venue's bankroll target without ever passing 50% heat.",
            "career",
            secret=True,
        ),
    ]
}


def _window_accuracy(profile: Any, key: str, window: int) -> tuple[float, int]:
    attempts = profile.drill_windows.get(key, [])
    recent = attempts[-window:]
    if not recent:
        return 0.0, 0
    return sum(1 for a in recent if a.correct) / len(recent), len(recent)


def _accuracy_gate(profile: Any, key: str, window: int, threshold: float) -> bool:
    """True when the window is full AND accuracy meets the threshold."""
    accuracy, count = _window_accuracy(profile, key, window)
    return count >= window and accuracy >= threshold


# Predicates receive (profile, event_type, payload) AFTER the event has been
# applied to the profile, and say whether the badge is earned now.
PREDICATES: dict[str, Callable[[Any, str, dict], bool]] = {
    "perfect-shoe": lambda p, t, d: (
        t == "shoe_complete"
        and d.get("checkins_exact", False)
        and d.get("strategy_errors", 1) == 0
    ),
    "twenty-second-deck": lambda p, t, d: (
        t == "drill"
        and d.get("drill_key") == "speed"
        and d.get("correct", False)
        and d.get("num_cards", 0) >= 52
        and 0 < d.get("time_ms", 10 ** 9) <= 20_000
    ),
    "index-play-expert": lambda p, t, d: (
        t == "drill"
        and d.get("drill_key") == "deviation"
        and _accuracy_gate(p, "deviation", 50, 0.95)
    ),
    "fab-four": lambda p, t, d: p.lifetime.get("fab4_correct", 0) >= 12,
    "kellys-disciple": lambda p, t, d: p.lifetime.get("kelly_streak_best", 0) >= 20,
    "iron-streak-7": lambda p, t, d: p.streak.current >= 7,
    "iron-streak-30": lambda p, t, d: p.streak.current >= 30,
    "casino-ready": lambda p, t, d: p.lifetime.get("casino_ready_shoes", 0) >= 1,
    "daily-perfect": lambda p, t, d: (
        t == "daily_complete"
        and d.get("decisions_pct", 0) >= 100
        and d.get("counts_pct", 0) >= 100
    ),
    "walks-away": lambda p, t, d: t == "trap_walkaway",
    "heat-proof": lambda p, t, d: (
        t == "venue_complete" and d.get("max_heat", 1.0) <= 0.5
    ),
}


def evaluate_badges(profile: Any, event_type: str, payload: dict) -> list[str]:
    """Return newly-earned badge ids for an already-applied event."""
    earned: list[str] = []
    for badge_id, predicate in PREDICATES.items():
        if badge_id in profile.badges:
            continue
        try:
            if predicate(profile, event_type, payload):
                earned.append(badge_id)
        except Exception:
            continue  # a bad predicate must never poison progression
    return earned
