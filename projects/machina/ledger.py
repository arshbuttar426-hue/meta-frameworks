from __future__ import annotations
import hashlib
import json
import uuid
from typing import Any, Optional

from research_runtime.persistence import RuntimeStore


class EvidenceLedger:
    def __init__(self, store: RuntimeStore):
        self.store = store

    def record(self, mission_id: str, claim: str, source: str,
               agent: str, confidence: float = 0.0,
               url: Optional[str] = None,
               extraction_method: str = "unknown",
               related_evidence: Optional[list[str]] = None,
               claim_ids: Optional[list[str]] = None) -> dict:
        evidence_id = str(uuid.uuid4())
        content_hash = hashlib.sha256(claim.encode()).hexdigest()
        record = {
            "evidence_id": evidence_id,
            "mission_id": mission_id,
            "claim": claim,
            "source": source,
            "url": url,
            "confidence": confidence,
            "extraction_method": extraction_method,
            "verification_status": "unverified",
            "related_evidence": json.dumps(related_evidence or []),
            "claim_ids": json.dumps(claim_ids or []),
            "content_hash": content_hash,
            "agent": agent,
        }
        self.store.save_evidence(record)
        return record

    def get(self, evidence_id: str) -> Optional[dict]:
        return self.store.get_evidence(evidence_id)

    def list(self, mission_id: str) -> list[dict]:
        return self.store.list_evidence(mission_id)

    def verify(self, evidence_id: str, status: str) -> None:
        evidence = self.store.get_evidence(evidence_id)
        if evidence:
            evidence["verification_status"] = status
            self.store.save_evidence(evidence)

    def verify_multiple(self, evidence_ids: list[str]) -> dict:
        results = {}
        for eid in evidence_ids:
            evidence = self.store.get_evidence(eid)
            if not evidence:
                results[eid] = {"status": "not_found"}
                continue
            if evidence.get("verification_status") != "verified":
                evidence["verification_status"] = "verified"
                self.store.save_evidence(evidence)
                results[eid] = {"status": "verified"}
            else:
                results[eid] = {"status": "already_verified"}
        return results

    def search_by_confidence(self, mission_id: str,
                             min_confidence: float = 0.0) -> list[dict]:
        all_evidence = self.store.list_evidence(mission_id)
        return [e for e in all_evidence if e.get("confidence", 0) >= min_confidence]

    def summary(self, mission_id: str) -> dict:
        entries = self.store.list_evidence(mission_id)
        verified = sum(1 for e in entries if e.get("verification_status") == "verified")
        unverified = sum(1 for e in entries if e.get("verification_status") == "unverified")
        disputed = sum(1 for e in entries if e.get("verification_status") == "disputed")
        avg_conf = (
            sum(e.get("confidence", 0) for e in entries) / len(entries)
            if entries else 0.0
        )
        source_counts = {}
        for e in entries:
            src = e.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1
        return {
            "mission_id": mission_id,
            "total_evidence": len(entries),
            "verified": verified,
            "unverified": unverified,
            "disputed": disputed,
            "avg_confidence": round(avg_conf, 3),
            "sources": source_counts,
        }

    def search(self, mission_id: str, query: str) -> list[dict]:
        entries = self.store.list_evidence(mission_id)
        q = query.lower()
        return [
            e for e in entries
            if q in e.get("claim", "").lower()
            or q in e.get("source", "").lower()
            or q in e.get("agent", "").lower()
        ]
