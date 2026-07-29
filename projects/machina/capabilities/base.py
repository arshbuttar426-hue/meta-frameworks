from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class LatencyClass(str, Enum):
    INSTANT = "instant"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class CostClass(str, Enum):
    FREE = "free"
    LOCAL = "local"
    CHEAP = "cheap"
    MODERATE = "moderate"
    EXPENSIVE = "expensive"


class CapabilityStatus(str, Enum):
    DRAFT = "draft"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


@dataclass
class CapabilityIO:
    name: str = ""
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None
    examples: list[str] = field(default_factory=list)


@dataclass
class RetryPolicy:
    max_retries: int = 3
    backoff_base: float = 2.0
    backoff_max: float = 60.0
    retryable_errors: list[str] = field(default_factory=lambda: ["timeout", "rate_limit", "network"])


@dataclass
class CapabilityDeclaration:
    name: str = ""
    description: str = ""
    inputs: list[CapabilityIO] = field(default_factory=list)
    outputs: list[CapabilityIO] = field(default_factory=list)
    latency: LatencyClass = LatencyClass.MEDIUM
    expected_cost: CostClass = CostClass.LOCAL
    offline_support: bool = False
    internet_required: bool = False
    dependencies: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    confidence: float = 0.8
    parallel_safe: bool = True
    cacheable: bool = True
    deterministic: bool = False
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    version: str = "0.1.0"
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    implementation: Any = None

    def validate_inputs(self, inputs: dict) -> list[str]:
        errors = []
        for inp in self.inputs:
            if inp.required and inp.name not in inputs:
                errors.append(f"Missing required input: {inp.name}")
        return errors


@dataclass
class CapabilityRequest:
    capability: str = ""
    inputs: dict = field(default_factory=dict)
    agent: Any = None
    priority: int = 5
    mission_id: Optional[str] = None
    timeout: Optional[float] = None
    cache_ttl: Optional[int] = None


@dataclass
class ExecutionMetadata:
    capability: str = ""
    implementation: str = "unknown"
    start_time: float = 0.0
    duration_ms: Optional[float] = None
    retry_count: int = 0
    error: Optional[str] = None
    cache_hit: bool = False

    def finish(self):
        import time
        self.duration_ms = (time.time() - self.start_time) * 1000


@dataclass
class CapabilityResult:
    success: bool = True
    output: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    cost_estimate: float = 0.0
    metadata: Any = None
    retry_count: int = 0

    @classmethod
    def ok(cls, output: Any) -> CapabilityResult:
        return cls(success=True, output=output)

    @classmethod
    def fail(cls, error: str = "", retry_count: int = 0) -> CapabilityResult:
        return cls(success=False, error=error, retry_count=retry_count)


@dataclass
class CapabilityProfile:
    name: str = ""
    description: str = ""
    allowed_capabilities: list[str] = field(default_factory=list)
    denied_capabilities: list[str] = field(default_factory=list)
    max_priority: int = 5
    rate_limits: dict = field(default_factory=dict)


@dataclass
class PipelineStep:
    capability: str = ""
    inputs: dict = field(default_factory=dict)
    agent: str = ""


@dataclass
class PipelineDefinition:
    name: str = ""
    steps: list[PipelineStep] = field(default_factory=list)


@dataclass
class PipelineResult:
    success: bool = True
    results: list = field(default_factory=list)
    error: Optional[str] = None
