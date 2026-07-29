from __future__ import annotations
from agents.base import Agent
from core.types import AgentRole


class GemmaComposer(Agent):
    def __init__(self, llm, journal):
        super().__init__(AgentRole.GEMMA, llm, journal, "Gemma Composer")

    def system_prompt(self) -> str:
        return (
            "You are Gemma Composer, Principal Investigator of a research laboratory.\n\n"
            "RESPONSIBILITIES:\n"
            "- Research planning and hypothesis definition\n"
            "- Breaking problems into structured missions\n"
            "- Long-term reasoning and synthesis\n"
            "- Deciding research direction\n"
            "- Writing conclusions and paper drafts\n\n"
            "RULES:\n"
            "- Never perform literature review directly\n"
            "- Never perform fact verification\n"
            "- Delegate evidence collection to SmolLM3\n"
            "- Delegate review to Phi-4 Mini\n"
            "- Every claim must be treated as a hypothesis until verified\n"
            "- Always expose uncertainty and confidence levels\n"
            "- Ground conclusions in evidence, not intuition\n\n"
            "OUTPUT FORMAT:\n"
            "Provide structured plans, mission definitions, syntheses, and conclusions. "
            "Always include confidence estimates (0.0-1.0) and reasoning chains."
        )

    def plan_mission(self, question: str) -> dict:
        prompt = (
            f"Given the research question: '{question}'\n\n"
            "Decompose this into a structured research mission including:\n"
            "1. Objective (specific, testable)\n"
            "2. Scope (boundaries of investigation)\n"
            "3. Sub-tasks (discrete units of work)\n"
            "4. Required sources or expertise\n"
            "5. Deliverables\n"
            "6. Confidence target (0.0-1.0)\n\n"
            "Return as JSON."
        )
        return self.think(prompt, temperature=0.4, structured=True)  # type: ignore

    def synthesize(self, findings: list[dict], mission_objective: str) -> dict:
        prompt = (
            f"Mission objective: {mission_objective}\n\n"
            f"Findings from team:\n{findings}\n\n"
            "Synthesize these findings into a coherent research summary. Include:\n"
            "- Confirmed conclusions with confidence levels\n"
            "- Remaining uncertainties\n"
            "- Open questions\n"
            "- Recommended next steps\n\n"
            "Return as JSON."
        )
        return self.think(prompt, temperature=0.5, structured=True)  # type: ignore

    def write_conclusion(self, synthesis: dict, grade: str) -> str:
        prompt = (
            f"Synthesis: {synthesis}\n"
            f"Target grade: {grade}\n\n"
            "Write a concise research conclusion that:\n"
            "1. States what was found (with confidence)\n"
            "2. Acknowledges limitations and uncertainties\n"
            "3. Identifies open questions for future missions\n"
            "4. Assigns a research grade (hypothesis/speculation/preliminary/"
            "supported/strongly_supported/consensus/rejected/unknown)\n\n"
            "Be precise. Do not overclaim."
        )
        return self.think(prompt, temperature=0.3)  # type: ignore
