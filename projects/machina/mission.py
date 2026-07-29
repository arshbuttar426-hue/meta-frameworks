from __future__ import annotations
import json
import logging
from typing import Optional

from core.types import (
    AgentRole, Mission, MissionStatus, ResearchGrade,
    ResearchNote, KnowledgeNode, KnowledgeEdge,
)
from memory.store import Store
from memory.mission_store import MissionStore
from memory.journal import Journal
from llm.client import LLMClient
from agents.gemma import GemmaComposer

logger = logging.getLogger(__name__)


class MissionSystem:
    def __init__(self, store: Store, llm: LLMClient, journal: Journal):
        self.store = store
        self.missions = MissionStore(store)
        self.llm = llm
        self.journal = journal
        self.gemma = GemmaComposer(llm, journal)

    def formulate(self, question: str) -> Mission:
        self.journal.write(
            agent=AgentRole.GEMMA,
            action="formulate_mission",
            reason=f"New research question received: {question}",
            input_summary=question,
            next_action="plan_mission",
        )
        plan = self.gemma.plan_mission(question)
        if isinstance(plan, dict) and "objective" not in plan:
            plan = {"objective": question, "sub_tasks": [question]}

        if isinstance(plan, dict) and "error" in plan:
            objective = question
            scope = ""
            deliverables = []
        else:
            objective = plan.get("objective", question)
            scope = plan.get("scope", "")
            sub_tasks = plan.get("sub_tasks", [question])
            deliverables = plan.get("deliverables", sub_tasks)

        mission = self.missions.create(
            objective=objective,
            scope=scope,
            parent_question=question,
            deliverables=deliverables,
            assigned_agents=[
                AgentRole.GEMMA,
                AgentRole.SMOLM3,
                AgentRole.PHI4,
                AgentRole.VIBE,
            ],
        )
        self.journal.write(
            agent=AgentRole.GEMMA,
            action="mission_created",
            reason=f"Mission {mission.mission_id} defined and agents assigned",
            input_summary=question,
            output_summary=json.dumps({
                "mission_id": mission.mission_id,
                "objective": objective,
                "deliverables": deliverables,
            }),
            mission_id=mission.mission_id,
            next_action="evidence_collection",
        )
        return mission

    def add_note(self, mission_id: str, title: str, content: str,
                 agent: AgentRole) -> ResearchNote:
        note = ResearchNote(
            mission_id=mission_id,
            title=title,
            content=content,
            agent=agent,
        )
        self.store.save_note(note)
        return note

    def get_notes(self, mission_id: str) -> list[ResearchNote]:
        return self.store.get_notes(mission_id)

    def compute_mission_confidence(self, mission_id: str) -> float:
        notes = self.get_notes(mission_id)
        if not notes:
            return 0.0
        claims = self.store.search_claims(mission_id)
        if not claims:
            return 0.0
        confidences = [c.confidence for c in claims]
        return sum(confidences) / len(confidences)

    def update_status(self, mission_id: str, status: MissionStatus) -> None:
        self.missions.update_status(mission_id, status)

    def summarize(self, mission_id: str) -> dict:
        mission = self.missions.get(mission_id)
        if not mission:
            return {"error": "mission not found"}
        notes = self.get_notes(mission_id)
        claims = self.store.search_claims(mission.objective)
        return {
            "mission_id": mission.mission_id,
            "objective": mission.objective,
            "status": mission.status.value,
            "confidence": self.compute_mission_confidence(mission_id),
            "notes_count": len(notes),
            "claims_count": len(claims),
            "created": mission.created_at,
        }
