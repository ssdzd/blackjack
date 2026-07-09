"""Legible heat: why counters get backed off, one readable reason at a time.

Instead of an opaque statistical correlation, heat accrues from explicit,
explainable events — exactly the tells a real pit boss watches for. Every
gain carries a human-readable reason so getting backed off teaches cover
betting instead of breeding superstition.
"""

from dataclasses import dataclass

BACKOFF_THRESHOLD = 1.0


@dataclass(frozen=True)
class HeatEvent:
    delta: float
    reason: str


def heat_events(
    bet: int,
    prev_bet: int | None,
    true_count: float,
    min_bet: int,
    max_bet: int,
    heat_tolerance: float,
) -> list[HeatEvent]:
    """Heat generated (or shed) by one bet, given the table context."""
    if heat_tolerance <= 0:
        return []  # this venue doesn't watch

    events: list[HeatEvent] = []

    # The classic tell: ramping hard the moment the count spikes
    if prev_bet and bet >= prev_bet * 4 and true_count >= 3:
        events.append(HeatEvent(
            0.28,
            f"You jumped ${prev_bet} → ${bet} right as the count spiked. "
            "The pit notices bet jumps that track the shoe.",
        ))
    elif prev_bet and bet >= prev_bet * 3 and true_count >= 2:
        events.append(HeatEvent(
            0.16,
            f"${prev_bet} → ${bet} on a rising count. Smooth it out.",
        ))

    # Table max with a hot shoe draws the camera
    if bet >= max_bet and true_count >= 3:
        events.append(HeatEvent(
            0.18,
            "Table max with the shoe this rich reads as a counter cashing in.",
        ))

    # A wide spread is a fingerprint even without a single big jump
    if prev_bet and min_bet > 0:
        spread = bet / min_bet
        if spread > heat_tolerance:
            events.append(HeatEvent(
                0.12,
                f"Your spread hit 1-to-{spread:.0f}; this room tolerates about "
                f"1-to-{heat_tolerance:.0f}.",
            ))

    # Cover behavior cools things down
    if not events:
        if prev_bet is not None and bet == prev_bet:
            events.append(HeatEvent(-0.05, "Flat betting looks like a tourist."))
        elif bet <= min_bet * 2 and true_count < 1:
            events.append(HeatEvent(-0.04, "Small bets in a cold shoe blend in."))

    return events


def apply_heat(current: float, events: list[HeatEvent]) -> float:
    """Fold events into a heat level, clamped to [0, 1.2]."""
    heat = current + sum(e.delta for e in events)
    return max(0.0, min(heat, 1.2))


def is_backed_off(heat: float) -> bool:
    return heat >= BACKOFF_THRESHOLD
