import random


def apply_noise(value: float, noise_level: float) -> float:
    """
    Add random noise to a value.

    The noise is uniformly distributed in [-noise_level, +noise_level].

    Args:
        value:       Base value to add noise to.
        noise_level: Maximum absolute noise magnitude (as a fraction, e.g. 0.02 = ±2%).

    Returns:
        The value with noise applied.
    """
    if noise_level <= 0:
        return value
    noise = random.uniform(-noise_level, noise_level)
    return value + noise
