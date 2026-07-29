"""
Risk Manager — Trust scoring for LLM outputs.

Evaluates each LLM completion against trust criteria:
  - Confidence threshold: minimum behavioral consistency score
  - Drift threshold: trigger alerts when drift exceeds limit
  - Collision-group trust budget: limits trust per behavior group
"""

import hashlib
import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TrustLevel(str, Enum):
    """Trust levels for LLM outputs."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SUSPICIOUS = "suspicious"
    REJECTED = "rejected"


@dataclass
class OutputSignal:
    """Behavioral signal from an LLM output for trust scoring."""
    refusal_probability: float = 0.0
    output_quality: float = 0.0
    confidence: float = 0.5
    collision_group_id: str = "uncertain"
    source: str = ""
    text_length: int = 0


@dataclass
class TrustDecision:
    """Decision from the trust scoring engine."""
    trust_level: TrustLevel = TrustLevel.MEDIUM
    score: float = 0.5
    allowed: bool = True
    reason: str = ""


class RiskManager:
    """
    Trust scoring engine for LLM output forensics.

    Evaluates each output signal against:
      1. Drift threshold (has the model's behavior shifted?)
      2. Confidence threshold (is the output consistent?)
      3. Collision-group trust budget (limit per behavior type)
    """

    def __init__(self, codec=None, factory=None,
                 min_confidence: float = 0.3,
                 drift_threshold: float = 0.7,
                 trust_budget_per_group: int = 1000,
                 refusal_penalty: float = 0.4):
        self.codec = codec
        self.factory = factory
        self.min_confidence = min_confidence
        self.drift_threshold = drift_threshold
        self.trust_budget_per_group = trust_budget_per_group
        self.refusal_penalty = refusal_penalty

        self._drift_score: float = 0.0
        self._total_signals = 0
        self._total_allowed = 0
        self._group_counts: dict = {}

    def evaluate_output(self, signal: OutputSignal) -> TrustDecision:
        """
        Evaluate an LLM output signal against trust criteria.

        Returns a TrustDecision with trust_level, score, and allowed flag.
        """
        self._total_signals += 1
        group = signal.collision_group_id

        # Track group usage
        self._group_counts[group] = self._group_counts.get(group, 0) + 1

        # 1. Drift check — high refusal probability suggests behavioral drift
        if signal.refusal_probability > self.drift_threshold:
            return TrustDecision(
                trust_level=TrustLevel.REJECTED,
                score=0.0,
                allowed=False,
                reason="drift_threshold_exceeded",
            )

        # 2. Confidence check
        if signal.confidence < self.min_confidence:
            return TrustDecision(
                trust_level=TrustLevel.SUSPICIOUS,
                score=signal.confidence,
                allowed=False,
                reason="confidence_below_threshold",
            )

        # 3. Trust budget check per collision group
        if self._group_counts.get(group, 0) > self.trust_budget_per_group:
            return TrustDecision(
                trust_level=TrustLevel.LOW,
                score=0.3,
                allowed=False,
                reason="group_trust_budget_exhausted",
            )

        # 4. Compute trust score from quality and refusal probability
        quality = signal.output_quality
        refusal_penalty = signal.refusal_probability * self.refusal_penalty
        trust_score = max(0.0, quality - refusal_penalty)

        # 5. Determine trust level
        if trust_score >= 0.8:
            level = TrustLevel.HIGH
        elif trust_score >= 0.5:
            level = TrustLevel.MEDIUM
        elif trust_score >= 0.2:
            level = TrustLevel.LOW
        else:
            level = TrustLevel.SUSPICIOUS

        self._total_allowed += 1
        return TrustDecision(
            trust_level=level,
            score=round(trust_score, 4),
            allowed=trust_score > 0.2,
            reason=f"trust_score_{level.value}",
        )

    def update_drift(self, new_refusal_rate: float) -> None:
        """Update drift score based on observed refusal rate."""
        self._drift_score = new_refusal_rate

    def get_stats(self) -> dict:
        """Get trust scoring statistics."""
        return {
            "drift_detected": self._drift_score > self.drift_threshold,
            "drift_score": round(self._drift_score, 4),
            "total_signals": self._total_signals,
            "total_allowed": self._total_allowed,
            "min_confidence": self.min_confidence,
            "group_counts": dict(self._group_counts),
        }
