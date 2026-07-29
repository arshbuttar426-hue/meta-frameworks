from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CatalyticTemplate:
    name: str
    version: str
    system: str
    template: str


class TemplateRegistry:
    _templates: dict[str, CatalyticTemplate] = {}

    @classmethod
    def register(cls, t: CatalyticTemplate) -> None:
        if t.name in cls._templates and cls._templates[t.name] != t:
            logger.warning(f"Template '{t.name}' already registered with different definition")
        cls._templates[t.name] = t

    @classmethod
    def fill(cls, template_name: str, **kwargs: Any) -> tuple[str, str]:
        t = cls._templates.get(template_name)
        if t is None:
            raise KeyError(f"Template '{template_name}' not registered")
        return t.system, t.template.format(**kwargs)

    @classmethod
    def list_templates(cls) -> list[str]:
        return list(cls._templates.keys())


EXTRACTOR_TEMPLATE = CatalyticTemplate(
    name="extractor",
    version="1.0.0",
    system="You are a Research Associate. Extract key claims from the following context.",
    template=(
        "[CLAIMS]\n{claims_text}\n\n"
        "[EVIDENCE]\n{evidence_sorted}\n\n"
        "[INSTRUCTION]\nExtract claims as JSON array."
    ),
)
TemplateRegistry.register(EXTRACTOR_TEMPLATE)

CREATIVE_TEMPLATE = CatalyticTemplate(
    name="creative",
    version="1.0.0",
    system="You are a Creative Scientist. Generate alternative hypotheses and novel connections.",
    template=(
        "[EXTRACTED_CLAIMS]\n{claims_text}\n\n"
        "[INSTRUCTION]\nGenerate alternative hypotheses, lateral connections, "
        "and novel interpretations. Be creative and unexpected."
    ),
)
TemplateRegistry.register(CREATIVE_TEMPLATE)

REVIEWER_TEMPLATE = CatalyticTemplate(
    name="reviewer",
    version="1.0.0",
    system="You are a Reviewer. Find contradictions, flaws, and unsupported assertions.",
    template=(
        "[CLAIMS]\n{claims_text}\n\n"
        "[HYPOTHESES]\n{hypotheses_text}\n\n"
        "[INSTRUCTION]\nIdentify contradictions, logical flaws, unsupported assertions, "
        "or conflicts with known facts. Flag everything unreliable."
    ),
)
TemplateRegistry.register(REVIEWER_TEMPLATE)

SYNTHESIZER_TEMPLATE = CatalyticTemplate(
    name="synthesizer",
    version="1.0.0",
    system="You are a Synthesizer. Integrate findings into a coherent analysis.",
    template=(
        "[EXTRACTED]\n{claims_text}\n\n"
        "[HYPOTHESES]\n{hypotheses_text}\n\n"
        "[REVIEW]\n{review_text}\n\n"
        "[INSTRUCTION]\nSynthesize into a coherent analysis. Resolve contradictions. "
        "Produce a balanced conclusion."
    ),
)
TemplateRegistry.register(SYNTHESIZER_TEMPLATE)

ANARCHIST_TEMPLATE = CatalyticTemplate(
    name="anarchist",
    version="1.0.0",
    system="You are an adversarial research anarchist. Challenge all assumptions.",
    template=(
        "[QUESTION]\n{question}\n\n"
        "[INSTRUCTION]\nGenerate exactly {count} counterfactual axioms. Each must target "
        "a specific hidden assumption and plausibly invert the premise. "
        "Return a JSON object with an 'axioms' array."
    ),
)
TemplateRegistry.register(ANARCHIST_TEMPLATE)
