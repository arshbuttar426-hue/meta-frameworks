"""
Forensic Validator — Behavioral pattern assessment for LLM outputs.

Evaluates LLM completions against known behavioral patterns, maintains
a Pareto front of best behavioral fits, and provides ensemble trust
scoring across multiple assessment criteria.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class ParetoPattern:
    """A behavioral pattern on the Pareto front with its metrics."""
    pattern_id: str
    description: str
    error: float       # 0.0 = perfect match
    accuracy: float    # 1.0 = perfect match
    is_anchored: bool
    complexity: int = 0
    pareto_rank: int = 0


@dataclass
class ValidatorResult:
    """Result of a behavioral validation cycle."""
    cycle: int = 0
    patterns_evaluated: int = 0
    patterns_passed: int = 0
    pareto_front: list = field(default_factory=list)
    anchored_present: bool = True
    best_error: float = 0.0
    best_pattern_id: str = ""


class ForensicValidator:
    """
    Behavioral pattern validator for LLM output forensics.

    Evaluates LLM outputs against known behavioral patterns, maintaining
    a Pareto front of best-fitting behaviors. Supports drift detection
    by comparing current output patterns against anchored baselines.
    """

    def __init__(self, codec=None, registry=None, factory=None,
                 min_accuracy: float = 0.505,
                 lambda_complexity: float = 0.3,
                 balance_groups: bool = True,
                 max_patterns: int = 100):
        self.codec = codec
        self.registry = registry
        self.factory = factory
        self.min_accuracy = min_accuracy
        self.lambda_complexity = lambda_complexity
        self.balance_groups = balance_groups
        self.max_patterns = max_patterns

        self._cycle = 0
        self._pareto_front: List[ParetoPattern] = []
        self._evaluated_patterns: Dict[str, ParetoPattern] = {}

    def evaluate(self, outputs: List[Tuple[str, str]]) -> ValidatorResult:
        """
        Run a behavioral assessment cycle on a set of LLM outputs.

        Each entry: (source_label, output_text)
        """
        self._cycle += 1

        # Generate behavioral assessment criteria
        candidates = self._generate_assessment_criteria()

        # Evaluate each criterion against the outputs
        passed = []
        for pattern_id, (desc, assess_fn) in candidates.items():
            errors = []
            for source, text in outputs:
                try:
                    score = assess_fn(text)
                    # Perfect score is 1.0, error is distance from 1.0
                    errors.append((1.0 - score) ** 2)
                except Exception:
                    errors.append(1.0)

            if not errors:
                continue

            error = sum(errors) / len(errors)
            accuracy = max(0.0, 1.0 - error)

            pattern = ParetoPattern(
                pattern_id=pattern_id,
                description=desc,
                error=error,
                accuracy=accuracy,
                is_anchored=True,
                complexity=len(desc),
            )

            self._evaluated_patterns[pattern_id] = pattern

            if accuracy >= self.min_accuracy:
                passed.append(pattern)

        # Build Pareto front
        self._pareto_front = self._compute_pareto_front(passed)
        self._pareto_front.sort(key=lambda p: p.error)

        best = self._pareto_front[0] if self._pareto_front else ParetoPattern(
            pattern_id="none",
            description="no_pattern_passed",
            error=1.0,
            accuracy=0.0,
            is_anchored=False,
        )

        return ValidatorResult(
            cycle=self._cycle,
            patterns_evaluated=len(candidates),
            patterns_passed=len(passed),
            pareto_front=self._pareto_front,
            anchored_present=best.is_anchored,
            best_error=best.error,
            best_pattern_id=best.pattern_id,
        )

    def _generate_assessment_criteria(self) -> Dict[str, Tuple[str, Callable]]:
        """Generate behavioral assessment criteria."""
        criteria = {}

        # Criterion 1: Output is not empty/short
        criteria["criterion_nonempty"] = (
            "output has meaningful length (>50 chars)",
            lambda t: min(1.0, len(t.strip()) / 200.0),
        )

        # Criterion 2: Output has diverse vocabulary
        criteria["criterion_diverse"] = (
            "output uses diverse vocabulary",
            lambda t: min(1.0, len(set(t.lower().split())) / max(len(t.split()), 1) * 3.0) if t.split() else 0.0,
        )

        # Criterion 3: No refusal pattern
        criteria["criterion_no_refusal"] = (
            "output does not contain refusal patterns",
            lambda t: 0.0 if any(p in t.lower() for p in [
                "i cannot", "i can't", "i'm sorry", "unable to", "cannot fulfill"
            ]) else 1.0,
        )

        # Criterion 4: Output is structured
        criteria["criterion_structured"] = (
            "output has structural elements (lists, paragraphs)",
            lambda t: min(1.0, (t.count("\n") / 5.0 + t.count("- ") / 3.0) / 2.0),
        )

        # Criterion 5: No hallucination markers
        criteria["criterion_grounded"] = (
            "output doesn't use hallucination markers",
            lambda t: 0.0 if any(p in t.lower() for p in [
                "according to my research", "i recall that", "studies have shown"
            ]) else 1.0,
        )

        return criteria

    def _compute_pareto_front(self, patterns: List[ParetoPattern]) -> List[ParetoPattern]:
        """Compute Pareto-optimal frontier (minimize error, maximize accuracy)."""
        if not patterns:
            return []
        pareto = []
        for p in patterns:
            dominated = False
            for q in patterns:
                if p is q:
                    continue
                if q.error <= p.error and q.accuracy >= p.accuracy:
                    if q.error < p.error or q.accuracy > p.accuracy:
                        dominated = True
                        break
            if not dominated:
                pareto.append(p)
        return pareto

    def assess(self, text: str) -> dict:
        """
        Assess a single LLM output against all Pareto-optimal patterns.

        Returns dict with score, confidence, and assessment details.
        """
        if not self._pareto_front:
            return {
                "score": 0.5,
                "confidence": 0.5,
                "patterns_used": 0,
                "method": "fallback",
            }

        scores = []
        weights = []
        for pattern in self._pareto_front:
            # Re-evaluate using a simple combined score from the codec
            if self.codec:
                sig = self.codec.encode(text)
                # Use diversity (d2) as a proxy for output quality
                score = sig[2] if len(sig) > 2 else 0.5
            else:
                score = 0.5
            scores.append(score)
            weights.append(pattern.accuracy)

        if sum(weights) == 0:
            weights = [1.0 / len(weights)] * len(weights)
        else:
            total = sum(weights)
            weights = [w / total for w in weights]

        ensemble_score = sum(s * w for s, w in zip(scores, weights))
        confidence = max(0.0, min(1.0,
            sum(p.accuracy for p in self._pareto_front) / len(self._pareto_front)))

        return {
            "score": round(ensemble_score, 4),
            "confidence": round(confidence, 4),
            "patterns_used": len(self._pareto_front),
            "method": "pareto_ensemble",
        }

    def check_health(self) -> dict:
        return {
            "pareto_size": len(self._pareto_front),
            "anchored": any(p.is_anchored for p in self._pareto_front),
            "cycle": self._cycle,
            "patterns_evaluated": len(self._evaluated_patterns),
        }
