from __future__ import annotations
import uuid
from typing import Any, Optional

from research_runtime.genome import MissionGenome, TaskAssignment
from research_runtime.persistence import RuntimeStore
from research_runtime.trust import TrustEngine


class MissionBroker:
    def __init__(self, store: RuntimeStore, trust_engine: TrustEngine):
        self.store = store
        self.trust = trust_engine

    def create_mission(self, objective: str, scope: str = "",
                       constraints: Optional[list[str]] = None,
                       required_confidence: float = 0.7,
                       allowed_capabilities: Optional[list[str]] = None,
                       required_evidence: int = 0,
                       priority: int = 5,
                       tags: Optional[list[str]] = None,
                       application: str = "generic") -> MissionGenome:
        genome = MissionGenome(
            objective=objective,
            scope=scope,
            constraints=constraints or [],
            required_confidence=required_confidence,
            allowed_capabilities=allowed_capabilities or [],
            required_evidence=required_evidence,
            priority=priority,
            tags=tags or [],
            application=application,
        )
        self.store.save_mission_genome(genome)
        return genome

    def assign_task(self, mission_id: str, capability: str,
                    inputs: Optional[dict] = None,
                    priority: int = 5,
                    confidence_threshold: float = 0.7) -> TaskAssignment:
        task = TaskAssignment(
            mission_id=mission_id,
            capability=capability,
            inputs=inputs or {},
            priority=priority,
            confidence_threshold=confidence_threshold,
        )
        self.store.save_task(task)
        return task

    def route_task(self, task: TaskAssignment) -> Optional[str]:
        agents = self.store.list_agent_genomes()
        if not agents:
            return None

        candidates = []
        for agent in agents:
            agent_id = agent.agent_id
            caps = agent.available_capabilities
            if caps and task.capability not in caps:
                continue

            reliability = self.trust.reliability_bayesian(agent_id, task.capability)
            trust_record = self.store.get_trust(agent_id, task.capability)
            latency = trust_record.get("avg_latency_ms", 1000.0)
            candidates.append({
                "agent_id": agent_id,
                "reliability": reliability,
                "latency": latency,
                "score": reliability - (latency / 100000.0),
            })

        if not candidates:
            return None

        best = max(candidates, key=lambda c: c["score"])
        return best["agent_id"]

    def claim_task(self, task_id: str, agent_id: str) -> bool:
        from datetime import datetime, timezone
        tasks = self.store.list_tasks()
        for task_data in tasks:
            if task_data.task_id != task_id:
                continue
            if task_data.status != "pending":
                return False
            task_data.status = "assigned"
            task_data.assigned_at = datetime.now(timezone.utc).isoformat()
            self.store.save_task(task_data)
            return True
        return False

    def complete_task(self, task_id: str, result: dict,
                      confidence: float = 0.0) -> None:
        from datetime import datetime, timezone
        tasks = self.store.list_tasks()
        for task_data in tasks:
            if task_data.task_id != task_id:
                continue
            task_data.status = "completed"
            task_data.completed_at = datetime.now(timezone.utc).isoformat()
            task_data.result_summary = result.get("summary", "")
            task_data.confidence_threshold = confidence
            self.store.save_task(task_data)
            return

    def fail_task(self, task_id: str, error: str) -> None:
        tasks = self.store.list_tasks()
        for task_data in tasks:
            if task_data.task_id != task_id:
                continue
            task_data.status = "failed"
            task_data.error = error
            task_data.retry_count += 1
            self.store.save_task(task_data)
            return

    def get_pending_tasks(self, mission_id: Optional[str] = None) -> list[dict]:
        tasks = self.store.list_tasks(mission_id)
        return [
            t.to_dict() for t in tasks
            if t.status == "pending"
        ]

    def get_active_missions(self) -> list[MissionGenome]:
        return self.store.list_mission_genomes(
            status="in_progress"
        )

    def get_mission(self, mission_id: str) -> Optional[MissionGenome]:
        return self.store.get_mission_genome(mission_id)

    def mission_summary(self, mission_id: str) -> dict:
        genome = self.store.get_mission_genome(mission_id)
        if not genome:
            return {"error": "mission not found"}

        tasks_list = self.store.list_tasks(mission_id)
        total = len(tasks_list)
        completed = sum(1 for t in tasks_list if t.status == "completed")
        failed = sum(1 for t in tasks_list if t.status == "failed")
        pending = sum(1 for t in tasks_list if t.status == "pending")

        return {
            "mission_id": mission_id,
            "objective": genome.objective,
            "state": genome.current_state,
            "application": genome.application,
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "created_at": genome.created_at,
        }
