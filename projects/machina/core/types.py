from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid


class AgentRole(str, Enum):
    GEMMA = "gemma"
    SMOLM3 = "smolm3"
    PHI4 = "phi4"
    VIBE = "vibe"
    HUMAN = "human"
    SYSTEM = "system"
    ANARCHIST = "anarchist"


class MissionStatus(str, Enum):
    DRAFT = "draft"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    UNDER_REVIEW = "under_review"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResearchGrade(str, Enum):
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    PEER_REVIEWED = "peer_reviewed"
    PREPRINTED = "preprinted"
    HYPOTHESIS = "hypothesis"
    SPECULATIVE = "speculative"
    CONTRADICTED = "contradicted"
    OBSERVED = "observed"


class ClaimType(str, Enum):
    FACT = "fact"
    OPINION = "opinion"
    INTERPRETATION = "interpretation"
    SPECULATION = "speculation"
    DEFINITION = "definition"


class EvidenceLevel(str, Enum):
    SINGLE_SOURCE = "single_source"
    MULTIPLE_SOURCES = "multiple_sources"
    PEER_REVIEWED = "peer_reviewed"
    DIRECT_EXPERIMENT = "direct_experiment"
    META_ANALYSIS = "meta_analysis"
    EXPERT_CONSENSUS = "expert_consensus"
    HISTORICAL_RECORD = "historical_record"


class CapabilityStatus(str, Enum):
    DRAFT = "draft"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


@dataclass
class Citation:
    source_id: str = field(default_factory=_uid)
    source_url: Optional[str] = None
    source_title: str = ""
    retrieved_at: Optional[str] = None
    content_hash: Optional[str] = None


@dataclass
class KnowledgeNode:
    node_id: str = field(default_factory=_uid)
    label: str = ""
    node_type: str = "concept"
    attributes: dict = field(default_factory=dict)
    confidence: float = 0.0
    grade: ResearchGrade = ResearchGrade.UNKNOWN
    timestamp: str = field(default_factory=_now)


@dataclass
class KnowledgeEdge:
    edge_id: str = field(default_factory=_uid)
    source_id: str = ""
    target_id: str = ""
    relation: str = ""
    weight: float = 1.0
    evidence_ids: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)


@dataclass
class Claim:
    claim_id: str = field(default_factory=_uid)
    statement: str = ""
    claim_type: ClaimType = ClaimType.FACT
    confidence: float = 0.0
    grade: ResearchGrade = ResearchGrade.UNKNOWN
    evidence_ids: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    source_agent: Optional[AgentRole] = None
    timestamp: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)


@dataclass
class Evidence:
    claim_id: str = ""
    source: Citation = field(default_factory=Citation)
    confidence: float = 0.0
    evidence_level: EvidenceLevel = EvidenceLevel.SINGLE_SOURCE
    reasoning_chain: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    supporting: bool = True
    agent_id: AgentRole = AgentRole.SMOLM3
    timestamp: str = field(default_factory=_now)


@dataclass
class Hypothesis:
    hypothesis_id: str = field(default_factory=_uid)
    statement: str = ""
    grade: ResearchGrade = ResearchGrade.HYPOTHESIS
    supporting_claims: list[str] = field(default_factory=list)
    contradicting_claims: list[str] = field(default_factory=list)
    confidence: float = 0.0
    proposed_by: AgentRole = AgentRole.GEMMA
    timestamp: str = field(default_factory=_now)


@dataclass
class Mission:
    mission_id: str = field(default_factory=_uid)
    objective: str = ""
    scope: str = ""
    deadline: Optional[str] = None
    confidence_target: float = 0.8
    allowed_sources: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    status: MissionStatus = MissionStatus.DRAFT
    assigned_agents: list[AgentRole] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    parent_question: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    completed_at: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = MissionStatus(self.status)


@dataclass
class JournalEntry:
    entry_id: str = field(default_factory=_uid)
    timestamp: str = field(default_factory=_now)
    agent: AgentRole = AgentRole.GEMMA
    action: str = ""
    reason: str = ""
    input_summary: str = ""
    output_summary: str = ""
    confidence: float = 0.0
    sources: list[str] = field(default_factory=list)
    next_action: str = ""
    mission_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ResearchNote:
    note_id: str = field(default_factory=_uid)
    mission_id: Optional[str] = None
    title: str = ""
    content: str = ""
    agent: AgentRole = AgentRole.GEMMA
    tags: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)


@dataclass
class PaperDraft:
    paper_id: str = field(default_factory=_uid)
    mission_id: Optional[str] = None
    title: str = ""
    abstract: str = ""
    sections: dict = field(default_factory=dict)
    citations: list[str] = field(default_factory=list)
    authors: list[AgentRole] = field(default_factory=list)
    status: str = "draft"
    confidence: float = 0.0
    grade: ResearchGrade = ResearchGrade.UNKNOWN
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    reviewer_approved: bool = False


@dataclass
class DebateRound:
    round_number: int = 0
    proposal: str = ""
    evidence_summary: str = ""
    critique: str = ""
    alternative: str = ""
    revision: str = ""
    confidence: float = 0.0
    agreement: bool = False
    timestamp: str = field(default_factory=_now)


def extract_string(obj) -> str:
    if obj is None:
        return ""
    if hasattr(obj, "value"):
        return str(obj.value)
    return str(obj)
