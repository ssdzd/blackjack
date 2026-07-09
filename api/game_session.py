"""Server-authoritative training session around the core game engine.

Wraps a BlackjackGame with:

- an attached counting system fed from engine events, counting exactly the
  cards a player at the table could see (face-up deals, the hole card at
  reveal — including resolution paths that never emit DEALER_REVEALS,
  which the old client-side counter silently missed);
- decision grading against BasicStrategy plus Illustrious 18 / Fab 4
  index plays (balanced systems only);
- bet grading against a Kelly band;
- a quant snapshot (edge, Kelly stake, risk of ruin, N0, dealer bust
  probability) computed by core.statistics;
- the WebSocket state payload, versioned `v: 2`, with count visibility
  modes (always / on_request / hidden).

Everything here is plain Python and unit-testable without a WebSocket.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from random import Random
from typing import Any

from core.cards import Card
from core.counting import HiLoSystem, KOSystem, Omega2System, WongHalvesSystem
from core.game import BlackjackGame
from core.game.events import EventType, GameEvent
from core.statistics.bankroll import BankrollManager
from core.statistics.house_edge import HouseEdgeCalculator
from core.statistics.kelly import KellyCalculator
from core.statistics.probability import ProbabilityEngine
from core.strategy.basic import Action, BasicStrategy
from core.strategy.deviations import find_deviation
from core.strategy.rules import RuleSet

COUNTING_SYSTEMS = {
    "hilo": HiLoSystem,
    "ko": KOSystem,
    "omega2": Omega2System,
    "wong_halves": WongHalvesSystem,
}

RULE_PRESETS = {
    "vegas_strip": RuleSet.vegas_strip,
    "downtown_vegas": RuleSet.downtown_vegas,
    "single_deck": RuleSet.single_deck,
    "atlantic_city": RuleSet.atlantic_city,
    "default": RuleSet,
}

VISIBILITY_MODES = ("always", "on_request", "hidden")

_ACTION_NAMES = {
    Action.HIT: "hit",
    Action.STAND: "stand",
    Action.DOUBLE: "double",
    Action.SPLIT: "split",
    Action.SURRENDER: "surrender",
}


@dataclass
class DailyRun:
    """Live state of a daily-challenge attempt riding on a session."""

    challenge: Any  # core.progression.daily.DailyChallenge
    decisions: list[bool] = field(default_factory=list)
    current_round: list[bool] = field(default_factory=list)
    round_results: list[str] = field(default_factory=list)
    checkins: list[bool] = field(default_factory=list)
    rounds_played: int = 0
    awaiting_checkin: bool = False
    done: bool = False

    def record_decision(self, correct: bool) -> None:
        self.decisions.append(correct)
        self.current_round.append(correct)

    def close_round(self) -> None:
        """Categorize the finished round for the emoji grid."""
        if not self.current_round:
            self.round_results.append("none")
        elif all(self.current_round):
            self.round_results.append("perfect")
        elif any(self.current_round):
            self.round_results.append("mixed")
        else:
            self.round_results.append("wrong")
        self.current_round = []
        self.rounds_played += 1

    @property
    def rounds_finished(self) -> bool:
        return self.rounds_played >= self.challenge.rounds


@dataclass
class DecisionGrade:
    """Result of grading one player decision."""

    kind: str  # "action" | "insurance" | "bet"
    action: str
    correct_action: str
    is_correct: bool
    true_count: float | None
    is_deviation: bool = False
    deviation: dict[str, Any] | None = None
    why: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "action": self.action,
            "correct_action": self.correct_action,
            "is_correct": self.is_correct,
            "true_count": self.true_count,
            "is_deviation": self.is_deviation,
            "deviation": self.deviation,
            "why": self.why,
        }


class TrainingGameSession:
    """A BlackjackGame plus everything the trainer knows about it."""

    def __init__(
        self,
        rules: RuleSet | None = None,
        initial_bankroll: Decimal = Decimal("1000"),
        counting_system: str = "hilo",
        visibility: str = "always",
        penetration: float = 0.75,
        rng: Random | None = None,
    ) -> None:
        self.rules = rules or RuleSet()
        self.visibility = visibility if visibility in VISIBILITY_MODES else "always"
        self.counting_system_name = (
            counting_system if counting_system in COUNTING_SYSTEMS else "hilo"
        )

        self.game = BlackjackGame(
            rules=self.rules,
            num_decks=self.rules.num_decks,  # engine's shoe sizes off this arg
            penetration=penetration,
            initial_bankroll=initial_bankroll,
        )
        if rng is not None:
            # Reproducible shoes (daily challenge): rebuild with seeded rng
            self.game = BlackjackGame(
                rules=self.rules,
                num_decks=self.rules.num_decks,
                penetration=penetration,
                initial_bankroll=initial_bankroll,
                rng=rng,
            )

        self.counter = COUNTING_SYSTEMS[self.counting_system_name]()
        self._reset_counter_for_shoe()

        self.strategy = BasicStrategy(self.rules)
        self.edge_calc = HouseEdgeCalculator(self.rules)
        self.base_house_edge = self.edge_calc.calculate()  # Decimal, percent
        self.probability = ProbabilityEngine(self.rules)

        self._hole_counted = False
        self.last_round_result: dict[str, Any] | None = None
        self.profile_id: str | None = None
        self.daily_run: "DailyRun | None" = None

        self.game.subscribe(self._on_event)

    # ---- Counting ----

    def set_counting_system(self, name: str) -> None:
        """Switch counting systems (resets the count — mid-shoe swaps lie)."""
        if name not in COUNTING_SYSTEMS or name == self.counting_system_name:
            return
        self.counting_system_name = name
        self.counter = COUNTING_SYSTEMS[name]()
        self._reset_counter_for_shoe()

    def _reset_counter_for_shoe(self) -> None:
        if hasattr(self.counter, "reset_for_shoe"):
            self.counter.reset_for_shoe(self.rules.num_decks)
        else:
            self.counter.reset()

    def _count_card_string(self, card_str: str) -> None:
        try:
            self.counter.count_card(Card.from_string(card_str))
        except ValueError:
            pass  # never let a malformed event string kill the session

    def _on_event(self, event: GameEvent) -> None:
        etype = event.event_type

        if etype == EventType.SHOE_SHUFFLED:
            self._reset_counter_for_shoe()

        elif etype == EventType.ROUND_STARTED:
            self._hole_counted = False

        elif etype == EventType.CARD_DEALT:
            card = event.data.get("card")
            if card and card != "??":
                self._count_card_string(card)

        elif etype == EventType.DEALER_REVEALS:
            card = event.data.get("card")
            if card:
                self._count_card_string(card)
                self._hole_counted = True

        elif etype == EventType.ROUND_ENDED:
            # Resolution paths without a DEALER_REVEALS event (dealer
            # blackjack, every hand busted/surrendered) still expose the
            # hole card in the final state — count it exactly once.
            dealer_cards = self.game.dealer_hand.cards
            if not self._hole_counted and len(dealer_cards) >= 2:
                self.counter.count_card(dealer_cards[1])
                self._hole_counted = True
            self.last_round_result = {
                "result": event.data.get("result", 0),
                "bankroll": event.data.get("bankroll", 0),
                "player_blackjack": any(
                    h.is_blackjack for h in self.game.player.hands
                ),
                "wager": sum(int(h.bet) for h in self.game.player.hands),
            }

    @property
    def decks_remaining(self) -> float:
        return self.game.shoe.decks_remaining

    @property
    def running_count(self) -> float:
        return self.counter.running_count

    @property
    def true_count(self) -> float | None:
        """True count for balanced systems; None for unbalanced (KO)."""
        if not self.counter.is_balanced:
            return None
        return self.counter.true_count(self.decks_remaining)

    def _tc_for_grading(self) -> float:
        """TC used in deviation/bet grading; unbalanced systems grade at 0."""
        tc = self.true_count
        return tc if tc is not None else 0.0

    # ---- Grading ----

    def grade_action(self, action: str) -> DecisionGrade | None:
        """Grade a player action against strategy. Call BEFORE executing."""
        if self.game.state.name != "PLAYER_TURN":
            return None
        hand = self.game.player.current_hand
        if hand is None or not self.game.dealer_hand.cards:
            return None

        upcard = self.game.dealer_hand.cards[0].value
        is_pair = hand.is_pair
        pair_rank = hand.cards[0].value if is_pair else None
        tc = self._tc_for_grading()

        basic = self.strategy.get_action(
            player_total=hand.value,
            dealer_upcard=upcard,
            is_soft=hand.is_soft,
            is_pair=is_pair,
            pair_rank=pair_rank,
            can_double=self.game.can_double,
            can_surrender=self.game.can_surrender,
            can_split=self.game.can_split,
        )

        deviation = None
        if self.counter.is_balanced:
            deviation = find_deviation(
                player_total=hand.value,
                is_soft=hand.is_soft,
                is_pair=is_pair,
                dealer_upcard=upcard,
                true_count=tc,
                include_surrender=self.rules.surrender != "none",
            )
            # A deviation the current hand can't act on falls back to basic
            if deviation is not None:
                dev_action = deviation.deviation_action
                if dev_action == Action.DOUBLE and not self.game.can_double:
                    deviation = None
                elif dev_action == Action.SURRENDER and not self.game.can_surrender:
                    deviation = None

        correct = deviation.deviation_action if deviation else basic
        correct_name = _ACTION_NAMES.get(correct, correct.name.lower())

        why: dict[str, Any] = {
            "dealer_bust_pct": round(
                self.probability.dealer_bust_probability(upcard) * 100, 1
            ),
            "hand": f"{'Soft ' if hand.is_soft else ''}{hand.value} vs {upcard}",
        }
        if deviation:
            why["deviation_note"] = deviation.description
        elif self.counter.is_balanced:
            near = find_deviation(
                player_total=hand.value,
                is_soft=hand.is_soft,
                is_pair=is_pair,
                dealer_upcard=upcard,
                true_count=tc,
                include_surrender=False,
            )
            if near is None:
                why["strategy_note"] = "Basic strategy"

        return DecisionGrade(
            kind="action",
            action=action,
            correct_action=correct_name,
            is_correct=action == correct_name,
            true_count=round(tc, 2) if self.counter.is_balanced else None,
            is_deviation=deviation is not None,
            deviation=(
                {
                    "description": deviation.description,
                    "index": deviation.index,
                    "direction": deviation.direction,
                    "basic_action": _ACTION_NAMES.get(
                        deviation.basic_action, str(deviation.basic_action)
                    ),
                    "deviation_action": _ACTION_NAMES.get(
                        deviation.deviation_action, str(deviation.deviation_action)
                    ),
                }
                if deviation
                else None
            ),
            why=why,
        )

    def grade_insurance(self, take: bool) -> DecisionGrade:
        """Insurance is the #1 index play: take at TC >= +3 (balanced)."""
        tc = self._tc_for_grading()
        correct_take = self.counter.is_balanced and tc >= 3.0
        action = "take" if take else "decline"
        correct = "take" if correct_take else "decline"
        return DecisionGrade(
            kind="insurance",
            action=action,
            correct_action=correct,
            is_correct=action == correct,
            true_count=round(tc, 2) if self.counter.is_balanced else None,
            is_deviation=correct_take,
            why={
                "note": (
                    "Insurance pays 2:1 but the dealer has blackjack less than "
                    "1 in 3 unless the deck is rich in tens. Take it only at "
                    "TC +3 or better."
                )
            },
        )

    def grade_bet(self, amount: int) -> DecisionGrade:
        """Grade bet sizing against a half-Kelly band for the current count."""
        tc = self._tc_for_grading()
        edge_pct = self.edge_calc.player_advantage_with_count(
            tc, self.base_house_edge
        )  # Decimal percent
        edge = edge_pct / Decimal("100")

        kelly = KellyCalculator(
            bankroll=self.game.player.bankroll,
            min_bet=Decimal(self.rules.min_bet),
            max_bet=Decimal(self.rules.max_bet),
            kelly_fraction=0.5,
        )
        optimal = kelly.optimal_bet(edge)
        if edge <= 0:
            optimal = Decimal(self.rules.min_bet)

        low = max(Decimal(self.rules.min_bet), optimal * Decimal("0.5"))
        high = min(Decimal(self.rules.max_bet), max(optimal * Decimal("2"), low))
        in_band = low <= Decimal(amount) <= high

        return DecisionGrade(
            kind="bet",
            action=str(amount),
            correct_action=str(int(optimal)),
            is_correct=in_band,
            true_count=round(tc, 2) if self.counter.is_balanced else None,
            why={
                "edge_pct": float(edge_pct),
                "band": [int(low), int(high)],
                "note": "Half-Kelly stake for the current edge",
            },
        )

    def grade_count_checkin(self, running_count: float) -> dict[str, Any]:
        """Grade a count check-in answer."""
        actual = self.running_count
        diff = abs(running_count - actual)
        return {
            "correct": diff < 0.001,
            "close": diff <= 1.0,
            "actual": actual,
            "answer": running_count,
            "difference": running_count - actual,
        }

    # ---- Quant snapshot ----

    def quant_snapshot(self) -> dict[str, Any]:
        tc = self._tc_for_grading()
        edge_pct = self.edge_calc.player_advantage_with_count(
            tc, self.base_house_edge
        )
        edge_float = float(edge_pct) / 100.0

        kelly = KellyCalculator(
            bankroll=self.game.player.bankroll,
            min_bet=Decimal(self.rules.min_bet),
            max_bet=Decimal(self.rules.max_bet),
            kelly_fraction=0.5,
        )
        kelly_bet = kelly.optimal_bet(edge_pct / Decimal("100"))
        if edge_pct <= 0:
            kelly_bet = Decimal(self.rules.min_bet)

        manager = BankrollManager(
            bankroll=self.game.player.bankroll,
            min_bet=Decimal(self.rules.min_bet),
            max_bet=Decimal(self.rules.max_bet),
            player_edge=max(edge_float, -0.05),
        )
        ror = manager.risk_of_ruin()

        upcard = None
        dealer_bust_pct = None
        if self.game.dealer_hand.cards:
            upcard = self.game.dealer_hand.cards[0].value
            dealer_bust_pct = round(
                self.probability.dealer_bust_probability(upcard) * 100, 1
            )

        return {
            "house_edge_pct": float(self.base_house_edge),
            "player_edge_pct": float(edge_pct),
            "kelly_bet": int(kelly_bet),
            "risk_of_ruin_pct": round(min(ror.probability, 1.0) * 100, 2),
            "n_zero": int(ror.n_zero_point) if ror.n_zero_point else None,
            "dealer_upcard": upcard,
            "dealer_bust_pct": dealer_bust_pct,
        }

    # ---- State payload ----

    def count_payload(self) -> dict[str, Any]:
        return {
            "system": self.counting_system_name,
            "balanced": self.counter.is_balanced,
            "running": self.counter.running_count,
            "true": (
                round(self.true_count, 2) if self.true_count is not None else None
            ),
            "cards_seen": self.counter.cards_seen,
            "decks_remaining": round(self.decks_remaining, 2),
        }

    def state_payload(
        self,
        hide_hole_card: bool | None = None,
        include_count: bool | None = None,
    ) -> dict[str, Any]:
        game = self.game
        if hide_hole_card is None:
            hide_hole_card = game.state.name in ("PLAYER_TURN", "OFFERING_INSURANCE")

        dealer_cards = []
        for i, card in enumerate(game.dealer_hand.cards):
            if hide_hole_card and i == 1:
                dealer_cards.append(
                    {"rank": "?", "suit": "?", "value": 0, "hidden": True}
                )
            else:
                dealer_cards.append(
                    {
                        "rank": str(card.rank),
                        "suit": str(card.suit),
                        "value": card.value,
                        "hidden": False,
                    }
                )

        player_hands = []
        for hand in game.player.hands:
            player_hands.append(
                {
                    "cards": [
                        {"rank": str(c.rank), "suit": str(c.suit), "value": c.value}
                        for c in hand.cards
                    ],
                    "value": hand.value,
                    "is_soft": hand.is_soft,
                    "is_blackjack": hand.is_blackjack,
                    "is_busted": hand.is_busted,
                    "bet": hand.bet,
                }
            )

        dealer_showing = None
        if game.dealer_hand.cards and not hide_hole_card:
            dealer_showing = game.dealer_hand.value
        elif game.dealer_hand.cards:
            dealer_showing = game.dealer_hand.cards[0].value

        if include_count is None:
            include_count = self.visibility == "always"

        payload: dict[str, Any] = {
            "v": 2,
            "state": game.state.name,
            "player_hands": player_hands,
            "current_hand_index": game.player.current_hand_index,
            "dealer_hand": {
                "cards": dealer_cards,
                "value": dealer_showing if not hide_hole_card else None,
            },
            "dealer_showing": dealer_showing,
            "bankroll": float(game.player.bankroll),
            "can_hit": game.can_hit,
            "can_stand": game.can_stand,
            "can_double": game.can_double,
            "can_split": game.can_split,
            "can_surrender": game.can_surrender,
            "can_insure": game.can_insure,
            "insurance_bet": float(game.player.insurance_bet),
            "shoe_cards_remaining": game.shoe.cards_remaining,
            "shoe_decks_remaining": round(game.shoe.cards_remaining / 52, 2),
            "visibility": self.visibility,
            "rules": {
                "num_decks": self.rules.num_decks,
                "min_bet": self.rules.min_bet,
                "max_bet": self.rules.max_bet,
                "dealer_hits_soft_17": self.rules.dealer_hits_soft_17,
                "blackjack_payout": self.rules.blackjack_payout,
                "double_after_split": self.rules.double_after_split,
                "surrender": self.rules.surrender,
                "house_edge_pct": float(self.base_house_edge),
            },
        }

        if include_count:
            payload["count"] = self.count_payload()
            payload["quant"] = self.quant_snapshot()

        return payload
