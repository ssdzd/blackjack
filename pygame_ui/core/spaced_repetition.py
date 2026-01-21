"""Spaced repetition system for optimized learning.

Implements a simplified SM-2 algorithm to schedule review items
based on user performance. Items answered correctly are shown
less frequently, while difficult items appear more often.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os


@dataclass
class RepetitionItem:
    """A single item tracked by the spaced repetition system.

    Attributes:
        key: Unique identifier (e.g., "deviation_12", "hand_16v10")
        easiness: E-factor controlling interval growth (1.3 to 2.5)
        interval: Days until next scheduled review
        repetitions: Consecutive correct answers
        next_review: When this item should be reviewed next
        total_attempts: Total times this item has been reviewed
        total_correct: Total correct answers
    """
    key: str
    easiness: float = 2.5
    interval: int = 1
    repetitions: int = 0
    next_review: str = ""  # ISO format datetime
    total_attempts: int = 0
    total_correct: int = 0

    def __post_init__(self):
        if not self.next_review:
            self.next_review = datetime.now().isoformat()

    @property
    def next_review_datetime(self) -> datetime:
        """Get next_review as datetime object."""
        try:
            return datetime.fromisoformat(self.next_review)
        except (ValueError, TypeError):
            return datetime.now()

    @property
    def accuracy(self) -> float:
        """Get accuracy percentage for this item."""
        if self.total_attempts == 0:
            return 0.0
        return (self.total_correct / self.total_attempts) * 100

    @property
    def is_due(self) -> bool:
        """Check if this item is due for review."""
        return self.next_review_datetime <= datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RepetitionItem":
        """Create from dictionary."""
        return cls(**data)


class SpacedRepetitionManager:
    """Manages spaced repetition scheduling for learning items.

    Uses a simplified SM-2 algorithm:
    - Quality 0-2: Incorrect - reset repetitions, show sooner
    - Quality 3-5: Correct - increase interval based on easiness

    The easiness factor adjusts based on performance to personalize
    the learning curve for each item.
    """

    def __init__(self, data_file: str = None):
        """Initialize the spaced repetition manager.

        Args:
            data_file: Path to JSON file for persistence.
                      Defaults to ~/.blackjack_trainer_sr.json
        """
        if data_file is None:
            home = os.path.expanduser("~")
            data_file = os.path.join(home, ".blackjack_trainer_sr.json")

        self.data_file = data_file
        self.items: Dict[str, RepetitionItem] = {}
        self._load()

    def _load(self) -> None:
        """Load items from file."""
        if not os.path.exists(self.data_file):
            return

        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)

            for key, item_data in data.get("items", {}).items():
                self.items[key] = RepetitionItem.from_dict(item_data)
        except (json.JSONDecodeError, TypeError, KeyError):
            # If file is corrupted, start fresh
            self.items = {}

    def save(self) -> None:
        """Save items to file."""
        try:
            data = {
                "items": {key: item.to_dict() for key, item in self.items.items()},
                "last_saved": datetime.now().isoformat(),
            }

            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError:
            pass  # Silently fail if can't write

    def get_or_create_item(self, key: str) -> RepetitionItem:
        """Get an existing item or create a new one.

        Args:
            key: Unique identifier for the item

        Returns:
            The RepetitionItem for this key
        """
        if key not in self.items:
            self.items[key] = RepetitionItem(key=key)
        return self.items[key]

    def update_after_review(self, key: str, quality: int) -> None:
        """Update an item after a review attempt.

        Implements SM-2 algorithm:
        - quality 0: Complete failure
        - quality 1: Incorrect but recognized
        - quality 2: Incorrect with significant hesitation
        - quality 3: Correct with difficulty
        - quality 4: Correct with some hesitation
        - quality 5: Perfect recall

        For simplicity in training drills:
        - Correct answer: quality = 4 (or 5 if fast)
        - Incorrect answer: quality = 1

        Args:
            key: Item identifier
            quality: Performance rating 0-5
        """
        quality = max(0, min(5, quality))  # Clamp to 0-5

        item = self.get_or_create_item(key)
        item.total_attempts += 1

        if quality >= 3:  # Correct response
            item.total_correct += 1

            if item.repetitions == 0:
                item.interval = 1
            elif item.repetitions == 1:
                item.interval = 6
            else:
                item.interval = int(item.interval * item.easiness)

            item.repetitions += 1
        else:  # Incorrect response
            item.repetitions = 0
            item.interval = 1

        # Update easiness factor (E-factor)
        # Formula: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        item.easiness = max(
            1.3,
            item.easiness + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        )

        # Schedule next review
        item.next_review = (datetime.now() + timedelta(days=item.interval)).isoformat()

        self.save()

    def record_correct(self, key: str, was_fast: bool = False) -> None:
        """Convenience method for recording a correct answer.

        Args:
            key: Item identifier
            was_fast: True if answered quickly (quality 5 vs 4)
        """
        quality = 5 if was_fast else 4
        self.update_after_review(key, quality)

    def record_incorrect(self, key: str, was_close: bool = False) -> None:
        """Convenience method for recording an incorrect answer.

        Args:
            key: Item identifier
            was_close: True if answer was close (quality 2 vs 1)
        """
        quality = 2 if was_close else 1
        self.update_after_review(key, quality)

    def get_next_item(self, keys: List[str]) -> Optional[str]:
        """Get the next item to review from a list of candidates.

        Priority:
        1. Overdue items (past next_review date), oldest first
        2. New items (never reviewed)
        3. Items due soonest

        Args:
            keys: List of item keys to choose from

        Returns:
            The key of the next item to review, or None if list is empty
        """
        if not keys:
            return None

        # Ensure all items exist
        for key in keys:
            self.get_or_create_item(key)

        now = datetime.now()

        # Find overdue items
        overdue = []
        for key in keys:
            item = self.items[key]
            if item.next_review_datetime <= now:
                overdue.append((key, item.next_review_datetime))

        if overdue:
            # Return the most overdue item
            overdue.sort(key=lambda x: x[1])
            return overdue[0][0]

        # Find new items (never attempted)
        for key in keys:
            if self.items[key].total_attempts == 0:
                return key

        # Return item due soonest
        items_with_due = [(key, self.items[key].next_review_datetime) for key in keys]
        items_with_due.sort(key=lambda x: x[1])
        return items_with_due[0][0]

    def get_due_count(self, keys: List[str]) -> int:
        """Get the number of items due for review.

        Args:
            keys: List of item keys to check

        Returns:
            Number of items that are due or overdue
        """
        now = datetime.now()
        count = 0

        for key in keys:
            if key in self.items:
                if self.items[key].next_review_datetime <= now:
                    count += 1
            else:
                # New items count as due
                count += 1

        return count

    def get_weak_items(self, keys: List[str], threshold: float = 70.0) -> List[str]:
        """Get items with accuracy below threshold.

        Args:
            keys: List of item keys to check
            threshold: Accuracy percentage threshold

        Returns:
            List of keys with accuracy below threshold
        """
        weak = []

        for key in keys:
            if key in self.items:
                item = self.items[key]
                if item.total_attempts >= 3 and item.accuracy < threshold:
                    weak.append(key)

        return weak

    def get_stats(self, keys: List[str]) -> dict:
        """Get aggregate statistics for a set of items.

        Args:
            keys: List of item keys

        Returns:
            Dictionary with overall stats
        """
        total_attempts = 0
        total_correct = 0
        items_mastered = 0  # Interval >= 21 days
        items_learning = 0  # At least 1 attempt
        items_new = 0

        for key in keys:
            if key in self.items:
                item = self.items[key]
                total_attempts += item.total_attempts
                total_correct += item.total_correct

                if item.total_attempts == 0:
                    items_new += 1
                elif item.interval >= 21:
                    items_mastered += 1
                else:
                    items_learning += 1
            else:
                items_new += 1

        accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0.0

        return {
            "total_items": len(keys),
            "items_mastered": items_mastered,
            "items_learning": items_learning,
            "items_new": items_new,
            "total_attempts": total_attempts,
            "total_correct": total_correct,
            "accuracy": accuracy,
        }

    def reset_item(self, key: str) -> None:
        """Reset an item to its initial state.

        Args:
            key: Item identifier
        """
        if key in self.items:
            self.items[key] = RepetitionItem(key=key)
            self.save()

    def reset_all(self) -> None:
        """Reset all items."""
        self.items = {}
        self.save()


# Global singleton
_sr_manager: Optional[SpacedRepetitionManager] = None


def get_sr_manager() -> SpacedRepetitionManager:
    """Get the global spaced repetition manager instance."""
    global _sr_manager
    if _sr_manager is None:
        _sr_manager = SpacedRepetitionManager()
    return _sr_manager
