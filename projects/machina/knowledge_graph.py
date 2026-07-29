from __future__ import annotations
from typing import Optional
from core.types import KnowledgeNode, KnowledgeEdge, ResearchGrade
from memory.store import Store


class KnowledgeGraph:
    def __init__(self, store: Store):
        self.store = store

    def add_node(self, label: str, node_type: str = "concept",
                 attributes: dict | None = None,
                 confidence: float = 0.0,
                 grade: ResearchGrade = ResearchGrade.UNKNOWN) -> KnowledgeNode:
        node = KnowledgeNode(
            label=label,
            node_type=node_type,
            attributes=attributes or {},
            confidence=confidence,
            grade=grade,
        )
        self.store.save_node(node)
        return node

    def add_edge(self, source_id: str, target_id: str, relation: str,
                 weight: float = 1.0) -> KnowledgeEdge:
        edge = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
        )
        self.store.save_edge(edge)
        return edge

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        nodes, _ = self.store.get_graph()
        for n in nodes:
            if n.node_id == node_id:
                return n
        return None

    def find_nodes(self, label_substr: str) -> list[KnowledgeNode]:
        nodes, _ = self.store.get_graph()
        return [n for n in nodes if label_substr.lower() in n.label.lower()]

    def get_connections(self, node_id: str) -> list[tuple[KnowledgeEdge, KnowledgeNode]]:
        _, edges = self.store.get_graph()
        result = []
        for e in edges:
            if e.source_id == node_id:
                target = self.get_node(e.target_id)
                if target:
                    result.append((e, target))
            elif e.target_id == node_id:
                source = self.get_node(e.source_id)
                if source:
                    result.append((e, source))
        return result

    def to_dict(self) -> dict:
        nodes, edges = self.store.get_graph()
        return {
            "nodes": [
                {"id": n.node_id, "label": n.label, "type": n.node_type,
                 "confidence": n.confidence, "grade": n.grade.value}
                for n in nodes
            ],
            "edges": [
                {"source": e.source_id, "target": e.target_id,
                 "relation": e.relation, "weight": e.weight}
                for e in edges
            ],
        }

    def summary(self) -> str:
        nodes, edges = self.store.get_graph()
        return f"Knowledge Graph: {len(nodes)} nodes, {len(edges)} edges"
