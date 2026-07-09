"""Progression: profiles, XP, badges, skill tree, career, daily challenge.

Pure Python, UI-agnostic. The API layer feeds graded events in; progression
hands structured deltas back. Design rules (from the project vision doc):

- Badges are skill-based, never participation trophies.
- XP rewards decisions and demonstrated skill, never money won.
- Levels pace flavor and cosmetics; every functional gate is an
  accuracy-window gate, never an XP gate.
"""

from core.progression.badges import BADGES, BadgeDef, evaluate_badges
from core.progression.profile import (
    AttemptRecord,
    CareerState,
    NodeState,
    PlayerProfile,
    ProfileSettings,
    ProgressionDelta,
    StreakState,
    apply_event,
    new_profile,
)
from core.progression.heat import (
    BACKOFF_THRESHOLD,
    HeatEvent,
    apply_heat,
    heat_events,
    is_backed_off,
)
from core.progression.skill_tree import SKILL_TREE, MasteryRule, SkillNode, recompute_tree
from core.progression.venues import VENUES, Venue, can_enter, gates_met, next_venue_id
from core.progression.xp import (
    LEVEL_TITLES,
    XP_RULES,
    level_for_xp,
    title_for_level,
    xp_to_reach_level,
)

__all__ = [
    "AttemptRecord",
    "BACKOFF_THRESHOLD",
    "BADGES",
    "BadgeDef",
    "CareerState",
    "HeatEvent",
    "VENUES",
    "Venue",
    "apply_heat",
    "can_enter",
    "gates_met",
    "heat_events",
    "is_backed_off",
    "next_venue_id",
    "LEVEL_TITLES",
    "MasteryRule",
    "NodeState",
    "PlayerProfile",
    "ProfileSettings",
    "ProgressionDelta",
    "SKILL_TREE",
    "SkillNode",
    "StreakState",
    "XP_RULES",
    "apply_event",
    "evaluate_badges",
    "level_for_xp",
    "new_profile",
    "recompute_tree",
    "title_for_level",
    "xp_to_reach_level",
]
