"""
Pure market analysis algorithms - ZERO framework dependencies
Reusable logic for DREAMSWAP research system.
"""

from typing import Dict, Any, List
import numpy as np
def regime_detection(
    ema_slope: float,
    adx: float,
    plus_di: float,
    minus_di: float,
    atr: float,
    price: float,
    ema_20: float,
    atr_50_avg: float
) -> str:
    """
    Market regime classification.
    Returns: TRENDING_UP / TRENDING_DOWN / RANGING / HIGH_VOL / LOW_VOL
    """
    # TRENDING_UP: EMA slope > 0, ADX > 25, +DI > -DI
    if ema_slope > 0 and adx > 25 and plus_di > minus_di:
        return "TRENDING_UP"
    # TRENDING_DOWN: EMA slope < 0, ADX > 25, -DI > +DI
    if ema_slope < 0 and adx > 25 and minus_di > plus_di:
        return "TRENDING_DOWN"
    # RANGING: ADX < 20, price within 1 ATR of 20-period mean
    if adx < 20 and abs(price - ema_20) <= atr:
        return "RANGING"
    # HIGH_VOL: ATR(14) > 2× 50-period ATR average
    if atr > 2 * atr_50_avg:
        return "HIGH_VOL"
    # LOW_VOL: ATR(14) < 0.5× 50-period ATR average
    if atr < 0.5 * atr_50_avg:
        return "LOW_VOL"
    return "RANGING"
def liquidity_persistence(
    depth_history: List[float],
    initial_depth: float,
    threshold: float = 0.85,
    min_duration: int = 180
) -> float:
    """
    Measures if top-5 depth remains >=85% of initial depth for >=180 seconds.
    Returns: 0.0 → 1.0 persistence score.
    """
    if not depth_history or initial_depth <= 0:
        return 0.0

    sustained = sum(1 for d in depth_history
                    if d >= threshold * initial_depth)
    persistence = sustained / len(depth_history)
    return min(persistence, 1.0)
def cancellation_velocity(
    cancelled_volume: float,
    executed_volume: float
) -> float:
    """
    Cancelled volume / Executed volume.
    Threshold: < 0.7 indicates healthy execution.
    """
    if executed_volume <= 0:
        return 1.0
    return cancelled_volume / executed_volume
def depth_stability(
    depth_history: List[float]
) -> float:
    """
    Standard deviation of depth / mean depth.
    Threshold: < 0.3 indicates stable liquidity.
    """
    if not depth_history:
        return 0.0
    depths = np.array(depth_history)
    mean_depth = float(np.mean(depths))
    if mean_depth == 0:
        return 1.0
    return float(np.std(depths) / mean_depth)
def acceleration_ratio(
    current_1m_volume: float,
    baseline_15m_volume: float
) -> float:
    """
    1-min volume / 15-min baseline volume.
    Threshold: > 1.8 indicates accelerating participation.
    """
    if baseline_15m_volume <= 0:
        return 0.0
    return current_1m_volume / baseline_15m_volume
def direction_bias(
    mid: float,
    prev_mid: float,
    spread: float
) -> Optional[str]:
    """
    Determines LONG/SHORT bias from mid price movement.
    Returns: "LONG", "SHORT", or None.
    """
    if mid <= 0 or spread <= 0:
        return None
    pct_change = (mid - prev_mid) / prev_mid
    if pct_change > 0.001:  # > 0.1% move
        return "LONG"
    elif pct_change < -0.001:
        return "SHORT"
    return None
def volume_anomaly(
    current_volume: float,
    baseline_volume: float,
    threshold_multiplier: float = 2.0
) -> float:
    """
    Identifies unusual volume spikes.
    Returns anomaly score (higher = more anomalous).
    """
    if baseline_volume <= 0:
        return 0.0
    ratio = current_volume / baseline_volume
    return max(0.0, ratio - threshold_multiplier)
def moving_average(values: List[float], window: int) -> List[float]:
    """Simple moving average."""
    if window <= 0 or len(values) < window:
        return values[:]
    return [float(np.mean(values[i-window+1:i+1]))
            for i in range(len(values)) if i >= window - 1]
def exponential_moving_average(values: List[float], alpha: float) -> List[float]:
    """Exponential moving average."""
    if not values or not (0 < alpha <= 1):
        return values[:]
    ema = [values[0]]
    for v in values[1:]:
        ema.append(alpha * v + (1 - alpha) * ema[-1])
    return ema
def z_score(value: float, mean: float, std: float) -> float:
    """Standard z-score."""
    if std == 0:
        return 0.0
    return (value - mean) / std
def bollinger_bands(
    values: List[float],
    window: int = 20,
    num_std: float = 2.0
) -> Dict[str, float]:
    """Bollinger bands for price analysis."""
    if len(values) < window:
        return {'upper': 0.0, 'middle': 0.0, 'lower': 0.0}
    recent = values[-window:]
    middle = float(np.mean(recent))
    std = float(np.std(recent))
    return {
        'upper': middle + num_std * std,
        'middle': middle,
        'lower': middle - num_std * std,
    }
def entropy(probabilities: List[float]) -> float:
    """Shannon entropy for regime classification."""
    probs = np.array([p for p in probabilities if p > 0])
    if len(probs) == 0:
        return 0.0
    return -float(np.sum(probs * np.log2(probs)))
def kl_divergence(p: List[float], q: List[float]) -> float:
    """Kullback-Leibler divergence for surprise detection."""
    p_arr, q_arr = np.array(p), np.array(q)
    mask = (p_arr > 0) & (q_arr > 0)
    if not np.any(mask):
        return 0.0
    return float(np.sum(p_arr[mask] * np.log2(p_arr[mask] / q_arr[mask])))
