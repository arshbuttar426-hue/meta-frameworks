from __future__ import annotations
import json
import logging
import statistics
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from capabilities.base import MetricPoint

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self):
        self._points: list[MetricPoint] = []
        self._lock = threading.Lock()
        self._start_time = time.time()

    def record(self, capability: str, duration_ms: float,
               success: bool = True, cache_hit: bool = False,
               retry_count: int = 0, agent: str = "",
               mission_id: Optional[str] = None) -> None:
        point = MetricPoint(
            capability=capability,
            duration_ms=duration_ms,
            success=success,
            cache_hit=cache_hit,
            retry_count=retry_count,
            agent=agent,
            mission_id=mission_id,
        )
        with self._lock:
            self._points.append(point)

    def query(self, capability: Optional[str] = None,
              agent: Optional[str] = None,
              limit: int = 1000) -> list[MetricPoint]:
        with self._lock:
            results = list(self._points)
        if capability:
            results = [p for p in results if p.capability == capability]
        if agent:
            results = [p for p in results if p.agent == agent]
        return results[-limit:]

    def stats(self, capability: Optional[str] = None) -> dict:
        points = self.query(capability=capability)
        if not points:
            return {"error": "No data"}

        durations = [p.duration_ms for p in points]
        success_count = sum(1 for p in points if p.success)
        cache_count = sum(1 for p in points if p.cache_hit)
        retry_total = sum(p.retry_count for p in points)
        agent_counts = defaultdict(int)
        for p in points:
            agent_counts[p.agent] += 1

        return {
            "total_calls": len(points),
            "success_rate": round(success_count / len(points) * 100, 1) if points else 0,
            "avg_duration_ms": round(statistics.mean(durations), 1) if durations else 0,
            "median_duration_ms": round(statistics.median(durations), 1) if durations else 0,
            "max_duration_ms": round(max(durations), 1) if durations else 0,
            "min_duration_ms": round(min(durations), 1) if durations else 0,
            "cache_hit_rate": round(cache_count / len(points) * 100, 1) if points else 0,
            "total_retries": retry_total,
            "top_agents": dict(sorted(agent_counts.items(), key=lambda x: -x[1])[:5]),
            "uptime_hours": round((time.time() - self._start_time) / 3600, 2),
        }

    def dashboard(self) -> str:
        all_stats = self.stats()
        lines = [
            "=== Capability Metrics Dashboard ===",
            f"Total calls: {all_stats.get('total_calls', 0)}",
            f"Success rate: {all_stats.get('success_rate', 0)}%",
            f"Avg duration: {all_stats.get('avg_duration_ms', 0)}ms",
            f"Cache hit rate: {all_stats.get('cache_hit_rate', 0)}%",
            f"Total retries: {all_stats.get('total_retries', 0)}",
            f"Uptime: {all_stats.get('uptime_hours', 0)}h",
            "",
            "--- Per Capability ---",
        ]

        with self._lock:
            caps = set(p.capability for p in self._points)

        for cap in sorted(caps):
            s = self.stats(cap)
            lines.append(
                f"  {cap}: {s.get('total_calls', 0)} calls, "
                f"{s.get('success_rate', 0)}% success, "
                f"{s.get('avg_duration_ms', 0)}ms avg"
            )

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "uptime_hours": round((time.time() - self._start_time) / 3600, 2),
            "total_points": len(self._points),
            "stats": self.stats(),
            "by_capability": {
                cap: self.stats(cap)
                for cap in sorted(set(p.capability for p in self._points))
            },
        }

    def export_json(self, path: str) -> None:
        data = self.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Metrics exported to {path}")
