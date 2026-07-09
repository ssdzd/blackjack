"""Mastery-weighted XP and levels.

XP rewards demonstrated skill, never outcomes: a perfectly-played losing
hand earns XP; a badly-played winning hand earns nothing. Per-hand play XP
only accrues while the count HUD is not permanently visible (playing from
memory is the skill being rewarded).

Levels are pacing/flavor only — no gameplay gate ever checks XP.
"""

# XP awarded per graded event kind
XP_RULES: dict[str, int] = {
    # Table play (only when count visibility != "always")
    "correct_play": 1,
    "correct_play_hidden": 2,
    # Index plays are the money skill
    "deviation_correct": 10,
    "insurance_correct_take": 10,
    # Count check-ins prove the count is real
    "count_checkin_exact": 15,
    "count_checkin_close": 5,
    # Drills
    "drill_correct": 5,
    "deck_countdown_pass": 20,
    # Milestones
    "node_mastered": 100,
    "daily_complete": 50,
    "badge_awarded": 25,
    "kelly_bet_in_band": 1,
}


def xp_to_reach_level(level: int) -> int:
    """Total XP required to reach a level (level 1 = start = 0 XP)."""
    if level <= 1:
        return 0
    return int(100 * (level - 1) ** 1.6)


def level_for_xp(xp: int) -> int:
    """The level a given XP total corresponds to."""
    level = 1
    while xp >= xp_to_reach_level(level + 1):
        level += 1
        if level >= 99:
            break
    return level


# Flavor titles by minimum level (checked from highest down)
LEVEL_TITLES: list[tuple[int, str]] = [
    (1, "Tourist"),
    (2, "Rookie"),
    (4, "Grinder"),
    (6, "Regular"),
    (9, "Card Sharp"),
    (12, "Mechanic"),
    (16, "Advantage Player"),
    (21, "Counter"),
    (27, "Pro"),
    (34, "High Roller"),
    (42, "Legend of the Strip"),
]


def title_for_level(level: int) -> str:
    """Flavor title for a level."""
    title = LEVEL_TITLES[0][1]
    for min_level, name in LEVEL_TITLES:
        if level >= min_level:
            title = name
    return title
