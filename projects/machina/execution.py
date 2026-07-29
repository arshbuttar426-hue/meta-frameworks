from __future__ import annotations
import functools
import hashlib
import json
import logging
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from capabilities.base import (
    CapabilityDeclaration, CapabilityRequest, CapabilityResult,
    ExecutionMetadata, CapabilityStatus,
)
from capabilities.registry import CapabilityRegistry
from capabilities.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class CacheEntry:
    def __init__(self, value: Any, ttl: int = 300):
        self.value = value
        self.expires_at = time.time() + ttl
        self.created_at = time.time()

    def is_valid(self) -> bool:
        return time.time() < self.expires_at


class ExecutionEngine:
    def __init__(self, registry: CapabilityRegistry,
                 metrics: Optional[MetricsCollector] = None):
        self.registry = registry
        self.metrics = metrics or MetricsCollector()
        self._cache: dict[str, CacheEntry] = {}
        self._cache_lock = threading.Lock()

    def execute(self, request: CapabilityRequest,
                decl: CapabilityDeclaration) -> CapabilityResult:
        cache_key = self._cache_key(request, decl) if decl.cacheable else None

        if cache_key:
            cached = self._get_cached(cache_key)
            if cached is not None:
                logger.info(f"Cache hit: {request.capability}")
                self.metrics.record(
                    capability=request.capability,
                    duration_ms=0,
                    success=True,
                    cache_hit=True,
                    agent=request.agent.value,
                    mission_id=request.mission_id,
                )
                cached.metadata.cache_hit = True
                return cached

        errors = decl.validate_inputs(request.inputs)
        if errors:
            return CapabilityResult.fail(
                error=f"Input validation failed: {'; '.join(errors)}",
            )

        impl = self.registry.get_implementation(request.capability)
        if not impl:
            return CapabilityResult.fail(
                error=f"No implementation registered for '{request.capability}'",
            )

        meta = ExecutionMetadata(
            capability=request.capability,
            implementation=decl.implementation or "unknown",
        )

        last_error = None
        for attempt in range(decl.retry_policy.max_retries + 1):
            try:
                if attempt > 0:
                    wait = min(
                        decl.retry_policy.backoff_base ** attempt,
                        decl.retry_policy.backoff_max,
                    )
                    logger.info(f"Retry {attempt}/{decl.retry_policy.max_retries} "
                                 f"for {request.capability} (wait={wait:.1f}s)")
                    time.sleep(wait)

                start = time.time()
                if request.timeout:
                    result = self._run_with_timeout(impl, request, decl, meta)
                else:
                    result = impl(**request.inputs)
                    if not isinstance(result, CapabilityResult):
                        result = CapabilityResult.ok(result)
                elapsed = (time.time() - start) * 1000
                meta.finish()
                meta.retry_count = attempt
                result.metadata = meta

                self.metrics.record(
                    capability=request.capability,
                    duration_ms=elapsed,
                    success=result.success,
                    cache_hit=False,
                    retry_count=attempt,
                    agent=request.agent.value,
                    mission_id=request.mission_id,
                )

                if result.success and cache_key:
                    ttl = decl.retry_policy.backoff_max if request.cache_ttl is None else request.cache_ttl
                    self._set_cached(cache_key, result, ttl=int(ttl))

                return result

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if not self._is_retryable(error_str, decl):
                    break
                logger.warning(f"Attempt {attempt + 1} failed for "
                               f"{request.capability}: {e}")

        meta.finish()
        meta.error = str(last_error)
        meta.retry_count = decl.retry_policy.max_retries
        result = CapabilityResult.fail(
            error=f"All {decl.retry_policy.max_retries + 1} attempts failed: {last_error}",
            retry_count=decl.retry_policy.max_retries,
        )
        result.metadata = meta

        self.metrics.record(
            capability=request.capability,
            duration_ms=meta.duration_ms or 0,
            success=False,
            cache_hit=False,
            retry_count=decl.retry_policy.max_retries,
            agent=request.agent.value,
            mission_id=request.mission_id,
        )
        return result

    def _run_with_timeout(self, impl: Callable, request: CapabilityRequest,
                          decl: CapabilityDeclaration,
                          meta: ExecutionMetadata) -> Any:
        result_container = []
        error_container = []

        def target():
            try:
                result_container.append(impl(**request.inputs))
            except Exception as e:
                error_container.append(e)

        thread = threading.Thread(target=target, daemon=True)
        timeout = request.timeout or 30.0
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TimeoutError(
                f"Capability '{request.capability}' timed out after {timeout}s"
            )
        if error_container:
            raise error_container[0]
        val = result_container[0]
        if not isinstance(val, CapabilityResult):
            val = CapabilityResult.ok(val)
        return val

    def _is_retryable(self, error_str: str, decl: CapabilityDeclaration) -> bool:
        for pattern in decl.retry_policy.retryable_errors:
            if pattern in error_str:
                return True
        return False

    def _cache_key(self, request: CapabilityRequest,
                   decl: CapabilityDeclaration) -> str:
        if decl.deterministic:
            raw = json.dumps({
                "capability": request.capability,
                "inputs": request.inputs,
            }, sort_keys=True, default=str)
        else:
            raw = json.dumps({
                "capability": request.capability,
                "inputs": request.inputs,
                "agent": request.agent.value,
            }, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[CapabilityResult]:
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry and entry.is_valid():
                return entry.value
            if entry:
                del self._cache[key]
            return None

    def _set_cached(self, key: str, result: CapabilityResult, ttl: int = 300) -> None:
        with self._cache_lock:
            self._cache[key] = CacheEntry(result, ttl=ttl)

    def invalidate_cache(self, capability: Optional[str] = None) -> int:
        with self._cache_lock:
            if capability:
                before = len(self._cache)
                self._cache = {
                    k: v for k, v in self._cache.items()
                    if not k.startswith(hashlib.sha256(
                        json.dumps({"capability": capability}).encode()
                    ).hexdigest()[:16])
                }
                return before - len(self._cache)
            else:
                count = len(self._cache)
                self._cache.clear()
                return count

    def cache_size(self) -> int:
        with self._cache_lock:
            return len(self._cache)
