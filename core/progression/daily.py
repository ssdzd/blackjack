"""The daily challenge: one seeded shoe, same cards for everyone.

Twenty heads-up rounds on Vegas Strip rules with the count hidden and
three count check-ins. The seed derives from the date, so every player
faces the identical card sequence — skill is the only variable. Scoring
is deliberately anti-luck: decisions 60%, count accuracy 30%, and only a
sign-bucketed 10% for the money.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import date

from core.strategy.rules import RuleSet

EPOCH = date(2026, 7, 1)  # Daily #1


@dataclass(frozen=True)
class DailyChallenge:
    date: str            # ISO date
    number: int          # Daily #N
    seed: int
    rounds: int = 20
    checkin_rounds: tuple[int, ...] = (7, 14, 20)
    min_bet: int = 10
    max_bet: int = 100
    bankroll: int = 1000

    @property
    def rules(self) -> RuleSet:
        return RuleSet.vegas_strip()


def challenge_for_date(day: date) -> DailyChallenge:
    iso = day.isoformat()
    digest = hashlib.sha256(f"bjt-daily-{iso}".encode()).digest()
    seed = int.from_bytes(digest[:8], "big")
    number = (day - EPOCH).days + 1
    return DailyChallenge(date=iso, number=number, seed=seed)


# ---- Scoring ----

GRADE_BANDS = [(950, "S"), (850, "A"), (700, "B"), (550, "C"), (400, "D")]


@dataclass
class DailyScore:
    score: int
    grade: str
    decisions_pct: float
    counts_pct: float
    net: float
    breakdown: dict = field(default_factory=dict)


def score_daily(
    decisions: list[bool],
    checkins: list[bool],
    net: float,
) -> DailyScore:
    """Composite 0-1000 score, weighted skill-heavy."""
    decisions_pct = (
        100.0 * sum(decisions) / len(decisions) if decisions else 0.0
    )
    counts_pct = 100.0 * sum(checkins) / len(checkins) if checkins else 0.0

    if net > 0:
        money = 1.0
    elif net == 0:
        money = 0.5
    else:
        money = 0.0

    score = round(
        600 * (decisions_pct / 100)
        + 300 * (counts_pct / 100)
        + 100 * money
    )

    grade = "F"
    for threshold, letter in GRADE_BANDS:
        if score >= threshold:
            grade = letter
            break

    return DailyScore(
        score=score,
        grade=grade,
        decisions_pct=round(decisions_pct, 1),
        counts_pct=round(counts_pct, 1),
        net=net,
        breakdown={
            "decisions": round(600 * decisions_pct / 100),
            "counts": round(300 * counts_pct / 100),
            "bankroll": round(100 * money),
        },
    )


# ---- Sharing ----

def emoji_grid(round_results: list[str]) -> str:
    """Rows of 5 squares; one square per round.

    round_results entries: "perfect" | "mixed" | "wrong" | "none"
    """
    symbols = {"perfect": "🟩", "mixed": "🟨", "wrong": "🟥", "none": "⬜"}
    cells = [symbols.get(r, "⬜") for r in round_results]
    rows = ["".join(cells[i:i + 5]) for i in range(0, len(cells), 5)]
    return "\n".join(rows)


def share_payload(
    challenge: DailyChallenge,
    score: DailyScore,
    round_results: list[str],
) -> dict:
    grid = emoji_grid(round_results)
    text = (
        f"Blackjack Noir Daily #{challenge.number} — {score.score}/1000 ({score.grade})\n"
        f"Decisions {score.decisions_pct:.0f}% · Counts {score.counts_pct:.0f}%"
        f" · {'+' if score.net > 0 else ''}{score.net:.0f} units\n"
        f"{grid}"
    )
    return {"share_text": text, "emoji_grid": grid}
