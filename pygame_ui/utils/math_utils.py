"""Math utility functions for animations and layout."""

import math
from typing import Tuple, Union

Number = Union[int, float]


def lerp(start: Number, end: Number, t: float) -> float:
    """Linear interpolation between start and end.

    Args:
        start: Starting value
        end: Ending value
        t: Interpolation factor (0.0 to 1.0)

    Returns:
        Interpolated value
    """
    return start + (end - start) * t


def lerp_tuple(
    start: Tuple[Number, ...], end: Tuple[Number, ...], t: float
) -> Tuple[float, ...]:
    """Linear interpolation between two tuples (e.g., positions, colors).

    Args:
        start: Starting tuple
        end: Ending tuple
        t: Interpolation factor (0.0 to 1.0)

    Returns:
        Interpolated tuple
    """
    return tuple(lerp(s, e, t) for s, e in zip(start, end))


def clamp(value: Number, min_val: Number, max_val: Number) -> Number:
    """Clamp a value between min and max.

    Args:
        value: Value to clamp
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Clamped value
    """
    return max(min_val, min(max_val, value))


def inverse_lerp(start: Number, end: Number, value: Number) -> float:
    """Calculate the interpolation factor for a value between start and end.

    Args:
        start: Starting value
        end: Ending value
        value: Value to find factor for

    Returns:
        Interpolation factor (0.0 to 1.0, unclamped)
    """
    if end - start == 0:
        return 0.0
    return (value - start) / (end - start)


def remap(
    value: Number,
    in_start: Number,
    in_end: Number,
    out_start: Number,
    out_end: Number,
) -> float:
    """Remap a value from one range to another.

    Args:
        value: Value to remap
        in_start: Input range start
        in_end: Input range end
        out_start: Output range start
        out_end: Output range end

    Returns:
        Remapped value
    """
    t = inverse_lerp(in_start, in_end, value)
    return lerp(out_start, out_end, t)


def distance(p1: Tuple[Number, Number], p2: Tuple[Number, Number]) -> float:
    """Calculate distance between two 2D points.

    Args:
        p1: First point (x, y)
        p2: Second point (x, y)

    Returns:
        Distance between points
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def normalize_angle(angle: float) -> float:
    """Normalize angle to be within -180 to 180 degrees.

    Args:
        angle: Angle in degrees

    Returns:
        Normalized angle
    """
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle


def smooth_damp(
    current: float,
    target: float,
    velocity: float,
    smooth_time: float,
    dt: float,
    max_speed: float = float("inf"),
) -> Tuple[float, float]:
    """Smoothly interpolate towards a target using spring-like damping.

    Based on Game Programming Gems 4 smooth damp.

    Args:
        current: Current value
        target: Target value
        velocity: Current velocity (will be modified)
        smooth_time: Approximate time to reach target
        dt: Delta time
        max_speed: Maximum speed

    Returns:
        Tuple of (new_value, new_velocity)
    """
    smooth_time = max(0.0001, smooth_time)
    omega = 2.0 / smooth_time

    x = omega * dt
    exp_factor = 1.0 / (1.0 + x + 0.48 * x * x + 0.235 * x * x * x)

    delta = current - target
    original_target = target

    # Clamp maximum speed
    max_delta = max_speed * smooth_time
    delta = clamp(delta, -max_delta, max_delta)
    target = current - delta

    temp = (velocity + omega * delta) * dt
    new_velocity = (velocity - omega * temp) * exp_factor
    new_value = target + (delta + temp) * exp_factor

    # Prevent overshooting
    if (original_target - current > 0.0) == (new_value > original_target):
        new_value = original_target
        new_velocity = (new_value - original_target) / dt

    return new_value, new_velocity
