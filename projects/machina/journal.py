from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from core.types import JournalEntry, AgentRole
from memory.store import Store


class Journal:
    def __init__(self, store: Store):
        self.store = store

    def write(self, agent: AgentRole, action: str, reason: str,
              input_summary: str = "", output_summary: str = "",
              confidence: float = 0.0, sources: list[str] | None = None,
              next_action: str = "", mission_id: Optional[str] = None,
              metadata: dict | None = None) -> JournalEntry:
        entry = JournalEntry(
            agent=agent,
            action=action,
            reason=reason,
            input_summary=input_summary[:500],
            output_summary=output_summary[:500],
            confidence=confidence,
            sources=sources or [],
            next_action=next_action,
            mission_id=mission_id,
            metadata=metadata or {},
        )
        self.store.save_journal(entry)
        return entry

    def recent(self, limit: int = 20, agent: Optional[str] = None) -> list[JournalEntry]:
        return self.store.get_journal(limit=limit, agent=agent)

    def for_mission(self, mission_id: str) -> list[JournalEntry]:
        return [
            e for e in self.store.get_journal(limit=10000)
            if e.mission_id == mission_id
        ]

    def timeline(self, mission_id: Optional[str] = None) -> str:
        entries = self.for_mission(mission_id) if mission_id else self.store.get_journal(limit=500)
        lines = []
        for e in entries:
            lines.append(
                f"[{e.timestamp}] {e.agent.value}: {e.action} "
                f"(conf={e.confidence:.2f})"
            )
        return "\n".join(lines)
