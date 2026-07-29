"""
Analysis utilities - ZERO framework dependencies
Reusable patterns for DREAMSWAP research system.
"""

from typing import Sequence, List, Optional
import math
def weighted_average(values: Sequence[float], weights: Sequence[float]) -> float:
    """Weighted average - used in regime_multiplier calculations."""
    if len(values) != len(weights) or not values:
        return 0.0
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_w
def normalize(
    values: Sequence[float],
    new_min: float = 0.0,
    new_max: float = 1.0
) -> List[float]:
    """Min-max normalization to [new_min, new_max] range."""
    if not values:
        return []
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return [new_min] * len(values)
    return [(v - vmin) / (vmax - vmin) * (new_max - new_min) + new_min
            for v in values]
def clamp(value: float, low: float, high: float) -> float:
    """Clamp value to [low, high] range - used throughout framework."""
    return max(low, min(high, value))
def percentile(data: Sequence[float], p: float) -> float:
    """Calculate percentile (0-100) of data."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = p / 100.0 * (len(sorted_data) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_data[lo]
    return sorted_data[lo] * (hi - idx) + sorted_data[hi] * (idx - lo)
def exponential_decay(value: float, half_life: float, dt: float) -> float:
    """Exponential decay: value * (1/2)^(dt / half_life)."""
    if half_life <= 0 or dt <= 0:
        return value
    return value * 0.5 ** (dt / half_life)
def entropy(probabilities: Sequence[float]) -> float:
    """Shannon entropy of a probability distribution."""
    probs = [p for p in probabilities if p > 0]
    if not probs:
        return 0.0
    import math
    return -sum(p * math.log2(p) for p in probs)
def kl_divergence(p: Sequence[float], q: Sequence[float]) -> float:
    """Kullback-Leibler divergence D(P || Q)."""
    p_arr, q_arr = list(p), list(q)
    if len(p_arr) != len(q_arr) or not p_arr:
        return 0.0
    total = 0.0
    for pi, qi in zip(p_arr, q_arr):
        if pi > 0 and qi > 0:
            total += pi * math.log2(pi / qi)
    return total
def z_score(value: float, mean: float, std: float) -> float:
    """Standard z-score."""
    if std == 0:
        return 0.0
    return (value - mean) / std
def bollinger_bands(
    values: Sequence[float],
    window: int = 20,
    num_std: float = 2.0
) -> Dict[str, float]:
    """Bollinger bands for price analysis."""
    try:
        import numpy as np
    except ImportError:
        return {'upper': 0.0, 'middle': 0.0, 'lower': 0.0}
    if len(values) < window:
        return {'upper': 0.0, 'middle': 0.0, 'lower': 0.0}
    recent = np.array(values[-window:])
    middle = float(np.mean(recent))
    std = float(np.std(recent))
    return {
        'upper': middle + num_std * std,
        'middle': middle,
        'lower': middle - num_std * std,
    }
def ewm(  # Exponentially Weighted Moving average
    values: Sequence[float],
    alpha: float
) -> List[float]:
    """Exponentially weighted moving average."""
    if not values or not (0 < alpha <= 1):
        return list(values) if values else []
    result = [values[0]]
    for v in values[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])
    return result
def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with configurable default."""
    if denominator == 0:
        return default
    return numerator / denominator
def rate_of_change(old: float, new: float) -> float:
    """Percentage rate of change from old to new."""
    return safe_divide(new - old, old, 0.0)
