"""Animation system with easing functions and tweening."""

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

from pygame_ui.utils.math_utils import lerp, lerp_tuple


class EaseType(Enum):
    """Available easing function types."""

    LINEAR = auto()
    EASE_IN = auto()
    EASE_OUT = auto()
    EASE_IN_OUT = auto()
    EASE_OUT_BACK = auto()
    EASE_OUT_ELASTIC = auto()
    EASE_OUT_BOUNCE = auto()


def ease_linear(t: float) -> float:
    """Linear interpolation (no easing)."""
    return t


def ease_in_quad(t: float) -> float:
    """Quadratic ease in - accelerates from zero."""
    return t * t


def ease_out_quad(t: float) -> float:
    """Quadratic ease out - decelerates to zero."""
    return 1 - (1 - t) * (1 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease in/out - accelerates then decelerates."""
    if t < 0.5:
        return 2 * t * t
    return 1 - pow(-2 * t + 2, 2) / 2


def ease_out_back(t: float, overshoot: float = 1.70158) -> float:
    """Ease out with overshoot - goes past target then settles back.

    Creates a "bouncy" feel perfect for card animations.
    """
    c3 = overshoot + 1
    return 1 + c3 * pow(t - 1, 3) + overshoot * pow(t - 1, 2)


def ease_out_elastic(t: float) -> float:
    """Elastic ease out - springs past target with diminishing oscillation.

    Great for emphasis animations like counter pops.
    """
    if t == 0:
        return 0
    if t == 1:
        return 1

    c4 = (2 * math.pi) / 3
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


def ease_out_bounce(t: float) -> float:
    """Bounce ease out - bounces at the end like a ball."""
    n1 = 7.5625
    d1 = 2.75

    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


# Mapping from EaseType to function
EASE_FUNCTIONS: Dict[EaseType, Callable[[float], float]] = {
    EaseType.LINEAR: ease_linear,
    EaseType.EASE_IN: ease_in_quad,
    EaseType.EASE_OUT: ease_out_quad,
    EaseType.EASE_IN_OUT: ease_in_out_quad,
    EaseType.EASE_OUT_BACK: ease_out_back,
    EaseType.EASE_OUT_ELASTIC: ease_out_elastic,
    EaseType.EASE_OUT_BOUNCE: ease_out_bounce,
}


def get_easing(ease_type: EaseType, t: float) -> float:
    """Get eased value for a given ease type and progress.

    Args:
        ease_type: The type of easing to apply
        t: Progress from 0.0 to 1.0

    Returns:
        Eased progress value
    """
    return EASE_FUNCTIONS[ease_type](t)


@dataclass
class Tween:
    """A single property animation from start to end value.

    Supports animating floats or tuples (positions, colors).
    """

    target: Any  # Object to animate
    property_name: str  # Property/attribute name
    start_value: Any  # Starting value
    end_value: Any  # Ending value
    duration: float  # Duration in seconds
    ease_type: EaseType = EaseType.EASE_OUT
    delay: float = 0.0  # Delay before starting
    on_complete: Optional[Callable[[], None]] = None

    elapsed: float = field(default=0.0, init=False)
    started: bool = field(default=False, init=False)
    completed: bool = field(default=False, init=False)

    def update(self, dt: float) -> bool:
        """Update the tween by delta time.

        Args:
            dt: Delta time in seconds

        Returns:
            True if still animating, False if completed
        """
        if self.completed:
            return False

        self.elapsed += dt

        # Handle delay
        if self.elapsed < self.delay:
            return True

        if not self.started:
            self.started = True
            # Capture start value if not set
            if self.start_value is None:
                self.start_value = getattr(self.target, self.property_name)

        # Calculate progress
        active_time = self.elapsed - self.delay
        raw_progress = active_time / self.duration if self.duration > 0 else 1.0
        progress = min(1.0, raw_progress)

        # Apply easing
        eased = get_easing(self.ease_type, progress)

        # Interpolate value
        if isinstance(self.start_value, tuple):
            new_value = lerp_tuple(self.start_value, self.end_value, eased)
            # Convert to int tuple if original was int
            if isinstance(self.start_value[0], int):
                new_value = tuple(int(round(v)) for v in new_value)
        else:
            new_value = lerp(self.start_value, self.end_value, eased)

        # Apply to target
        setattr(self.target, self.property_name, new_value)

        # Check completion
        if progress >= 1.0:
            self.completed = True
            if self.on_complete:
                self.on_complete()
            return False

        return True


class TweenManager:
    """Manages multiple concurrent tweens."""

    def __init__(self):
        self.tweens: List[Tween] = []

    def add(self, tween: Tween) -> Tween:
        """Add a tween to be managed.

        Args:
            tween: The tween to add

        Returns:
            The added tween (for chaining)
        """
        self.tweens.append(tween)
        return tween

    def create(
        self,
        target: Any,
        property_name: str,
        end_value: Any,
        duration: float,
        ease_type: EaseType = EaseType.EASE_OUT,
        start_value: Any = None,
        delay: float = 0.0,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> Tween:
        """Create and add a new tween.

        Args:
            target: Object to animate
            property_name: Property/attribute name
            end_value: Target value
            duration: Animation duration in seconds
            ease_type: Easing function type
            start_value: Starting value (None = current value)
            delay: Delay before starting
            on_complete: Callback when animation completes

        Returns:
            The created tween
        """
        if start_value is None:
            start_value = getattr(target, property_name)

        tween = Tween(
            target=target,
            property_name=property_name,
            start_value=start_value,
            end_value=end_value,
            duration=duration,
            ease_type=ease_type,
            delay=delay,
            on_complete=on_complete,
        )
        return self.add(tween)

    def update(self, dt: float) -> None:
        """Update all tweens.

        Args:
            dt: Delta time in seconds
        """
        # Update and remove completed tweens
        self.tweens = [tween for tween in self.tweens if tween.update(dt)]

    def clear(self) -> None:
        """Remove all tweens."""
        self.tweens.clear()

    def cancel_for(self, target: Any, property_name: Optional[str] = None) -> None:
        """Cancel tweens for a specific target.

        Args:
            target: The target object
            property_name: Specific property to cancel (None = all properties)
        """
        self.tweens = [
            tween
            for tween in self.tweens
            if not (
                tween.target is target
                and (property_name is None or tween.property_name == property_name)
            )
        ]

    @property
    def is_animating(self) -> bool:
        """Check if any tweens are active."""
        return len(self.tweens) > 0


class AnimationSequence:
    """Chain multiple tweens to run in sequence."""

    def __init__(self):
        self.steps: List[Tween] = []
        self.current_index: int = 0
        self.completed: bool = False

    def then(
        self,
        target: Any,
        property_name: str,
        end_value: Any,
        duration: float,
        ease_type: EaseType = EaseType.EASE_OUT,
    ) -> "AnimationSequence":
        """Add a step to the sequence.

        Args:
            target: Object to animate
            property_name: Property to animate
            end_value: Target value
            duration: Animation duration
            ease_type: Easing function

        Returns:
            Self for chaining
        """
        tween = Tween(
            target=target,
            property_name=property_name,
            start_value=None,  # Will be captured when step starts
            end_value=end_value,
            duration=duration,
            ease_type=ease_type,
        )
        self.steps.append(tween)
        return self

    def update(self, dt: float) -> bool:
        """Update the sequence.

        Args:
            dt: Delta time in seconds

        Returns:
            True if still animating
        """
        if self.completed or self.current_index >= len(self.steps):
            self.completed = True
            return False

        current = self.steps[self.current_index]

        # Initialize start value if needed
        if not current.started and current.start_value is None:
            current.start_value = getattr(current.target, current.property_name)

        if not current.update(dt):
            self.current_index += 1

        return not self.completed


# Global tween manager for convenience
_global_tween_manager: Optional[TweenManager] = None


def get_tween_manager() -> TweenManager:
    """Get the global tween manager instance."""
    global _global_tween_manager
    if _global_tween_manager is None:
        _global_tween_manager = TweenManager()
    return _global_tween_manager
