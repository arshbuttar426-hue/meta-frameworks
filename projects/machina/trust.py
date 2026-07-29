from __future__ import annotations
import math
from typing import Optional

from research_runtime.persistence import RuntimeStore


class TrustEngine:
    def __init__(self, store: RuntimeStore):
        self.store = store

    def record_outcome(self, agent: str, capability: str, success: bool,
                       latency_ms: float = 0.0, hallucinated: bool = False,
                       overridden: bool = False) -> None:
        self.store.update_trust(agent, capability, success, latency_ms,
                                hallucinated, overridden)

    def get_score(self, agent: str, capability: str) -> dict:
        return self.store.get_trust(agent, capability)

    def reliability_bayesian(self, agent: str, capability: str) -> float:
        trust = self.store.get_trust(agent, capability)
        successes = trust.get("successful_tasks", 0)
        failures = trust.get("failed_tasks", 0)
        alpha = successes + 1
        beta = failures + 1
        return alpha / (alpha + beta)

    def confidence_interval(self, agent: str, capability: str,
                            z: float = 1.96) -> tuple[float, float]:
        trust = self.store.get_trust(agent, capability)
        n = trust.get("total_tasks", 0)
        if n == 0:
            return (0.05, 0.95)
        successes = trust.get("successful_tasks", 0)
        p = successes / n
        se = math.sqrt(p * (1 - p) / n)
        lower = max(0.0, p - z * se)
        upper = min(1.0, p + z * se)
        return (round(lower, 3), round(upper, 3))

    def compare_agents(self, capability: str) -> list[dict]:
        agents = self.store.list_agent_genomes()
        results = []
        for agent in agents:
            score = self.reliability_bayesian(agent.agent_id, capability)
            trust = self.store.get_trust(agent.agent_id, capability)
            results.append({
                "agent": agent.agent_id,
                "role": agent.role.value,
                "reliability": round(score, 3),
                "total_tasks": trust.get("total_tasks", 0),
                "avg_latency_ms": trust.get("avg_latency_ms", 0.0),
            })
        return sorted(results, key=lambda r: r["reliability"], reverse=True)

    def best_agent_for(self, capability: str, min_tasks: int = 1) -> Optional[str]:
        agents = self.store.list_agent_genomes()
        best = None
        best_score = -1.0
        for agent in agents:
            trust = self.store.get_trust(agent.agent_id, capability)
            if trust.get("total_tasks", 0) < min_tasks:
                continue
            score = self.reliability_bayesian(agent.agent_id, capability)
            if score > best_score:
                best_score = score
                best = agent.agent_id
        return best

    def freshness_weight(self, agent: str, capability: str,
                         half_life_days: float = 7.0,
                         current_time: Optional[str] = None) -> float:
        from datetime import datetime, timezone
        trust = self.store.get_trust(agent, capability)
        updated_str = trust.get("last_updated", "")
        if not updated_str:
            return 0.5
        try:
            updated = datetime.fromisoformat(updated_str)
            now = (
                datetime.fromisoformat(current_time)
                if current_time else datetime.now(timezone.utc)
            )
            days_elapsed = (now - updated).total_seconds() / 86400.0
            decay = 2 ** (-days_elapsed / half_life_days)
            return round(decay, 3)
        except Exception:
            return 0.5
