from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from research_runtime.phase_diagram import PhaseDiagram


@dataclass
class Antibody:
    model: str
    task: str
    condition: str
    corrective_action: str
    confidence: float
    source: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    hit_count: int = 0


class ImmuneMemory:
    def __init__(self, phase_diagram: Optional[PhaseDiagram] = None):
        self.antibodies: list[Antibody] = []
        if phase_diagram is not None:
            self._generate_from_phase_diagram(phase_diagram)

    def _generate_from_phase_diagram(self, pd: PhaseDiagram) -> None:
        for (model, task), regions in pd.regions.items():
            for region in regions:
                if region.delivery_rate < 0.5:
                    self.antibodies.append(Antibody(
                        model=model,
                        task=task,
                        condition=f"temp in [{region.temp_min}, {region.temp_max})",
                        corrective_action=(
                            f"Switch model for task '{task}' — "
                            f"delivery rate {region.delivery_rate:.0%} "
                            f"in temp range [{region.temp_min}, {region.temp_max})"
                        ),
                        confidence=1.0 - region.delivery_rate,
                        source="phase_diagram:delivery_rate",
                    ))
                if region.repetition_risk > 0.3:
                    self.antibodies.append(Antibody(
                        model=model,
                        task=task,
                        condition=f"temp in [{region.temp_min}, {region.temp_max})",
                        corrective_action=(
                            f"Reduce temperature for {model} on '{task}' — "
                            f"repetition risk {region.repetition_risk:.0%}"
                        ),
                        confidence=region.repetition_risk,
                        source="phase_diagram:repetition_risk",
                    ))

    def learn(self, model: str, task: str, condition: str,
              corrective_action: str, confidence: float,
              source: str = "production") -> Antibody:
        antibody = Antibody(
            model=model,
            task=task,
            condition=condition,
            corrective_action=corrective_action,
            confidence=confidence,
            source=source,
        )
        self.antibodies.append(antibody)
        return antibody

    def query(self, model: str, task: str,
              temperature: Optional[float] = None) -> list[Antibody]:
        matches = []
        for ab in self.antibodies:
            if ab.model == model and ab.task == task:
                matches.append(ab)
            elif ab.model == model and ab.task == "any":
                matches.append(ab)
            elif ab.model == "any" and ab.task == task:
                matches.append(ab)
        matches.sort(key=lambda ab: ab.confidence, reverse=True)
        for ab in matches:
            ab.hit_count += 1
        return matches

    def check_config(self, model: str, task: str,
                     temperature: float) -> list[str]:
        warnings = []
        for ab in self.antibodies:
            if ab.model != model and ab.model != "any":
                continue
            if ab.task != task and ab.task != "any":
                continue
            warnings.append(
                f"[{ab.source}] {ab.model}/{ab.task}: {ab.corrective_action}"
            )
        return warnings

    def stats(self) -> dict:
        return {
            "total_antibodies": len(self.antibodies),
            "by_source": {
                src: sum(1 for a in self.antibodies if a.source == src)
                for src in {a.source for a in self.antibodies}
            },
            "total_hits": sum(a.hit_count for a in self.antibodies),
        }
