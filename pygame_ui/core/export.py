"""CSV export functionality for hand history and statistics."""

import csv
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from pygame_ui.core.hand_logger import HandRecord, get_hand_logger
from pygame_ui.core.stats_manager import get_stats_manager


def export_hand_history(
    filepath: str,
    hands: Optional[List[HandRecord]] = None,
    include_decisions: bool = True,
) -> bool:
    """Export hand history to CSV.

    Args:
        filepath: Path to save CSV file
        hands: List of hands to export (defaults to all history)
        include_decisions: Whether to include individual decisions

    Returns:
        True if export successful
    """
    try:
        if hands is None:
            hands = get_hand_logger().history

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)

            # Header
            headers = [
                "ID",
                "Timestamp",
                "Player Cards",
                "Dealer Cards",
                "Dealer Upcard",
                "Player Value",
                "Dealer Value",
                "Initial Bet",
                "Final Bet",
                "Running Count",
                "True Count",
                "Outcome",
                "Profit/Loss",
                "Was Doubled",
                "Was Split",
                "Took Insurance",
                "Insurance Won",
                "Num Decisions",
                "Num Mistakes",
            ]
            if include_decisions:
                headers.extend([
                    "Decisions",
                    "Mistakes",
                ])
            writer.writerow(headers)

            # Data rows
            for hand in hands:
                row = [
                    hand.id,
                    hand.timestamp,
                    " ".join(hand.player_cards),
                    " ".join(hand.dealer_cards),
                    hand.dealer_upcard,
                    hand.player_final_value,
                    hand.dealer_final_value,
                    hand.initial_bet,
                    hand.final_bet,
                    hand.running_count,
                    f"{hand.true_count:.1f}",
                    hand.outcome,
                    f"{hand.profit_loss:.2f}",
                    "Yes" if hand.was_doubled else "No",
                    "Yes" if hand.was_split_hand else "No",
                    "Yes" if hand.took_insurance else "No",
                    "Yes" if hand.insurance_won else "No",
                    len(hand.decisions),
                    len(hand.mistakes),
                ]
                if include_decisions:
                    # Format decisions as action sequence
                    decision_str = " -> ".join(
                        d.get("action", "?") for d in hand.decisions
                    )
                    # Format mistakes
                    mistake_str = "; ".join(
                        f"{m.get('action', '?')} should be {m.get('correct_action', '?')}"
                        for m in hand.mistakes
                    )
                    row.extend([decision_str, mistake_str])

                writer.writerow(row)

        return True
    except IOError:
        return False


def export_decisions(
    filepath: str,
    hands: Optional[List[HandRecord]] = None,
) -> bool:
    """Export all decisions to CSV (one row per decision).

    Args:
        filepath: Path to save CSV file
        hands: List of hands to export (defaults to all history)

    Returns:
        True if export successful
    """
    try:
        if hands is None:
            hands = get_hand_logger().history

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "Hand ID",
                "Timestamp",
                "Action",
                "Player Total",
                "Is Soft",
                "Is Pair",
                "Dealer Upcard",
                "Running Count",
                "True Count",
                "Correct Action",
                "Is Correct",
                "Is Deviation",
                "Deviation Index",
            ])

            # Data rows
            for hand in hands:
                for decision in hand.decisions:
                    writer.writerow([
                        hand.id,
                        decision.get("timestamp", ""),
                        decision.get("action", ""),
                        decision.get("player_total", 0),
                        "Yes" if decision.get("is_soft", False) else "No",
                        "Yes" if decision.get("is_pair", False) else "No",
                        decision.get("dealer_upcard", 0),
                        decision.get("running_count", 0),
                        f"{decision.get('true_count', 0.0):.1f}",
                        decision.get("correct_action", ""),
                        "Yes" if decision.get("is_correct", True) else "No",
                        "Yes" if decision.get("is_deviation", False) else "No",
                        decision.get("deviation_index", ""),
                    ])

        return True
    except IOError:
        return False


def export_mistake_breakdown(filepath: str) -> bool:
    """Export mistake breakdown to CSV.

    Args:
        filepath: Path to save CSV file

    Returns:
        True if export successful
    """
    try:
        mistakes = get_hand_logger().get_mistake_breakdown()

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "Situation",
                "Correct Action",
                "Wrong Action",
                "Count",
                "Is Deviation",
            ])

            # Sort by count descending
            sorted_mistakes = sorted(
                mistakes.values(),
                key=lambda m: m.count,
                reverse=True,
            )

            for mistake in sorted_mistakes:
                writer.writerow([
                    mistake.situation,
                    mistake.correct_action,
                    mistake.wrong_action,
                    mistake.count,
                    "Yes" if mistake.is_deviation else "No",
                ])

        return True
    except IOError:
        return False


def export_strategy_accuracy(filepath: str) -> bool:
    """Export strategy accuracy heat map data to CSV.

    Args:
        filepath: Path to save CSV file

    Returns:
        True if export successful
    """
    try:
        stats = get_hand_logger().get_strategy_accuracy()

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "Player Total",
                "Dealer Upcard",
                "Is Soft",
                "Is Pair",
                "Correct",
                "Incorrect",
                "Total",
                "Accuracy",
            ])

            # Sort by player total, then dealer upcard
            sorted_stats = sorted(
                stats.values(),
                key=lambda s: (s["player_total"], s["dealer_upcard"]),
            )

            for s in sorted_stats:
                writer.writerow([
                    s["player_total"],
                    s["dealer_upcard"],
                    "Yes" if s["is_soft"] else "No",
                    "Yes" if s["is_pair"] else "No",
                    s["correct"],
                    s["incorrect"],
                    s["total"],
                    f"{s['accuracy']:.1%}",
                ])

        return True
    except IOError:
        return False


def export_performance_stats(filepath: str) -> bool:
    """Export overall performance statistics to CSV.

    Args:
        filepath: Path to save CSV file

    Returns:
        True if export successful
    """
    try:
        stats = get_stats_manager()

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)

            # Write as key-value pairs
            writer.writerow(["Statistic", "Value"])

            # Game stats
            writer.writerow(["Total Hands", stats.stats.game.total_hands])
            writer.writerow(["Hands Won", stats.stats.game.hands_won])
            writer.writerow(["Hands Lost", stats.stats.game.hands_lost])
            writer.writerow(["Hands Pushed", stats.stats.game.hands_pushed])
            writer.writerow(["Blackjacks", stats.stats.game.blackjacks])
            writer.writerow(["Win Rate", f"{stats.stats.game.win_rate:.1%}"])

            writer.writerow([])  # Empty row

            # Drill stats
            writer.writerow(["Counting Attempts", stats.stats.drills.counting_attempts])
            writer.writerow(["Counting Correct", stats.stats.drills.counting_correct])
            writer.writerow(["Counting Accuracy", f"{stats.stats.drills.counting_accuracy:.1%}"])

            writer.writerow([])

            writer.writerow(["Strategy Attempts", stats.stats.drills.strategy_attempts])
            writer.writerow(["Strategy Correct", stats.stats.drills.strategy_correct])
            writer.writerow(["Strategy Accuracy", f"{stats.stats.drills.strategy_accuracy:.1%}"])

            writer.writerow([])

            writer.writerow(["Speed Best Time", f"{stats.stats.drills.speed_best_time:.1f}s"])
            writer.writerow(["Speed Best Accuracy", f"{stats.stats.drills.speed_best_accuracy:.1%}"])

        return True
    except IOError:
        return False


def export_drill_results(
    filepath: str,
    drill_type: str = "all",
) -> bool:
    """Export drill results to CSV.

    Args:
        filepath: Path to save CSV file
        drill_type: Type of drill ("counting", "strategy", "speed", "deviation", "all")

    Returns:
        True if export successful
    """
    try:
        stats = get_stats_manager().stats.drills

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(["Drill Type", "Attempts", "Correct", "Accuracy", "Additional Info"])

            drills = []

            if drill_type in ("all", "counting"):
                drills.append([
                    "Counting",
                    stats.counting_attempts,
                    stats.counting_correct,
                    f"{stats.counting_accuracy:.1%}",
                    "",
                ])

            if drill_type in ("all", "strategy"):
                drills.append([
                    "Strategy",
                    stats.strategy_attempts,
                    stats.strategy_correct,
                    f"{stats.strategy_accuracy:.1%}",
                    "",
                ])

            if drill_type in ("all", "speed"):
                drills.append([
                    "Speed",
                    stats.speed_attempts,
                    "",
                    f"{stats.speed_best_accuracy:.1%}",
                    f"Best time: {stats.speed_best_time:.1f}s",
                ])

            if drill_type in ("all", "deviation"):
                drills.append([
                    "Deviation",
                    stats.deviation_attempts,
                    stats.deviation_correct,
                    f"{stats.deviation_accuracy:.1%}",
                    "",
                ])

            if drill_type in ("all", "tc_conversion"):
                drills.append([
                    "TC Conversion",
                    stats.tc_conversion_attempts,
                    stats.tc_conversion_correct,
                    f"{stats.tc_conversion_accuracy:.1%}",
                    "",
                ])

            if drill_type in ("all", "deck_estimation"):
                drills.append([
                    "Deck Estimation",
                    stats.deck_estimation_attempts,
                    stats.deck_estimation_correct,
                    f"{stats.deck_estimation_accuracy:.1%}",
                    "",
                ])

            for drill in drills:
                writer.writerow(drill)

        return True
    except IOError:
        return False


def get_export_directory() -> str:
    """Get the default export directory (user's Documents folder)."""
    docs = os.path.expanduser("~/Documents")
    export_dir = os.path.join(docs, "BlackjackTrainer")
    os.makedirs(export_dir, exist_ok=True)
    return export_dir


def generate_export_filename(prefix: str, extension: str = "csv") -> str:
    """Generate a timestamped filename for export."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"
