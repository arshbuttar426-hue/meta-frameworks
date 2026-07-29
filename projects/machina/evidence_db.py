from __future__ import annotations
from typing import Optional
from core.types import Evidence, Claim, ClaimType, ResearchGrade, Citation, EvidenceLevel, AgentRole
from memory.store import Store


class EvidenceDB:
    def __init__(self, store: Store):
        self.store = store

    def record_claim(self, statement: str, claim_type: ClaimType = ClaimType.FACT,
                     source_agent: Optional[AgentRole] = None) -> Claim:
        claim = Claim(
            statement=statement,
            claim_type=claim_type,
            source_agent=source_agent,
        )
        self.store.save_claim(claim)
        return claim

    def add_evidence(self, claim_id: str, source: Citation,
                     confidence: float, evidence_level: EvidenceLevel,
                     reasoning_chain: list[str],
                     unknowns: list[str] | None = None,
                     assumptions: list[str] | None = None,
                     supporting: bool = True,
                     agent_id: AgentRole = AgentRole.SMOLM3) -> Evidence:
        evidence = Evidence(
            claim_id=claim_id,
            source=source,
            confidence=confidence,
            evidence_level=evidence_level,
            reasoning_chain=reasoning_chain,
            unknowns=unknowns or [],
            assumptions=assumptions or [],
            supporting=supporting,
            agent_id=agent_id,
        )
        self.store.save_evidence(evidence)
        claim = self.store.get_claim(claim_id)
        if claim:
            if evidence.evidence_id not in claim.evidence_ids:
                claim.evidence_ids.append(source.source_id)
                claim.confidence = self._recompute_confidence(claim.claim_id)
                self.store.save_claim(claim)
        return evidence

    def get_evidence(self, claim_id: str) -> list[Evidence]:
        return self.store.get_evidence_for_claim(claim_id)

    def _recompute_confidence(self, claim_id: str) -> float:
        evidences = self.store.get_evidence_for_claim(claim_id)
        if not evidences:
            return 0.0
        scores = [e.confidence for e in evidences]
        return sum(scores) / len(scores)

    def search(self, query: str) -> list[Claim]:
        return self.store.search_claims(query)

    def get_contradictions(self, claim_id: str) -> list[Evidence]:
        claim = self.store.get_claim(claim_id)
        if not claim:
            return []
        all_evidence = []
        for cid in claim.contradictions:
            all_evidence.extend(self.store.get_evidence_for_claim(cid))
        return all_evidence

    def summarize_claim(self, claim_id: str) -> dict:
        claim = self.store.get_claim(claim_id)
        if not claim:
            return {"error": "claim not found"}
        evidence = self.store.get_evidence_for_claim(claim_id)
        return {
            "claim_id": claim.claim_id,
            "statement": claim.statement,
            "confidence": claim.confidence,
            "grade": claim.grade.value,
            "evidence_count": len(evidence),
            "avg_evidence_confidence": (
                sum(e.confidence for e in evidence) / len(evidence)
            ) if evidence else 0,
            "assumptions": list({
                a for e in evidence for a in e.assumptions
            }),
            "unknowns": list({
                u for e in evidence for u in e.unknowns
            }),
        }
