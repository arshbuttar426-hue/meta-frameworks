from __future__ import annotations
import hashlib
import uuid
from typing import Any, Optional

from research_runtime.persistence import RuntimeStore


class KnowledgeAutoConnector:
    RELATION_TYPES = {
        "contradicts": -1.0,
        "refines": 0.3,
        "supports": 0.7,
        "confirms": 0.9,
        "derived_from": 0.8,
        "extends": 0.5,
        "unrelated": 0.0,
    }

    def __init__(self, store: RuntimeStore):
        self.store = store

    def connect_evidence_to_claim(self, evidence_id: str, claim_id: str,
                                   relation: str = "supports",
                                   weight: float | None = None) -> str:
        if relation not in self.RELATION_TYPES:
            raise ValueError(f"Unknown relation: {relation}")
        weight = weight or self.RELATION_TYPES[relation]
        link_id = str(uuid.uuid4())
        self.store.save_knowledge_link(
            link_id=link_id,
            source_type="evidence",
            source_id=evidence_id,
            target_type="claim",
            target_id=claim_id,
            relation=relation,
            weight=weight,
            auto_generated=True,
        )
        return link_id

    def connect_mission_to_evidence(self, mission_id: str,
                                     evidence_id: str,
                                     relation: str = "derived_from") -> str:
        link_id = str(uuid.uuid4())
        self.store.save_knowledge_link(
            link_id=link_id,
            source_type="mission",
            source_id=mission_id,
            target_type="evidence",
            target_id=evidence_id,
            relation=relation,
            weight=self.RELATION_TYPES.get(relation, 0.5),
            auto_generated=True,
        )
        return link_id

    def connect_journal_to_evidence(self, journal_id: str,
                                     evidence_id: str) -> str:
        link_id = str(uuid.uuid4())
        self.store.save_knowledge_link(
            link_id=link_id,
            source_type="journal",
            source_id=journal_id,
            target_type="evidence",
            target_id=evidence_id,
            relation="references",
            weight=0.6,
            auto_generated=True,
        )
        return link_id

    def auto_link_evidence(self, evidence_entries: list[dict]) -> list[dict]:
        links = []
        for i, e1 in enumerate(evidence_entries):
            for j, e2 in enumerate(evidence_entries):
                if j <= i:
                    continue
                relation, weight = self._infer_relation(e1, e2)
                if relation == "unrelated":
                    continue
                link_id = self.connect_evidence_to_claim(
                    evidence_id=e1.get("evidence_id", ""),
                    claim_id=e2.get("evidence_id", ""),
                    relation=relation,
                    weight=weight,
                )
                links.append({
                    "link_id": link_id,
                    "source": e1.get("evidence_id", ""),
                    "target": e2.get("evidence_id", ""),
                    "relation": relation,
                })
        return links

    def query(self, entity_type: Optional[str] = None,
               entity_id: Optional[str] = None) -> list[dict]:
        return self.store.query_knowledge_links(entity_type, entity_id)

    def graph_summary(self) -> dict:
        links = self.store.query_knowledge_links()
        if not links:
            return {"total_links": 0, "by_relation": {}}
        by_relation: dict[str, int] = {}
        entities: set[str] = set()
        for link in links:
            rel = link.get("relation", "unknown")
            by_relation[rel] = by_relation.get(rel, 0) + 1
            entities.add(link.get("source_id", ""))
            entities.add(link.get("target_id", ""))
        return {
            "total_links": len(links),
            "unique_entities": len(entities),
            "by_relation": by_relation,
        }

    def _infer_relation(self, e1: dict, e2: dict) -> tuple[str, float]:
        c1 = e1.get("claim", "").lower()
        c2 = e2.get("claim", "").lower()
        if not c1 or not c2:
            return ("unrelated", 0.0)

        words_1 = set(c1.split())
        words_2 = set(c2.split())
        overlap = words_1 & words_2

        if len(overlap) >= 5:
            return ("confirms", 0.9)
        elif len(overlap) >= 3:
            return ("supports", 0.7)
        elif len(overlap) >= 1:
            return ("refines", 0.3)
        else:
            return ("unrelated", 0.0)

    def compute_knowledge_graph_links(self) -> list[dict]:
        missions = self.store.list_mission_genomes()
        all_links = []
        for mission in missions:
            evidence = self.store.list_evidence(mission.mission_id)
            auto_links = self.auto_link_evidence(evidence)
            all_links.extend(auto_links)
        return all_links
