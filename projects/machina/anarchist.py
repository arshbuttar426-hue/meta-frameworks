import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CounterfactualAxiom:
    axiom: str
    target_assumption: str
    severity: str  # "moderate" | "aggressive" | "foundational"
    confidence: float


@dataclass
class AnarchistOutput:
    axioms: list[CounterfactualAxiom] = field(default_factory=list)
    raw_response: str = ""


ANARCHIST_PROMPT = (
    "You are an adversarial research anarchist. Your only job is to identify and challenge "
    "the fundamental assumptions embedded in the following research question. "
    "For each assumption you identify, generate a counterfactual axiom — a statement that, "
    "if true, would completely invert or undermine the premise of the question.\n\n"
    "Generate exactly 5 counterfactual axioms. Each must:\n"
    "  1. Target a specific hidden assumption in the question\n"
    "  2. Be plausible enough to force genuine re-evaluation\n"
    "  3. Be assigned a severity: 'moderate', 'aggressive', or 'foundational'\n"
    "  4. Include a confidence score (0.0-1.0) reflecting how confident you are "
    "that this assumption is actually false\n\n"
    "Question: {question}\n\n"
    "Return a JSON object with a single key 'axioms' containing an array of objects, "
    "each with keys: 'axiom', 'target_assumption', 'severity', 'confidence'.\n"
    "Return ONLY the JSON object."
)


class AnarchistNode:
    def __init__(self, llm_client: Any):
        self.llm = llm_client

    def generate(self, question: str, mission_id: str) -> AnarchistOutput:
        prompt = ANARCHIST_PROMPT.format(question=question)
        try:
            result = self.llm.structured(
                model_key="ornith_anarchist",
                prompt=prompt,
                temperature=0.9,
                top_p=0.95,
                max_tokens=1000,
            )
            axioms_data = []
            if isinstance(result, dict):
                axioms_data = result.get("axioms", [])
            elif isinstance(result, list):
                axioms_data = result[:5]

            axioms = [
                CounterfactualAxiom(
                    axiom=a.get("axiom", str(a)),
                    target_assumption=a.get("target_assumption", ""),
                    severity=a.get("severity", "moderate"),
                    confidence=float(a.get("confidence", 0.3)),
                )
                for a in axioms_data[:5]
            ]
            return AnarchistOutput(axioms=axioms, raw_response=str(result))
        except Exception as e:
            logger.warning(f"AnarchistNode failed: {e}")
            return AnarchistOutput()

    def format_for_blackboard(self, output: AnarchistOutput) -> str:
        if not output.axioms:
            return "No counterfactual axioms generated."
        lines = ["=== ADVERSARIAL COUNTERFACTUAL AXIOMS ==="]
        for i, ax in enumerate(output.axioms, 1):
            lines.append(
                f"{i}. [{ax.severity.upper()}] {ax.axiom}\n"
                f"   Targets: {ax.target_assumption}\n"
                f"   Confidence: {ax.confidence:.2f}"
            )
        return "\n\n".join(lines)
