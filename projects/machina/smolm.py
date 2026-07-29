from __future__ import annotations
from agents.base import Agent
from core.types import AgentRole, EvidenceLevel


class SmolLM3(Agent):
    def __init__(self, llm, journal):
        super().__init__(
            AgentRole.SMOLM3, llm, journal, "SmolLM3 Research Associate"
        )

    def system_prompt(self) -> str:
        return (
            "You are SmolLM3, Research Associate in a research laboratory.\n\n"
            "RESPONSIBILITIES:\n"
            "- Literature extraction and summarization\n"
            "- Reading papers, documentation, and repositories\n"
            "- Building structured notes and evidence timelines\n"
            "- Producing structured knowledge only\n\n"
            "RULES:\n"
            "- Never write conclusions or recommendations\n"
            "- Never interpret findings beyond what sources state\n"
            "- Always cite sources with confidence levels\n"
            "- Always distinguish between what sources say and what you infer\n"
            "- Expose unknowns and assumptions explicitly\n"
            "- Use evidence levels: anecdotal, single_source, multi_source, systematic, meta_analysis\n\n"
            "OUTPUT FORMAT:\n"
            "Structured evidence entries with:\n"
            "- Claim\n"
            "- Source\n"
            "- Confidence (0.0-1.0)\n"
            "- Evidence level\n"
            "- Key passages\n"
            "- Unknowns\n"
            "- Assumptions\n"
            "- Reasoning chain"
        )

    def extract_evidence(self, source_text: str, source_id: str) -> dict:
        prompt = (
            f"Source ID: {source_id}\n"
            f"Source text: {source_text[:3000]}\n\n"
            "Extract ALL factual claims from this source. For each claim, provide:\n"
            "- Statement (verbatim or close paraphrase)\n"
            "- Confidence that this is accurately represented (0.0-1.0)\n"
            "- Evidence level\n"
            "- Unknowns (what the source doesn't address)\n"
            "- Assumptions the source makes\n"
            "- Reasoning chain (how you arrived at this extraction)\n\n"
            "Return as JSON array."
        )
        return self.think(prompt, temperature=0.2, structured=True)  # type: ignore

    def summarize_source(self, source_text: str, source_title: str) -> dict:
        prompt = (
            f"Title: {source_title}\n"
            f"Text: {source_text[:4000]}\n\n"
            "Create a structured summary:\n"
            "- Main claims (list)\n"
            "- Methodology (if any)\n"
            "- Key evidence presented\n"
            "- Limitations acknowledged by source\n"
            "- Confidence in source reliability (0.0-1.0)\n\n"
            "Return as JSON."
        )
        return self.think(prompt, temperature=0.3, structured=True)  # type: ignore

    def build_timeline(self, events: list[dict]) -> dict:
        prompt = (
            "Given these events/claims with timestamps:\n"
            f"{events}\n\n"
            "Build a chronological structured timeline. Group related events.\n"
            "Return as JSON with ordered entries."
        )
        return self.think(prompt, temperature=0.3, structured=True)  # type: ignore
