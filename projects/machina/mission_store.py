from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from core.types import Mission, MissionStatus, AgentRole
from memory.store import Store


class MissionStore:
    def __init__(self, store: Store):
        self.store = store

    def create(self, objective: str, scope: str = "",
               parent_question: str = "",
               confidence_target: float = 0.7,
               allowed_sources: list[str] | None = None,
               deliverables: list[str] | None = None,
               assigned_agents: list[AgentRole] | None = None,
               dependencies: list[str] | None = None,
               deadline: Optional[str] = None) -> Mission:
        mission = Mission(
            objective=objective,
            scope=scope,
            parent_question=parent_question,
            confidence_target=confidence_target,
            allowed_sources=allowed_sources or [],
            deliverables=deliverables or [],
            assigned_agents=assigned_agents or [],
            dependencies=dependencies or [],
            deadline=deadline,
        )
        self.store.save_mission(mission)
        return mission

    def get(self, mission_id: str) -> Optional[Mission]:
        return self.store.get_mission(mission_id)

    def update_status(self, mission_id: str, status: MissionStatus) -> None:
        mission = self.store.get_mission(mission_id)
        if mission:
            mission.status = status
            mission.updated_at = datetime.now(timezone.utc).isoformat()
            if status == MissionStatus.COMPLETED:
                mission.completed_at = mission.updated_at
            self.store.save_mission(mission)

    def assign_agent(self, mission_id: str, agent: AgentRole) -> None:
        mission = self.store.get_mission(mission_id)
        if mission and agent not in mission.assigned_agents:
            mission.assigned_agents.append(agent)
            mission.updated_at = datetime.now(timezone.utc).isoformat()
            self.store.save_mission(mission)

    def list_active(self) -> list[Mission]:
        return [
            m for m in self.store.list_missions()
            if m.status in (MissionStatus.ASSIGNED, MissionStatus.IN_PROGRESS, MissionStatus.UNDER_REVIEW)
        ]

    def list_by_status(self, status: MissionStatus) -> list[Mission]:
        return self.store.list_missions(status=status.value)

    def list_all(self) -> list[Mission]:
        return self.store.list_missions()

    def get_blocked(self) -> list[Mission]:
        return self.store.list_missions(status=MissionStatus.BLOCKED.value)
