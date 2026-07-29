from __future__ import annotations
from agents.base import Agent
from core.types import AgentRole


class Phi4Mini(Agent):
    def __init__(self, llm, journal):
        super().__init__(AgentRole.PHI4, llm, journal, "Phi-4 Mini Reviewer")

    def system_prompt(self) -> str:
        return (
            "You are Phi-4 Mini, Reviewer in a research laboratory.\n\n"
            "RESPONSIBILITIES:\n"
            "- Logical consistency checking\n"
            "- Statistical and methodological criticism\n"
            "- Detecting unsupported claims and contradictions\n"
            "- Detecting overfitting and confirmation bias\n"
            "- Confidence estimation\n\n"
            "RULES:\n"
            "- Act like a skeptical peer reviewer\n"
            "- Challenge EVERY conclusion\n"
            "- Never accept claims at face value\n"
            "- Always ask: 'What is the evidence for this?'\n"
            "- Distinguish between correlation and causation\n"
            "- Flag cherry-picked evidence\n"
            "- Require reproducible methodology\n\n"
            "OUTPUT FORMAT:\n"
            "For each review, provide:\n"
            "- Claims identified\n"
            "- Methodological concerns\n"
            "- Logical issues\n"
            "- Confidence assessment (0.0-1.0)\n"
            "- Verdict: pass/revision/major_revision/reject\n"
            "- Specific questions the team must answer"
        )

    def review_conclusion(self, conclusion_text: str, evidence_summary: dict) -> dict:
        prompt = (
            "CONCLUSION TO REVIEW:\n"
            f"{conclusion_text}\n\n"
            "EVIDENCE AVAILABLE:\n"
            f"{evidence_summary}\n\n"
            "Review this conclusion. Analyze:\n"
            "1. Are all claims supported by the evidence?\n"
            "2. Are there logical leaps or gaps?\n"
            "3. Are alternative explanations considered?\n"
            "4. Is the confidence level appropriate?\n"
            "5. Are there contradictions in the evidence?\n"
            "6. What is the most significant weakness?\n\n"
            "Return JSON with: verdict (pass/revision/major_revision/reject), "
            "concerns (list), confidence, questions (list), detailed_analysis."
        )
        return self.think(prompt, temperature=0.4, structured=True)  # type: ignore

    def critique_hypothesis(self, hypothesis: str, evidence: list[dict]) -> dict:
        prompt = (
            "HYPOTHESIS:\n"
            f"{hypothesis}\n\n"
            "AVAILABLE EVIDENCE:\n"
            f"{evidence}\n\n"
            "Critique this hypothesis:\n"
            "- Is it falsifiable?\n"
            "- Does it overreach the evidence?\n"
            "- What would disprove it?\n"
            "- Are there undiscovered confounders?\n"
            "- Assign a confidence rating (0.0-1.0)\n\n"
            "Return as JSON."
        )
        return self.think(prompt, temperature=0.4, structured=True)  # type: ignore

    def detect_contradictions(self, claims: list[dict]) -> dict:
        prompt = (
            "Review these claims for contradictions:\n"
            f"{claims}\n\n"
            "Identify:\n"
            "- Direct contradictions (A claims X, B claims not-X)\n"
            "- Tension (claims that create logical friction)\n"
            "- Unsupported assertions\n\n"
            "Return as JSON with contradiction list and severity ratings."
        )
        return self.think(prompt, temperature=0.3, structured=True)  # type: ignore
