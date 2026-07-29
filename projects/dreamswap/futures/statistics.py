"""
Pure statistics module - NO FRAMEWORK DEPENDENCIES
Provides lift calculation, bayesian updates, and confidence intervals
for DREAMSWAP research system.
"""

from math import sqrt, log, exp
from typing import Tuple, List, Dict, Any
import numpy as np
from dataclasses import dataclass
from typing import Optional
@dataclass(frozen=True)
class ConfidenceInterval:
    """Result of a confidence interval calculation."""
    lower: float
    upper: float
def calculate_lift(
    h1_success: int,
    h1_total: int,
    baseline_success: int,
    baseline_total: int
) -> float:
    """
    Calculate P(continuation | H1) / P(continuation | ¬H1)

    This is the CORE METRIC that determines if a hypothesis is valid.
    Lift > 1.0 means the hypothesis predicts continuation better than baseline.
    """
    if h1_total == 0 or baseline_total == 0:
        return 0.0

    p_h1 = h1_success / h1_total
    p_baseline = baseline_success / baseline_total

    if p_baseline == 0.0:
        return float('inf')

    return p_h1 / p_baseline
def bayesian_update(
    prior: float,
    likelihood: float,
    evidence: float
) -> float:
    """
    Bayesian posterior: P(H|E) = P(E|H) * P(H) / P(E)
    Used for hypothesis survival criteria.
    """
    if evidence == 0.0:
        return prior
    return likelihood * prior / evidence
def confidence_interval(
    successes: int,
    trials: int,
    confidence: float = 0.95
) -> ConfidenceInterval:
    """
    Wilson score interval for binomial proportion.
    Returns ConfidenceInterval(lower_bound, upper_bound).
    """
    if trials == 0:
        return ConfidenceInterval(0.0, 0.0)

    z = 1.96 if abs(confidence - 0.95) < 1e-9 else 2.576
    p = successes / trials
    denominator = 1 + z*z/trials
    center = (p + z*z/(2*trials)) / denominator
    margin = z * sqrt(p*(1-p)/trials + z*z/(4*trials*trials)) / denominator
    return ConfidenceInterval(center - margin, center + margin)
def sample_size_required(
    min_lift: float,
    baseline_rate: float,
    power: float = 0.8,
    alpha: float = 0.05
) -> int:
    """
    Calculate minimum sample size for statistical validity.
    Uses normal approximation for binomial proportions.
    """
    from math import ceil
    z_alpha = 1.96  # for alpha=0.05
    z_beta = 0.84   # for power=0.8

    p1 = baseline_rate * min_lift
    p2 = baseline_rate

    numerator = (z_alpha * sqrt(2 * p2 * (1 - p2)) +
                 z_beta * sqrt(p1 * (1 - p1) + p2 * (1 - p2)))**2
    denominator = (p1 - p2)**2

    return ceil(numerator / denominator)
def regime_stratified_lift(
    observations: List[Dict[str, Any]],
    regime: str
) -> float:
    """
    Calculate lift only within a specific regime.
    Ensures hypotheses are only evaluated in their valid context.
    """
    regime_obs = [o for o in observations if o.get('regime') == regime]
    if not regime_obs:
        return 0.0

    h1_success = sum(1 for o in regime_obs if o.get('tier1_reached'))
    baseline_success = sum(1 for o in regime_obs if o.get('baseline_reached'))

    return calculate_lift(h1_success, len(regime_obs),
                         baseline_success, len(regime_obs))
def lift_confidence(
    h1_success: int,
    h1_total: int,
    baseline_success: int,
    baseline_total: int,
    confidence: float = 0.95
) -> Tuple[float, Tuple[float, float]]:
    """
    Calculate lift and its confidence interval together.
    Returns (lift, (lower_ci, upper_ci)).
    """
    lift_val = calculate_lift(h1_success, h1_total,
                              baseline_success, baseline_total)
    ci = confidence_interval(h1_success, h1_total, confidence)
    return lift_val, (ci.lower, ci.upper)
def standard_error_lift(
    h1_success: int,
    h1_total: int,
    baseline_success: int,
    baseline_total: int
) -> float:
    """
    Standard error of the lift ratio using delta method.
    """
    if h1_total == 0 or baseline_total == 0:
        return 0.0

    p_h1 = h1_success / h1_total
    p_baseline = baseline_success / baseline_total

    if p_baseline == 0.0:
        return float('inf')

    var_lift = (p_h1 / p_baseline**2) * (
        (1 - p_h1) / h1_total +
        p_h1 * (1 - p_baseline) / baseline_total
    )
    return sqrt(var_lift)
def bootstrap_lift(
    h1_success: int,
    h1_total: int,
    baseline_success: int,
    baseline_total: int,
    n_bootstrap: int = 1000
) -> Dict[str, float]:
    """
    Non-parametric bootstrap for lift confidence intervals.
    Useful when normality assumptions are questionable.
    """
    rng = np.random.RandomState(42)

    h1_rate = h1_success / h1_total if h1_total > 0 else 0.0
    baseline_rate = baseline_success / baseline_total if baseline_total > 0 else 0.0

    boots = []
    for _ in range(n_bootstrap):
        h1_boot = rng.binomial(h1_total, h1_rate)
        baseline_boot = rng.binomial(baseline_total, baseline_rate)
        lift = calculate_lift(h1_boot, h1_total,
                             baseline_boot, baseline_total)
        boots.append(lift)

    boots = np.array(boots)
    return {
        'mean': float(np.mean(boots)),
        'std': float(np.std(boots)),
        'lower_95': float(np.percentile(boots, 2.5)),
        'upper_95': float(np.percentile(boots, 97.5)),
    }
