from __future__ import annotations
import logging
from typing import Any, Optional

from capabilities.base import (
    CapabilityDeclaration, CapabilityRequest, CapabilityResult,
    CapabilityStatus, CapabilityIO, RetryPolicy, LatencyClass, CostClass,
)

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    def __init__(self):
        self._declarations: dict[str, CapabilityDeclaration] = {}
        self._implementations: dict[str, Any] = {}

    def register(self, decl: CapabilityDeclaration,
                 implementation: Optional[Any] = None) -> None:
        if decl.name in self._declarations:
            logger.debug(f"Capability already registered: {decl.name}")
            return
        self._declarations[decl.name] = decl
        if implementation:
            self._implementations[decl.name] = implementation
            decl.implementation = implementation.__name__ if hasattr(implementation, "__name__") else str(type(implementation).__name__)
        logger.debug(f"Registered capability: {decl.name} (v{decl.version})")

    def get(self, name: str) -> Optional[CapabilityDeclaration]:
        return self._declarations.get(name)

    def has(self, name: str) -> bool:
        return name in self._declarations

    def list(self, category: Optional[str] = None,
             status: Optional[CapabilityStatus] = None,
             tag: Optional[str] = None) -> list[CapabilityDeclaration]:
        results = []
        for decl in self._declarations.values():
            if category and decl.category != category:
                continue
            if status and decl.status != status:
                continue
            if tag and tag not in decl.tags:
                continue
            results.append(decl)
        return sorted(results, key=lambda d: d.name)

    def categories(self) -> list[str]:
        return sorted(set(d.category for d in self._declarations.values()))

    def search(self, query: str) -> list[CapabilityDeclaration]:
        q = query.lower()
        return [
            d for d in self._declarations.values()
            if q in d.name.lower()
            or q in d.description.lower()
            or q in d.category.lower()
            or any(q in t.lower() for t in d.tags)
        ]

    def set_implementation(self, name: str, implementation: Any) -> None:
        if name in self._declarations:
            self._implementations[name] = implementation
            self._declarations[name].implementation = implementation.__name__ if hasattr(implementation, "__name__") else str(type(implementation).__name__)
            self._declarations[name].status = CapabilityStatus.AVAILABLE

    def get_implementation(self, name: str) -> Optional[Any]:
        return self._implementations.get(name)

    def set_status(self, name: str, status: CapabilityStatus) -> None:
        decl = self._declarations.get(name)
        if decl:
            decl.status = status

    def count(self) -> int:
        return len(self._declarations)

    def summary(self, category: Optional[str] = None) -> dict:
        caps = self.list(category=category)
        return {
            "total": len(caps),
            "available": sum(1 for c in caps if c.status == CapabilityStatus.AVAILABLE),
            "unavailable": sum(1 for c in caps if c.status == CapabilityStatus.UNAVAILABLE),
            "degraded": sum(1 for c in caps if c.status == CapabilityStatus.DEGRADED),
            "categories": self.categories(),
        }

    def to_manifest(self) -> dict:
        return {
            "registry_version": "1.0.0",
            "capabilities": [
                {
                    "name": d.name,
                    "description": d.description,
                    "category": d.category,
                    "version": d.version,
                    "status": d.status.value,
                    "latency": d.latency.value,
                    "cost": d.expected_cost.value,
                    "offline": d.offline_support,
                    "internet": d.internet_required,
                    "parallel_safe": d.parallel_safe,
                    "cacheable": d.cacheable,
                    "confidence": d.confidence,
                    "inputs": [
                        {"name": i.name, "type": i.type, "required": i.required}
                        for i in d.inputs
                    ],
                    "outputs": [
                        {"name": o.name, "type": o.type}
                        for o in d.outputs
                    ],
                    "tags": d.tags,
                }
                for d in sorted(self._declarations.values(), key=lambda x: x.name)
            ],
        }

    def create_quick_declaration(
        self, name: str, description: str,
        category: str = "general",
        inputs: list[tuple[str, str]] | None = None,
        outputs: list[tuple[str, str]] | None = None,
        latency: str = "medium",
        internet: bool = False,
        cacheable: bool = True,
        parallel_safe: bool = True,
    ) -> CapabilityDeclaration:
        return CapabilityDeclaration(
            name=name,
            description=description,
            inputs=[CapabilityIO(name=n, type=t) for n, t in (inputs or [])],
            outputs=[CapabilityIO(name=n, type=t) for n, t in (outputs or [])],
            latency=LatencyClass(latency),
            internet_required=internet,
            cacheable=cacheable,
            parallel_safe=parallel_safe,
            category=category,
        )
