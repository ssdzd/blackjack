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
from core.progression.skill_tree import SKILL_TREE, MasteryRule, SkillNode, recompute_tree
from core.progression.xp import (
    LEVEL_TITLES,
    XP_RULES,
    level_for_xp,
    title_for_level,
    xp_to_reach_level,
)

__all__ = [
    "AttemptRecord",
    "BADGES",
    "BadgeDef",
    "CareerState",
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
