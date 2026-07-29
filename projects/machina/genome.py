from __future__ import annotations
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from core.types import AgentRole, MissionStatus


class Modality(str, Enum):
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    TABLE = "table"
    GRAPH = "graph"
    MATH = "math"
    STRUCTURED = "structured"


class ReasoningDepth(str, Enum):
    SHALLOW = "shallow"
    MODERATE = "moderate"
    DEEP = "deep"
    MULTI_STEP = "multi_step"


@dataclass
class AgentGenome:
    agent_id: str = ""
    role: AgentRole = AgentRole.GEMMA
    model_name: str = ""
    model_size_gb: float = 0.0
    context_size: int = 4096
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    preferred_domains: list[str] = field(default_factory=list)
    supported_modalities: list[Modality] = field(default_factory=lambda: [Modality.TEXT])
    reasoning_depth: ReasoningDepth = ReasoningDepth.MODERATE
    average_latency_ms: float = 0.0
    memory_usage_mb: float = 0.0
    available_capabilities: list[str] = field(default_factory=list)
    reliability_score: float = 0.5
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    hallucination_count: int = 0
    human_overrides: int = 0
    last_active: str = field(default_factory=lambda: _now())
    version: str = "0.1.0"

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.5
        return self.successful_tasks / self.total_tasks

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> AgentGenome:
        if "role" in d and isinstance(d["role"], str):
            d["role"] = AgentRole(d["role"])
        if "supported_modalities" in d:
            d["supported_modalities"] = [
                Modality(m) if isinstance(m, str) else m
                for m in d["supported_modalities"]
            ]
        if "reasoning_depth" in d and isinstance(d["reasoning_depth"], str):
            d["reasoning_depth"] = ReasoningDepth(d["reasoning_depth"])
        return cls(**d)


@dataclass
class MissionGenome:
    mission_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    objective: str = ""
    scope: str = ""
    constraints: list[str] = field(default_factory=list)
    required_confidence: float = 0.7
    allowed_capabilities: list[str] = field(default_factory=list)
    required_evidence: int = 0
    budget: str = "unlimited"
    priority: int = 5
    deadline: Optional[str] = None
    current_state: str = "created"
    next_state: str = "planning"
    blocking_dependencies: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    owner: str = "runtime"
    application: str = "generic"
    created_at: str = field(default_factory=lambda: _now())
    updated_at: str = field(default_factory=lambda: _now())
    completed_at: Optional[str] = None
    version: str = "0.1.0"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> MissionGenome:
        return cls(**d)

    def transition(self, new_state: str) -> None:
        self.current_state = new_state
        self.updated_at = _now()

    def complete(self) -> None:
        self.current_state = "completed"
        self.next_state = "none"
        self.completed_at = _now()
        self.updated_at = _now()


@dataclass
class TaskAssignment:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mission_id: str = ""
    capability: str = ""
    agent_role: Optional[AgentRole] = None
    inputs: dict = field(default_factory=dict)
    priority: int = 5
    status: str = "pending"
    confidence_threshold: float = 0.7
    retry_count: int = 0
    max_retries: int = 3
    assigned_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_summary: str = ""
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: _now())

    def to_dict(self) -> dict:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
