from __future__ import annotations
import logging
import threading
import time
from collections import defaultdict
from typing import Any, Optional

from core.types import AgentRole
from capabilities.base import (
    CapabilityDeclaration, CapabilityRequest, CapabilityResult,
    LatencyClass, CapabilityStatus,
)
from capabilities.registry import CapabilityRegistry
from capabilities.permission import PermissionManager
from capabilities.execution import ExecutionEngine

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str, max_per_minute: int = 10) -> bool:
        now = time.time()
        with self._lock:
            self._buckets[key] = [t for t in self._buckets[key] if now - t < 60]
            if len(self._buckets[key]) >= max_per_minute:
                return False
            self._buckets[key].append(now)
            return True


class CapabilityScheduler:
    def __init__(self, registry: CapabilityRegistry,
                 permissions: PermissionManager,
                 engine: ExecutionEngine):
        self.registry = registry
        self.permissions = permissions
        self.engine = engine
        self.rate_limiter = RateLimiter()
        self._queue: list[CapabilityRequest] = []
        self._lock = threading.Lock()

    def submit(self, request: CapabilityRequest) -> CapabilityResult:
        decl = self.registry.get(request.capability)
        if not decl:
            return CapabilityResult.fail(
                error=f"Unknown capability: {request.capability}",
            )

        if decl.status == CapabilityStatus.UNAVAILABLE:
            return CapabilityResult.fail(
                error=f"Capability '{request.capability}' is unavailable",
            )

        allowed, reason = self.permissions.check(request)
        if not allowed:
            logger.warning(f"Permission denied: {request.agent.value} -> "
                           f"{request.capability}: {reason}")
            return CapabilityResult.fail(
                error=f"Permission denied: {reason}",
            )

        profile = self.permissions.get_profile(request.agent)
        if profile and request.capability in profile.rate_limits:
            limit = profile.rate_limits[request.capability]
            rate_key = f"{request.agent.value}:{request.capability}"
            if not self.rate_limiter.check(rate_key, limit):
                return CapabilityResult.fail(
                    error=f"Rate limit exceeded for {request.capability} "
                           f"(max {limit}/min)",
                )

        logger.info(f"Scheduling: {request.agent.value} -> "
                     f"{request.capability} (priority={request.priority})")
        return self.engine.execute(request, decl)

    def submit_batch(self, requests: list[CapabilityRequest]) -> list[CapabilityResult]:
        return [self.submit(r) for r in requests]

    def submit_async(self, request: CapabilityRequest) -> str:
        with self._lock:
            self._queue.append(request)
        return request.request_id

    def process_queue(self, max_batch: int = 10) -> list[CapabilityResult]:
        batch = []
        with self._lock:
            while self._queue and len(batch) < max_batch:
                batch.append(self._queue.pop(0))
        if not batch:
            return []
        batch.sort(key=lambda r: r.priority, reverse=True)
        return [self.submit(r) for r in batch]

    def queue_size(self) -> int:
        with self._lock:
            return len(self._queue)
