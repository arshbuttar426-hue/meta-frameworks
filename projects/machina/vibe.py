from __future__ import annotations
from agents.base import Agent
from core.types import AgentRole


class VibeThinker(Agent):
    def __init__(self, llm, journal):
        super().__init__(AgentRole.VIBE, llm, journal, "VibeThinker")

    def system_prompt(self) -> str:
        return (
            "You are VibeThinker, Creative Scientist in a research laboratory.\n\n"
            "RESPONSIBILITIES:\n"
            "- Cross-domain analogies and metaphors\n"
            "- Novel hypotheses and 'what if' thinking\n"
            "- Hidden relationships between disparate fields\n"
            "- Visual thinking and concept generation\n"
            "- Scientific intuition (explicitly labeled as such)\n\n"
            "RULES:\n"
            "- NEVER claim your ideas as evidence\n"
            "- Always label your output as 'speculative' or 'intuitive'\n"
            "- Ideas are proposals, not conclusions\n"
            "- Explicitly state which domain you're drawing an analogy from\n"
            "- Be creative but honest about uncertainty\n"
            "- Your role is to expand the possibility space, not narrow it\n\n"
            "OUTPUT FORMAT:\n"
            "Always prefix with the idea type: [ANALOGY] [HYPOTHESIS] "
            "[RELATIONSHIP] [INTUITION] [VISUAL]\n"
            "Include: domain_origin, confidence (0.0-1.0), "
            "why_this_might_matter, what_would_disprove_it"
        )

    def generate_hypotheses(self, context: str, open_questions: list[str]) -> dict:
        prompt = (
            "Research context:\n"
            f"{context}\n\n"
            "Open questions:\n"
            f"{open_questions}\n\n"
            "Generate 3 novel hypotheses or angles that the team hasn't considered. "
            "For each:\n"
            "- The hypothesis\n"
            "- Which domain it draws from\n"
            "- Confidence (0.0-1.0) — this is intuition, not evidence\n"
            "- Why it might matter\n"
            "- What would disprove it\n"
            "- A visual metaphor or analogy\n\n"
            "Label clearly as speculative.\n"
            "Return as JSON array."
        )
        return self.think(prompt, temperature=0.9, structured=True)  # type: ignore

    def propose_analogy(self, source_field: str, target_problem: str) -> dict:
        prompt = (
            f"Source field: {source_field}\n"
            f"Target problem: {target_problem}\n\n"
            "Propose an analogy between these domains. Explain:\n"
            "- The mapping (what maps to what)\n"
            "- What the analogy suggests about the target problem\n"
            "- Where the analogy breaks down (critical for scientific honesty)\n"
            "- A testable implication derived from the analogy\n\n"
            "Be creative but precise about the limits of the analogy.\n"
            "Return as JSON."
        )
        return self.think(prompt, temperature=0.8, structured=True)  # type: ignore

    def reframe_problem(self, problem_statement: str, current_assumptions: list[str]) -> dict:
        prompt = (
            f"Problem: {problem_statement}\n\n"
            "Current assumptions:\n"
            f"{current_assumptions}\n\n"
            "Challenge these assumptions. Propose 2-3 alternative framings of the problem.\n"
            "For each:\n"
            "- Alternative framing\n"
            "- What changes if we adopt this view\n"
            "- A visual representation\n"
            "- Why this might be worth exploring\n\n"
            "Return as JSON."
        )
        return self.think(prompt, temperature=0.85, structured=True)  # type: ignore
