"""The skill tree: the vision doc's 7-stage pedagogy as unlockable nodes.

Every gate is a demonstrated-skill gate — an accuracy threshold over a
rolling window of attempts, or a counter of hard achievements. Never XP.

Node progress is computed from the profile's drill windows and lifetime
counters; `recompute_tree` returns status changes so callers can announce
unlocks and masteries.
"""

from dataclasses import dataclass
from typing import Literal

MetricKind = Literal["accuracy", "counter"]


@dataclass(frozen=True)
class MasteryRule:
    """How a node is mastered."""

    metric: MetricKind
    # accuracy: fraction correct over the last `window` attempts
    # counter: a lifetime counter reaching `threshold`
    threshold: float
    window: int = 0            # accuracy only
    min_attempts: int = 0      # accuracy only
    counter_key: str = ""      # counter only

    def describe(self) -> str:
        if self.metric == "accuracy":
            pct = int(self.threshold * 100)
            return f"≥{pct}% over your last {self.window} (min {self.min_attempts})"
        return f"reach {int(self.threshold)} × {self.counter_key.replace('_', ' ')}"


@dataclass(frozen=True)
class SkillNode:
    """One node in the tree."""

    id: str
    stage: int
    name: str
    description: str
    drill_key: str             # which attempt window feeds progress
    mastery: MasteryRule
    prerequisites: tuple[str, ...] = ()
    unlocks: tuple[str, ...] = ()  # flavor copy for the UI (venues, systems)


SKILL_TREE: dict[str, SkillNode] = {
    node.id: node
    for node in [
        SkillNode(
            id="basic-strategy",
            stage=1,
            name="Basic Strategy",
            description="Every decision by the book. The chart is the floor, not the ceiling.",
            drill_key="strategy",
            mastery=MasteryRule("accuracy", 0.90, window=40, min_attempts=40),
            unlocks=("riverboat venue",),
        ),
        SkillNode(
            id="card-values",
            stage=2,
            name="Card Values",
            description="See a card, feel its tag. +1, 0, −1 without thinking.",
            drill_key="counting",
            mastery=MasteryRule("accuracy", 0.90, window=20, min_attempts=20),
            prerequisites=("basic-strategy",),
        ),
        SkillNode(
            id="deck-countdown",
            stage=3,
            name="Deck Countdown",
            description="A full deck, one pass, land on zero. The classic proof.",
            drill_key="speed",
            mastery=MasteryRule("counter", 3, counter_key="deck_countdown_pass"),
            prerequisites=("card-values",),
            unlocks=("downtown grind venue",),
        ),
        SkillNode(
            id="speed-counting",
            stage=4,
            name="Speed Counting",
            description="Casino dealers don't wait. Keep the count at table pace.",
            drill_key="speed",
            mastery=MasteryRule("accuracy", 0.85, window=20, min_attempts=20),
            prerequisites=("deck-countdown",),
        ),
        SkillNode(
            id="true-count",
            stage=5,
            name="True Count",
            description="Divide by decks remaining. The running count lies; the true count doesn't.",
            drill_key="tc-conversion",
            mastery=MasteryRule("accuracy", 0.90, window=30, min_attempts=30),
            prerequisites=("speed-counting",),
        ),
        SkillNode(
            id="betting-kelly",
            stage=6,
            name="Kelly Betting",
            description="Size bets to your edge. Too small leaves money; too big goes broke.",
            drill_key="bet",
            mastery=MasteryRule("counter", 20, counter_key="kelly_streak_best"),
            prerequisites=("true-count",),
            unlocks=("the strip venue",),
        ),
        SkillNode(
            id="illustrious-18",
            stage=7,
            name="Illustrious 18",
            description="The eighteen index plays worth more than all the rest combined.",
            drill_key="deviation",
            mastery=MasteryRule("accuracy", 0.90, window=50, min_attempts=50),
            prerequisites=("true-count",),
        ),
        SkillNode(
            id="fab-4",
            stage=7,
            name="Fab Four",
            description="The four surrender indices. Folding well is a skill.",
            drill_key="deviation",
            mastery=MasteryRule("counter", 12, counter_key="fab4_correct"),
            prerequisites=("illustrious-18",),
        ),
        SkillNode(
            id="multi-system",
            stage=8,
            name="Advanced Systems",
            description="Omega II and Wong Halves. More precision, more to carry.",
            drill_key="counting-adv",
            mastery=MasteryRule("accuracy", 0.80, window=30, min_attempts=30),
            prerequisites=("illustrious-18",),
        ),
        SkillNode(
            id="casino-ready",
            stage=9,
            name="Casino Ready",
            description="A full shoe, count hidden, zero strategy errors. The graduation exam.",
            drill_key="casino",
            mastery=MasteryRule("counter", 1, counter_key="casino_ready_shoes"),
            prerequisites=("betting-kelly", "illustrious-18", "fab-4"),
            unlocks=("high-limit room venue",),
        ),
    ]
}


def node_progress(node: SkillNode, windows: dict, counters: dict) -> tuple[float, int]:
    """Return (progress 0..1, attempts considered) for a node."""
    rule = node.mastery
    if rule.metric == "counter":
        have = counters.get(rule.counter_key, 0)
        return min(have / rule.threshold, 1.0), have

    attempts = windows.get(node.drill_key, [])
    recent = attempts[-rule.window:] if rule.window else attempts
    if not recent:
        return 0.0, 0
    accuracy = sum(1 for a in recent if a.correct) / len(recent)
    # Progress blends fill (enough attempts) and accuracy against threshold
    fill = min(len(recent) / max(rule.min_attempts, 1), 1.0)
    quality = min(accuracy / rule.threshold, 1.0)
    return fill * quality, len(recent)


def is_mastered(node: SkillNode, windows: dict, counters: dict) -> bool:
    rule = node.mastery
    if rule.metric == "counter":
        return counters.get(rule.counter_key, 0) >= rule.threshold

    attempts = windows.get(node.drill_key, [])
    recent = attempts[-rule.window:] if rule.window else attempts
    if len(recent) < rule.min_attempts:
        return False
    accuracy = sum(1 for a in recent if a.correct) / len(recent)
    return accuracy >= rule.threshold


def recompute_tree(profile) -> dict[str, str]:
    """Update every node's state on the profile.

    Returns {node_id: new_status} for nodes whose status changed.
    Mastery is sticky: once mastered, a cold streak can't demote you.
    """
    from core.progression.profile import NodeState  # local: avoid cycle

    changes: dict[str, str] = {}
    windows = profile.drill_windows
    counters = profile.lifetime

    for node_id, node in SKILL_TREE.items():
        state = profile.nodes.get(node_id) or NodeState()
        old_status = state.status

        prereqs_met = all(
            (profile.nodes.get(p) or NodeState()).status == "mastered"
            for p in node.prerequisites
        )

        if state.status != "mastered":
            if is_mastered(node, windows, counters) and prereqs_met:
                state.status = "mastered"
                state.progress = 1.0
            elif prereqs_met:
                progress, attempts = node_progress(node, windows, counters)
                state.status = "in_progress" if attempts > 0 else "available"
                state.progress = round(progress, 3)
                state.attempts = attempts
            else:
                state.status = "locked"
                progress, attempts = node_progress(node, windows, counters)
                state.progress = round(progress, 3)
                state.attempts = attempts

        profile.nodes[node_id] = state
        if state.status != old_status:
            changes[node_id] = state.status

    return changes
