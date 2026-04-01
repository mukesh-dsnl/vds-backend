import math


def apply_curve(progress: float, curve_type: str = "sigmoid") -> float:
    """
    Map linear progress (0 → 1) to a shaped curve value (0 → 1).

    Supported curve types:
        sigmoid  — S-curve using logistic function
        linear   — Identity (no shaping)

    Args:
        progress:   Linear progress value from 0.0 to 1.0.
        curve_type: Name of the curve to apply.

    Returns:
        Adjusted progress value between 0.0 and 1.0.
    """
    if curve_type == "sigmoid":
        return 1.0 / (1.0 + math.exp(-10.0 * (progress - 0.5)))
    elif curve_type == "linear":
        return progress
    else:
        # Default to sigmoid for unknown types
        return 1.0 / (1.0 + math.exp(-10.0 * (progress - 0.5)))
