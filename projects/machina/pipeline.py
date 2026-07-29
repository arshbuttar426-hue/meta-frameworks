from __future__ import annotations
import logging
import time
from typing import Any, Optional

from core.types import AgentRole
from capabilities.base import (
    PipelineDefinition, PipelineStep, PipelineResult,
    CapabilityRequest, CapabilityResult,
)
from capabilities.scheduler import CapabilityScheduler

logger = logging.getLogger(__name__)


class PipelineBuilder:
    def __init__(self, scheduler: CapabilityScheduler):
        self.scheduler = scheduler

    def build(self, name: str, steps: list[dict],
              description: str = "") -> PipelineDefinition:
        parsed = []
        for s in steps:
            if isinstance(s, PipelineStep):
                parsed.append(s)
            elif isinstance(s, dict):
                parsed.append(PipelineStep(
                    capability=s.get("capability", ""),
                    inputs=s.get("inputs", {}),
                    alias=s.get("alias", s.get("capability", "")),
                    depends_on=s.get("depends_on", []),
                ))
        return PipelineDefinition(name=name, steps=parsed, description=description)

    def validate(self, pipeline: PipelineDefinition) -> list[str]:
        errors = []
        names = set()
        for step in pipeline.steps:
            if not step.capability:
                errors.append(f"Step '{step.alias}' has no capability")
            if step.alias in names:
                errors.append(f"Duplicate alias: {step.alias}")
            names.add(step.alias)
            for dep in step.depends_on:
                if dep not in names and dep != step.alias:
                    if dep not in [s.alias for s in pipeline.steps]:
                        errors.append(f"Step '{step.alias}' depends on unknown step '{dep}'")

        step_order = [s.alias for s in pipeline.steps]
        for step in pipeline.steps:
            for dep in step.depends_on:
                if dep in step_order:
                    dep_idx = step_order.index(dep)
                    step_idx = step_order.index(step.alias)
                    if dep_idx > step_idx:
                        errors.append(
                            f"Step '{step.alias}' depends on '{dep}' "
                            f"which appears after it"
                        )
        return errors

    def run(self, pipeline: PipelineDefinition,
            agent: AgentRole = AgentRole.GEMMA,
            mission_id: Optional[str] = None) -> PipelineResult:
        errors = self.validate(pipeline)
        if errors:
            return PipelineResult(
                name=pipeline.name,
                success=False,
                error=f"Pipeline validation failed: {'; '.join(errors)}",
            )

        start = time.time()
        step_results: dict[str, CapabilityResult] = {}
        completed: set[str] = set()

        while len(completed) < len(pipeline.steps):
            progress = False
            for step in pipeline.steps:
                if step.alias in completed:
                    continue
                deps_met = all(d in completed for d in step.depends_on)
                if not deps_met:
                    continue

                resolved_inputs = dict(step.inputs)
                for key, val in resolved_inputs.items():
                    if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
                        ref = val[2:-1]
                        parts = ref.split(".")
                        if parts[0] in step_results:
                            result_obj = step_results[parts[0]]
                            if result_obj.success and result_obj.output is not None:
                                if len(parts) > 1:
                                    out = result_obj.output
                                    if isinstance(out, dict):
                                        resolved_inputs[key] = out.get(parts[1], val)
                                else:
                                    resolved_inputs[key] = result_obj.output

                req = CapabilityRequest(
                    capability=step.capability,
                    inputs=resolved_inputs,
                    agent=agent,
                    mission_id=mission_id,
                )
                logger.info(f"Pipeline step: {step.alias} -> {step.capability}")
                result = self.scheduler.submit(req)
                step_results[step.alias] = result
                completed.add(step.alias)
                progress = True

                if not result.success and step.retry_policy:
                    meta = result.metadata
                    if meta.retry_count >= (step.retry_policy.max_retries + 1):
                        logger.error(f"Pipeline step {step.alias} failed after retries")
                        return PipelineResult(
                            name=pipeline.name,
                            step_results=step_results,
                            success=False,
                            error=f"Step '{step.alias}' failed: {result.error}",
                            total_duration_ms=(time.time() - start) * 1000,
                        )

            if not progress and len(completed) < len(pipeline.steps):
                remaining = [s.alias for s in pipeline.steps if s.alias not in completed]
                return PipelineResult(
                    name=pipeline.name,
                    step_results=step_results,
                    success=False,
                    error=f"Pipeline deadlock. Remaining steps: {remaining}",
                    total_duration_ms=(time.time() - start) * 1000,
                )

        total_time = (time.time() - start) * 1000
        all_ok = all(r.success for r in step_results.values())
        return PipelineResult(
            name=pipeline.name,
            step_results=step_results,
            success=all_ok,
            total_duration_ms=total_time,
        )
