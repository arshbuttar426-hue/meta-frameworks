from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SetPoint:
    field_name: str
    value: Any
    tolerance: float
    correction_strength: float


@dataclass
class DriftCorrection:
    field: str
    expected: Any
    measured: Any
    correction: str


class ContinuityHomeostat:
    def __init__(self):
        self.set_points: dict[str, SetPoint] = {}
        self.correction_history: list[DriftCorrection] = []
        self.segment_counter: int = 0

    def establish_set_points(self, evidence_entries: list[dict]) -> None:
        if not evidence_entries:
            return
        claim_texts = [
            e.get("claim", "") for e in evidence_entries if e.get("claim")
        ]
        if claim_texts:
            consensus = self._find_consensus_claim(claim_texts)
            self.set_points["primary_claim"] = SetPoint(
                field_name="primary_claim", value=consensus,
                tolerance=0.0, correction_strength=10.0,
            )
        confidences = [
            e.get("confidence", 0.5) for e in evidence_entries
            if isinstance(e.get("confidence"), (int, float))
        ]
        if confidences:
            self.set_points["confidence_baseline"] = SetPoint(
                field_name="confidence_baseline",
                value=statistics.median(confidences),
                tolerance=0.3, correction_strength=2.0,
            )
        source_types = [
            e.get("extraction_method", "") for e in evidence_entries
            if e.get("extraction_method")
        ]
        if source_types:
            dominant = max(set(source_types), key=source_types.count)
            self.set_points["source_type"] = SetPoint(
                field_name="source_type", value=dominant,
                tolerance=float("inf"), correction_strength=0.0,
            )

    def measure_and_correct(self, output: dict) -> dict:
        self.segment_counter += 1
        corrections: list[str] = []

        for prop_name, set_point in self.set_points.items():
            measured = output.get(prop_name)
            if measured is None:
                continue
            deviation = self._deviation(measured, set_point.value)
            if abs(deviation) > set_point.tolerance and self.segment_counter > 2:
                correction_text = (
                    f"[CORRECTION] {prop_name}: "
                    f"'{measured}' → '{set_point.value}'"
                )
                corrections.append(correction_text)
                self.correction_history.append(DriftCorrection(
                    field=prop_name, expected=set_point.value,
                    measured=measured, correction=correction_text,
                ))
                if set_point.correction_strength > 0:
                    output[prop_name] = set_point.value

        output["_corrections"] = corrections
        return output

    def deviation_count(self) -> int:
        return len(self.correction_history)

    def _find_consensus_claim(self, claim_texts: list[str]) -> str:
        if not claim_texts:
            return ""
        word_scores: dict[str, int] = {}
        for text in claim_texts:
            seen = set()
            for w in text.lower().split():
                if len(w) > 3 and w not in seen:
                    word_scores[w] = word_scores.get(w, 0) + 1
                    seen.add(w)
        if not word_scores:
            return claim_texts[0]
        best_word = max(word_scores, key=word_scores.get)
        for text in claim_texts:
            if best_word in text.lower():
                return text
        return claim_texts[0]

    @staticmethod
    def _deviation(measured: Any, expected: Any) -> float:
        if isinstance(measured, (int, float)) and isinstance(expected, (int, float)):
            return measured - expected
        return 0.0 if measured == expected else 1.0
