from __future__ import annotations
import json
from typing import Any, Optional

from research_runtime.persistence import RuntimeStore


class CompositeManager:
    def __init__(self, store: RuntimeStore):
        self.store = store
        self._cache: dict[str, dict] = {}

    def register(self, name: str, description: str,
                 pipeline: list[dict], version: str = "0.1.0") -> None:
        pipeline_json = json.dumps(pipeline)
        self.store.save_composite(name, description, pipeline_json, version)
        self._cache[name] = {
            "name": name,
            "description": description,
            "pipeline": pipeline,
            "version": version,
        }

    def list(self) -> list[dict]:
        return self.store.list_composites()

    def get(self, name: str) -> Optional[dict]:
        if name in self._cache:
            return self._cache[name]
        composites = self.store.list_composites()
        for c in composites:
            if c["name"] == name:
                parsed = {
                    "name": c["name"],
                    "description": c["description"],
                    "pipeline": json.loads(c["pipeline_json"]),
                    "version": c.get("version", "0.1.0"),
                }
                self._cache[name] = parsed
                return parsed
        return None

    def discover_missing_dependencies(self) -> list[dict]:
        composites = self.store.list_composites()
        all_caps = set()
        try:
            from capabilities import registry
            all_caps.update(r.name for r in registry.list())
        except ImportError:
            return []

        missing = []
        for c in composites:
            pipeline = json.loads(c["pipeline_json"])
            for step in pipeline:
                cap = step.get("capability", "")
                if cap and cap not in all_caps:
                    missing.append({
                        "composite": c["name"],
                        "missing_capability": cap,
                    })
        return missing

    def expand_pipeline(self, name: str) -> Optional[list[dict]]:
        composite = self.get(name)
        if not composite:
            return None
        expanded = []
        for step in composite["pipeline"]:
            if step.get("type") == "composite":
                nested = self.expand_pipeline(step["name"])
                if nested:
                    expanded.extend(nested)
                continue
            expanded.append(step)
        return expanded

    def validate_pipeline(self, pipeline: list[dict]) -> dict:
        errors = []
        all_caps = set()
        try:
            from capabilities import registry
            all_caps = set(r.name for r in registry.list())
        except ImportError:
            pass

        for i, step in enumerate(pipeline):
            cap = step.get("capability", "")
            if not cap:
                errors.append(f"Step {i}: missing 'capability' field")
            elif cap not in all_caps:
                errors.append(f"Step {i}: capability '{cap}' not found in registry")

            inputs = step.get("inputs", {})
            for key in ("query", "model"):
                if key in inputs and not isinstance(inputs[key], str):
                    errors.append(
                        f"Step {i}: input '{key}' must be string"
                    )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "step_count": len(pipeline),
        }
