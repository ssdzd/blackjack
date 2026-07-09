"""The career ladder: real venues, real rules, real house edges.

Five mandatory rungs from a kitchen table to the high-limit room, each a
genuine rule set whose house edge comes from core.statistics — plus the
Neon Mirage, an optional 6:5 trap room where the winning move is reading
the rules and walking away.

Gates are skill-tree nodes (demonstrated ability). Bankroll targets are
survival, not skill: busting a venue attempt costs nothing but the retry.
"""

from dataclasses import dataclass
from decimal import Decimal

from core.statistics.house_edge import HouseEdgeCalculator
from core.strategy.rules import RuleSet


@dataclass(frozen=True)
class Venue:
    id: str
    order: int
    name: str
    flavor: str
    rules: RuleSet
    penetration: float
    buy_in: int
    target: int | None          # bankroll that clears the venue; None = unbeatable
    gates: tuple[str, ...] = () # skill-tree node ids required to enter
    heat_tolerance: float = 0.0 # max comfortable bet spread; 0 = no heat here
    trap: bool = False

    @property
    def house_edge_pct(self) -> float:
        return float(HouseEdgeCalculator(self.rules).calculate())

    def rules_summary(self) -> str:
        r = self.rules
        payout = "3:2" if r.blackjack_payout >= 1.5 else "6:5"
        parts = [
            f"{r.num_decks} deck{'s' if r.num_decks > 1 else ''}",
            "H17" if r.dealer_hits_soft_17 else "S17",
            payout,
        ]
        if r.double_after_split:
            parts.append("DAS")
        if r.surrender != "none":
            parts.append("LS" if r.surrender == "late" else "ES")
        if r.resplit_aces:
            parts.append("RSA")
        return " · ".join(parts)


VENUES: dict[str, Venue] = {
    venue.id: venue
    for venue in [
        Venue(
            id="kitchen-table",
            order=1,
            name="The Kitchen Table",
            flavor="Tuesday night, your cousin deals. Nobody counts. You will.",
            rules=RuleSet(
                num_decks=1,
                min_bet=5,
                max_bet=25,
                dealer_hits_soft_17=True,
                double_after_split=False,
                surrender="none",
            ),
            penetration=0.9,
            buy_in=200,
            target=300,
            gates=(),
            heat_tolerance=0.0,  # friends don't back you off
        ),
        Venue(
            id="riverboat",
            order=2,
            name="The Riverboat",
            flavor="Two decks, brass rails, a dealer who's seen it all.",
            rules=RuleSet(
                num_decks=2,
                min_bet=10,
                max_bet=200,
                dealer_hits_soft_17=True,
                double_after_split=True,
                surrender="none",
            ),
            penetration=0.7,
            buy_in=500,
            target=750,
            gates=("basic-strategy",),
            heat_tolerance=8.0,
        ),
        Venue(
            id="downtown-grind",
            order=3,
            name="The Downtown Grind",
            flavor="Six decks, stale smoke, pit bosses who count faster than you.",
            rules=RuleSet.downtown_vegas(),
            penetration=0.75,
            buy_in=1000,
            target=1500,
            gates=("deck-countdown", "speed-counting"),
            heat_tolerance=6.0,
        ),
        Venue(
            id="the-strip",
            order=4,
            name="The Strip",
            flavor="Cameras in the chandeliers. Play sharp, bet smart, stay boring.",
            rules=RuleSet(
                num_decks=6,
                min_bet=25,
                max_bet=1000,
                dealer_hits_soft_17=False,
                double_after_split=True,
                surrender="late",
            ),
            penetration=0.8,
            buy_in=2500,
            target=3750,
            gates=("true-count", "betting-kelly"),
            heat_tolerance=8.0,
        ),
        Venue(
            id="high-limit-room",
            order=5,
            name="The High-Limit Room",
            flavor="Velvet rope, deep penetration, real money. The graduation floor.",
            rules=RuleSet(
                num_decks=6,
                min_bet=100,
                max_bet=10000,
                dealer_hits_soft_17=False,
                double_after_split=True,
                resplit_aces=True,
                surrender="late",
            ),
            penetration=0.85,
            buy_in=10000,
            target=15000,
            gates=("illustrious-18", "fab-4"),
            heat_tolerance=10.0,
        ),
        Venue(
            id="neon-mirage",
            order=99,
            name="The Neon Mirage",
            flavor="Free drinks, loud carpet, blackjack pays 6:5. Do the math before you sit.",
            rules=RuleSet(
                num_decks=8,
                min_bet=10,
                max_bet=5000,
                dealer_hits_soft_17=True,
                blackjack_payout=1.2,
                double_after_split=True,
                surrender="none",
            ),
            penetration=0.5,
            buy_in=1000,
            target=None,  # you cannot beat this game; that's the lesson
            gates=(),
            heat_tolerance=0.0,
            trap=True,
        ),
    ]
}

VENUE_ORDER = [v.id for v in sorted(VENUES.values(), key=lambda v: v.order) if not v.trap]


def next_venue_id(venue_id: str) -> str | None:
    """The next mandatory rung after a venue, if any."""
    try:
        index = VENUE_ORDER.index(venue_id)
    except ValueError:
        return None
    if index + 1 < len(VENUE_ORDER):
        return VENUE_ORDER[index + 1]
    return None


def gates_met(venue: Venue, profile) -> list[dict]:
    """Evaluate a venue's gates against a profile's skill tree."""
    results = []
    for node_id in venue.gates:
        state = profile.nodes.get(node_id)
        results.append({
            "node": node_id,
            "met": bool(state and state.status == "mastered"),
        })
    return results


def can_enter(venue: Venue, profile) -> bool:
    if venue.trap:
        return True  # anyone can walk into a trap
    if venue.id not in profile.career.unlocked:
        return False
    return all(g["met"] for g in gates_met(venue, profile))
