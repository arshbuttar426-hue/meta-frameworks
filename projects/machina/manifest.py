from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Optional

from capabilities.base import (
    CapabilityDeclaration, CapabilityIO, RetryPolicy,
    LatencyClass, CostClass, CapabilityStatus,
)

logger = logging.getLogger(__name__)

MANIFEST_SCHEMA_VERSION = "1.0.0"


def validate_manifest(data: dict) -> list[str]:
    errors = []
    if not isinstance(data, dict):
        return ["Root must be a dict"]
    if "capabilities" not in data:
        return ["Missing required key: capabilities"]
    if not isinstance(data["capabilities"], list):
        return ["capabilities must be a list"]
    for i, cap in enumerate(data["capabilities"]):
        if not isinstance(cap, dict):
            errors.append(f"capabilities[{i}]: must be a dict")
            continue
        if "name" not in cap:
            errors.append(f"capabilities[{i}]: missing name")
        if "description" not in cap:
            errors.append(f"capabilities[{i}]: missing description")
    return errors


def load_manifest(path: str | Path) -> list[CapabilityDeclaration]:
    path = Path(path)
    if not path.exists():
        logger.warning(f"Manifest not found: {path}")
        return []
    with open(path) as f:
        data = json.load(f)
    errors = validate_manifest(data)
    if errors:
        logger.error(f"Manifest validation errors in {path}: {errors}")
        return []
    return [dict_to_declaration(c) for c in data["capabilities"]]


def dict_to_declaration(d: dict) -> CapabilityDeclaration:
    inputs = []
    for inp in d.get("inputs", []):
        if isinstance(inp, dict):
            inputs.append(CapabilityIO(
                name=inp.get("name", ""),
                type=inp.get("type", "string"),
                description=inp.get("description", ""),
                required=inp.get("required", True),
                default=inp.get("default"),
                examples=inp.get("examples", []),
            ))
        elif isinstance(inp, str):
            inputs.append(CapabilityIO(name=inp, type="string"))

    outputs = []
    for out in d.get("outputs", []):
        if isinstance(out, dict):
            outputs.append(CapabilityIO(
                name=out.get("name", ""),
                type=out.get("type", "any"),
                description=out.get("description", ""),
                required=out.get("required", True),
            ))
        elif isinstance(out, str):
            outputs.append(CapabilityIO(name=out, type="any"))

    retry = d.get("retry_policy", {})
    if isinstance(retry, dict):
        retry = RetryPolicy(
            max_retries=retry.get("max_retries", 3),
            backoff_base=retry.get("backoff_base", 2.0),
            backoff_max=retry.get("backoff_max", 60.0),
            retryable_errors=retry.get("retryable_errors", [
                "timeout", "rate_limit", "network",
            ]),
        )

    return CapabilityDeclaration(
        name=d["name"],
        description=d.get("description", ""),
        inputs=inputs,
        outputs=outputs,
        latency=LatencyClass(d.get("latency", "medium")),
        expected_cost=CostClass(d.get("expected_cost", "local")),
        offline_support=d.get("offline_support", False),
        internet_required=d.get("internet_required", False),
        dependencies=d.get("dependencies", []),
        failure_modes=d.get("failure_modes", []),
        confidence=d.get("confidence", 0.8),
        parallel_safe=d.get("parallel_safe", True),
        cacheable=d.get("cacheable", True),
        deterministic=d.get("deterministic", False),
        retry_policy=retry,
        version=d.get("version", "0.1.0"),
        category=d.get("category", "general"),
        tags=d.get("tags", []),
        status=CapabilityStatus(d.get("status", "available")),
    )


def declaration_to_dict(decl: CapabilityDeclaration) -> dict:
    return {
        "name": decl.name,
        "description": decl.description,
        "category": decl.category,
        "version": decl.version,
        "status": decl.status.value,
        "latency": decl.latency.value,
        "expected_cost": decl.expected_cost.value,
        "offline_support": decl.offline_support,
        "internet_required": decl.internet_required,
        "parallel_safe": decl.parallel_safe,
        "cacheable": decl.cacheable,
        "deterministic": decl.deterministic,
        "confidence": decl.confidence,
        "dependencies": decl.dependencies,
        "failure_modes": decl.failure_modes,
        "tags": decl.tags,
        "inputs": [
            {
                "name": i.name, "type": i.type,
                "description": i.description,
                "required": i.required,
                "examples": i.examples,
            }
            for i in decl.inputs
        ],
        "outputs": [
            {
                "name": o.name, "type": o.type,
                "description": o.description,
            }
            for o in decl.outputs
        ],
        "retry_policy": {
            "max_retries": decl.retry_policy.max_retries,
            "backoff_base": decl.retry_policy.backoff_base,
            "backoff_max": decl.retry_policy.backoff_max,
        },
    }


def export_manifest(declarations: list[CapabilityDeclaration],
                    path: str | Path) -> None:
    path = Path(path)
    data = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "capabilities": [declaration_to_dict(d) for d in declarations],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Exported {len(declarations)} capabilities to {path}")
