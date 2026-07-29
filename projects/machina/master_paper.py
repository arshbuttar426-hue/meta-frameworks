from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class PaperSection:
    heading: str
    content: str
    evidence_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    sub_sections: list[PaperSection] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "heading": self.heading,
            "content": self.content,
            "evidence_ids": self.evidence_ids,
            "confidence": self.confidence,
            "sub_sections": [s.to_dict() for s in self.sub_sections],
        }

    @classmethod
    def from_dict(cls, d: dict) -> PaperSection:
        return cls(
            heading=d.get("heading", ""),
            content=d.get("content", ""),
            evidence_ids=d.get("evidence_ids", []),
            confidence=d.get("confidence", 0.0),
            sub_sections=[cls.from_dict(s) for s in d.get("sub_sections", [])],
        )


@dataclass
class MasterPaper:
    paper_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str = ""
    title: str = ""
    abstract: str = ""
    sections: list[PaperSection] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    overall_confidence: float = 0.0
    version: str = "1.0.0"
    status: str = "draft"
    debate_consensus: float = 0.0
    reflection_count: int = 0
    author_agents: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: _now())
    updated_at: str = field(default_factory=lambda: _now())

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "mission_id": self.mission_id,
            "title": self.title,
            "abstract": self.abstract,
            "sections": [s.to_dict() for s in self.sections],
            "evidence_refs": self.evidence_refs,
            "overall_confidence": self.overall_confidence,
            "version": self.version,
            "status": self.status,
            "debate_consensus": self.debate_consensus,
            "reflection_count": self.reflection_count,
            "author_agents": self.author_agents,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MasterPaper:
        return cls(
            paper_id=d.get("paper_id", ""),
            mission_id=d.get("mission_id", ""),
            title=d.get("title", ""),
            abstract=d.get("abstract", ""),
            sections=[PaperSection.from_dict(s) for s in d.get("sections", [])],
            evidence_refs=d.get("evidence_refs", []),
            overall_confidence=d.get("overall_confidence", 0.0),
            version=d.get("version", "1.0.0"),
            status=d.get("status", "draft"),
            debate_consensus=d.get("debate_consensus", 0.0),
            reflection_count=d.get("reflection_count", 0),
            author_agents=d.get("author_agents", []),
            tags=d.get("tags", []),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

    def render_markdown(self) -> str:
        lines = [f"# {self.title}", "", self.abstract, ""]
        for section in self.sections:
            lines.append(f"## {section.heading}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            if section.evidence_ids:
                lines.append(f"*Evidence: {len(section.evidence_ids)} references*")
                lines.append("")
            if section.confidence > 0:
                lines.append(f"*Section confidence: {section.confidence:.2f}*")
                lines.append("")
            for sub in section.sub_sections:
                lines.append(f"### {sub.heading}")
                lines.append("")
                lines.append(sub.content)
                lines.append("")
        lines.append("---")
        lines.append(f"**Overall confidence:** {self.overall_confidence:.2f}")
        lines.append(f"**Debate consensus:** {self.debate_consensus:.2f}")
        lines.append(f"**Evidence items:** {len(self.evidence_refs)}")
        lines.append(f"**Status:** {self.status}")
        lines.append(f"**Version:** {self.version}")
        lines.append(f"**Generated:** {self.created_at}")
        return "\n".join(lines)


class MasterPaperCompiler:
    def __init__(self):
        pass

    def compile(self, mission_id: str, title: str,
                sections: list[PaperSection],
                evidence_ids: list[str],
                overall_confidence: float,
                debate_consensus: float,
                reflection_count: int,
                author_agents: list[str],
                tags: list[str] | None = None,
                abstract: str = "") -> MasterPaper:
        paper = MasterPaper(
            mission_id=mission_id,
            title=title,
            abstract=abstract,
            sections=sections,
            evidence_refs=evidence_ids,
            overall_confidence=overall_confidence,
            debate_consensus=debate_consensus,
            reflection_count=reflection_count,
            author_agents=author_agents or [],
            tags=tags or [],
        )
        return paper

    def compute_confidence(self, sections: list[PaperSection]) -> float:
        if not sections:
            return 0.0
        scores = [s.confidence for s in sections if s.confidence > 0]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
