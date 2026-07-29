from __future__ import annotations
import logging

from core.types import AgentRole
from capabilities.registry import CapabilityRegistry
from capabilities.permission import PermissionManager, DEFAULT_PROFILES, CapabilityProfile
from capabilities.execution import ExecutionEngine
from capabilities.scheduler import CapabilityScheduler
from capabilities.metrics import MetricsCollector
from capabilities.pipeline import PipelineBuilder
from capabilities.discovery import auto_discover

logger = logging.getLogger(__name__)


def initialize_system(registry: Optional[CapabilityRegistry] = None,
                      auto_load: bool = True,
                      chain_config: Optional[dict] = None) -> dict:
    if registry is None:
        registry = CapabilityRegistry()

    if auto_load:
        auto_discover(registry=registry)

    metrics = MetricsCollector()
    permissions = PermissionManager()
    engine = ExecutionEngine(registry, metrics)
    scheduler = CapabilityScheduler(registry, permissions, engine)
    pipeline = PipelineBuilder(scheduler)

    for name, profile in DEFAULT_PROFILES.items():
        permissions.add_profile(profile)

    # Use chain config if provided, otherwise use optimized defaults
    if chain_config:
        extractor = chain_config.get("extractor", "phi4_mini_reviewer")
        creative = chain_config.get("creative", "smolm3_research_associate")
        reviewer = chain_config.get("reviewer", "phi4_mini_reviewer")
        synthesizer = chain_config.get("synthesizer", "gemma_composer")
    else:
        # Optimized chain: Phi-4 (extract/review), SmolLM3 (creative), Gemma (synthesize)
        extractor = "phi4_mini_reviewer"
        creative = "smolm3_research_associate"
        reviewer = "phi4_mini_reviewer"
        synthesizer = "gemma_composer"

    # Assign models to chain roles
    permissions.assign_agent(extractor, "ra")
    permissions.assign_agent(creative, "creative")
    permissions.assign_agent(reviewer, "reviewer")
    permissions.assign_agent(synthesizer, "pi")

    logger.info(
        f"Capability system initialized: "
        f"{registry.count()} capabilities, "
        f"{len(permissions._profiles)} profiles, "
        f"{len(permissions._agent_assignments)} agents assigned"
    )

    return {
        "registry": registry,
        "metrics": metrics,
        "permissions": permissions,
        "engine": engine,
        "scheduler": scheduler,
        "pipeline": pipeline,
    }
