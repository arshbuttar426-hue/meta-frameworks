from __future__ import annotations
import uuid
from typing import Any, Optional

from research_runtime.persistence import RuntimeStore


class ReflectionEngine:
    def __init__(self, store: RuntimeStore):
        self.store = store

    def analyze_gaps(self, mission_id: str, current_evidence: list[dict],
                     required_evidence_count: int) -> list[dict]:
        findings = []
        if len(current_evidence) < required_evidence_count:
            missing = required_evidence_count - len(current_evidence)
            finding = (
                f"Evidence gap: have {len(current_evidence)}, "
                f"need {required_evidence_count} ({missing} missing)"
            )
            reflection_id = str(uuid.uuid4())
            self.store.save_reflection(
                reflection_id=reflection_id,
                mission_id=mission_id,
                analysis_type="evidence_gap",
                finding=finding,
                severity="warning",
            )
            findings.append({
                "reflection_id": reflection_id,
                "type": "evidence_gap",
                "finding": finding,
                "severity": "warning",
            })
        return findings

    def analyze_confidence(self, mission_id: str,
                           evidence: list[dict]) -> list[dict]:
        findings = []
        low_conf = [e for e in evidence if e.get("confidence", 1.0) < 0.6]
        if low_conf:
            finding = (
                f"Confidence concern: {len(low_conf)} evidence entries "
                f"have confidence below 0.6"
            )
            reflection_id = str(uuid.uuid4())
            self.store.save_reflection(
                reflection_id=reflection_id,
                mission_id=mission_id,
                analysis_type="confidence",
                finding=finding,
                severity="warning",
            )
            findings.append({
                "reflection_id": reflection_id,
                "type": "confidence",
                "finding": finding,
                "severity": "warning",
            })
        return findings

    def analyze_consensus(self, mission_id: str,
                          evidence: list[dict],
                          debate_results: Optional[list[dict]] = None) -> list[dict]:
        findings = []
        sources = set(e.get("source", "unknown") for e in evidence)
        if len(sources) < 2 and len(evidence) > 0:
            finding = (
                f"Source diversity concern: only {len(sources)} unique "
                f"source(s) among {len(evidence)} evidence entries"
            )
            reflection_id = str(uuid.uuid4())
            self.store.save_reflection(
                reflection_id=reflection_id,
                mission_id=mission_id,
                analysis_type="source_diversity",
                finding=finding,
                severity="info",
            )
            findings.append({
                "reflection_id": reflection_id,
                "type": "source_diversity",
                "finding": finding,
                "severity": "info",
            })

        if debate_results:
            final_conf = [
                r.get("confidence", 0.0) for r in debate_results
                if r.get("step") == "conclusion"
            ]
            if final_conf and min(final_conf) < 0.5:
                finding = "Debate consensus below 0.5 — conclusions may be unreliable"
                rid = str(uuid.uuid4())
                self.store.save_reflection(
                    reflection_id=rid,
                    mission_id=mission_id,
                    analysis_type="debate_consensus",
                    finding=finding,
                    severity="critical",
                )
                findings.append({
                    "reflection_id": rid,
                    "type": "debate_consensus",
                    "finding": finding,
                    "severity": "critical",
                })
        return findings

    def analyze_contradictions(self, mission_id: str,
                                evidence: list[dict]) -> list[dict]:
        findings = []
        claims_by_content: dict[str, list[dict]] = {}
        for e in evidence:
            claim = e.get("claim", "").strip().lower()
            if not claim:
                continue
            words = set(claim.split())
            for key, group in claims_by_content.items():
                key_words = set(key.split())
                overlap = words & key_words
                if len(overlap) >= 3 and len(group) > 0:
                    direction_1 = _sentiment_sign(group[0].get("claim", ""))
                    direction_2 = _sentiment_sign(e.get("claim", ""))
                    if direction_1 and direction_2 and direction_1 != direction_2:
                        finding = (
                            f"Possible contradiction detected between "
                            f"{group[0].get('evidence_id', 'unknown')} and "
                            f"{e.get('evidence_id', 'unknown')}"
                        )
                        rid = str(uuid.uuid4())
                        self.store.save_reflection(
                            reflection_id=rid,
                            mission_id=mission_id,
                            analysis_type="contradiction",
                            finding=finding,
                            severity="warning",
                        )
                        findings.append({
                            "reflection_id": rid,
                            "type": "contradiction",
                            "finding": finding,
                            "severity": "warning",
                        })
                        break
            claims_by_content.setdefault(claim, []).append(e)
        return findings

    def full_analysis(self, mission_id: str,
                      evidence: list[dict],
                      required_evidence_count: int = 0,
                      debate_results: Optional[list[dict]] = None) -> list[dict]:
        all_findings = []
        all_findings.extend(
            self.analyze_gaps(mission_id, evidence, required_evidence_count)
        )
        all_findings.extend(
            self.analyze_confidence(mission_id, evidence)
        )
        all_findings.extend(
            self.analyze_consensus(mission_id, evidence, debate_results)
        )
        all_findings.extend(
            self.analyze_contradictions(mission_id, evidence)
        )
        return all_findings

    def list_reflections(self, mission_id: str) -> list[dict]:
        return self.store.list_reflections(mission_id)


def _sentiment_sign(text: str) -> Optional[bool]:
    positive = {"yes", "true", "supports", "confirms", "validates", "proves", "agrees"}
    negative = {"no", "false", "contradicts", "refutes", "disagrees", "invalidates"}
    words = text.lower().split()
    for w in words:
        if w in positive:
            return True
        if w in negative:
            return False
    return None
