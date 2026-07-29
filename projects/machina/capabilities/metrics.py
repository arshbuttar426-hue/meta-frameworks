import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self):
        self._records: list[dict] = []

    def record(self, capability: str = "", duration_ms: float = 0,
               success: bool = True, cache_hit: bool = False,
               retry_count: int = 0, agent: str = "",
               mission_id: Optional[str] = None) -> None:
        self._records.append({
            "capability": capability,
            "duration_ms": duration_ms,
            "success": success,
            "cache_hit": cache_hit,
            "retry_count": retry_count,
            "agent": agent,
            "mission_id": mission_id,
        })

    def summary(self) -> dict:
        total = len(self._records)
        if total == 0:
            return {"total_calls": 0}
        success = sum(1 for r in self._records if r["success"])
        cache_hits = sum(1 for r in self._records if r["cache_hit"])
        return {
            "total_calls": total,
            "successful": success,
            "failed": total - success,
            "success_rate": success / total if total > 0 else 0,
            "cache_hits": cache_hits,
        }
