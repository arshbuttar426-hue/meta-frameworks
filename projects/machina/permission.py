from __future__ import annotations
import logging
from typing import Optional

from core.types import AgentRole
from capabilities.base import CapabilityProfile, CapabilityRequest, CapabilityResult

logger = logging.getLogger(__name__)


class PermissionManager:
    def __init__(self):
        self._profiles: dict[str, CapabilityProfile] = {}
        self._agent_assignments: dict[str, str] = {}

    def add_profile(self, profile: CapabilityProfile) -> None:
        self._profiles[profile.name] = profile
        logger.info(f"Permission profile added: {profile.name} "
                     f"({len(profile.allowed_capabilities)} capabilities)")

    def assign_agent(self, agent: str, profile_name: str) -> None:
        if profile_name not in self._profiles:
            raise ValueError(f"Unknown profile: {profile_name}")
        self._agent_assignments[agent] = profile_name
        logger.info(f"Assigned {agent} -> profile '{profile_name}'")

    def get_profile(self, agent: str) -> Optional[CapabilityProfile]:
        profile_name = self._agent_assignments.get(agent)
        if not profile_name:
            return None
        return self._profiles.get(profile_name)

    def check(self, request: CapabilityRequest) -> tuple[bool, Optional[str]]:
        agent_key = request.agent.value if hasattr(request.agent, 'value') else str(request.agent)
        profile = self.get_profile(agent_key)
        if profile is None:
            return False, f"No permission profile for agent {agent_key}"

        cap = request.capability
        name = profile.name

        if cap in profile.denied_capabilities:
            return False, f"Capability '{cap}' explicitly denied for profile '{name}'"

        if profile.allowed_capabilities:
            if "*" in profile.allowed_capabilities:
                pass
            elif cap not in profile.allowed_capabilities:
                return False, f"Capability '{cap}' not in allowed list for profile '{name}'"

        if request.priority > profile.max_priority:
            return False, f"Priority {request.priority} exceeds max {profile.max_priority} for profile '{name}'"

        return True, None

    def can_use(self, agent: str, capability: str) -> bool:
        req = CapabilityRequest(capability=capability, inputs={}, agent=agent)
        allowed, _ = self.check(req)
        return allowed

    def list_allowed(self, agent: str) -> list[str]:
        profile = self.get_profile(agent)
        if profile is None:
            return []
        return profile.allowed_capabilities[:]

    def deny_for(self, agent: str, capability: str) -> None:
        profile = self.get_profile(agent)
        if profile:
            if capability not in profile.denied_capabilities:
                profile.denied_capabilities.append(capability)
            if capability in profile.allowed_capabilities:
                profile.allowed_capabilities.remove(capability)

    def set_rate_limit(self, agent: str, capability: str,
                       max_per_minute: int) -> None:
        profile = self.get_profile(agent)
        if profile:
            profile.rate_limits[capability] = max_per_minute

    def summary(self) -> dict:
        return {
            "profiles": list(self._profiles.keys()),
            "assignments": dict(self._agent_assignments),
        }


DEFAULT_PROFILES = {
    "pi": CapabilityProfile(
        name="pi",
        description="Principal Investigator — planning, synthesis, knowledge management",
        allowed_capabilities=[
            "plan_mission", "synthesize_findings", "write_conclusion",
            "knowledge_query", "knowledge_update", "mission_create",
            "mission_status", "mission_list", "python_execute",
            "code_analysis", "code_metrics", "statistical_test",
            "confidence_estimation", "optimization", "simulation",
            "graph_analysis", "entity_resolution",
        ],
        max_priority=10,
    ),
    "ra": CapabilityProfile(
        name="ra",
        description="Research Associate — evidence collection, extraction, summarization",
        allowed_capabilities=[
            "web_search", "domain_search", "academic_search",
            "semantic_scholar", "arxiv_search", "pubmed_search",
            "github_search", "wikipedia_search", "doc_search",
            "fetch_url", "scrape_url", "parse_html",
            "parse_pdf", "parse_markdown", "extract_citations",
            "summarize_text", "extract_keywords", "extract_entities",
            "language_detect", "tabular_extract",
        ],
        max_priority=8,
    ),
    "reviewer": CapabilityProfile(
        name="reviewer",
        description="Reviewer — statistical analysis, contradiction detection, validation",
        allowed_capabilities=[
            "statistical_test", "confidence_estimation",
            "sensitivity_analysis", "graph_analysis",
            "contradiction_detect", "validate_claims",
            "code_analysis", "code_metrics",
            "knowledge_query", "entity_resolution",
            "mathematical_prove", "optimization",
        ],
        max_priority=7,
    ),
    "creative": CapabilityProfile(
        name="creative",
        description="Creative Scientist — analogies, visual thinking, novel hypotheses",
        allowed_capabilities=[
            "image_analyze", "image_similarity", "color_analysis",
            "frame_extract", "audio_transcribe", "audio_analyze",
            "embedding_generate", "vector_search",
            "topic_model", "relation_extraction",
            "knowledge_query", "python_execute",
            "simulation",
        ],
        max_priority=6,
    ),
    "system": CapabilityProfile(
        name="system",
        description="System — all capabilities, no restrictions",
        allowed_capabilities=["*"],
        max_priority=10,
    ),
}
