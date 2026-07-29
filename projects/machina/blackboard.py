from __future__ import annotations
import uuid
from typing import Any, Optional

from research_runtime.persistence import RuntimeStore


class Blackboard:
    def __init__(self, store: RuntimeStore):
        self.store = store

    def write(self, mission_id: str, section: str, agent: str, content: str) -> str:
        entry_id = str(uuid.uuid4())
        content_hash = self.store.append_blackboard(
            entry_id=entry_id,
            mission_id=mission_id,
            section=section,
            agent=agent,
            content=content,
        )
        return f"{entry_id}:{content_hash}"

    def read(self, mission_id: str, section: Optional[str] = None) -> list[dict]:
        return self.store.read_blackboard(mission_id, section)

    def read_section(self, mission_id: str, section: str) -> list[dict]:
        return self.store.read_blackboard(mission_id, section)

    def get_entries_by_agent(self, mission_id: str, agent: str) -> list[dict]:
        all_entries = self.store.read_blackboard(mission_id)
        return [e for e in all_entries if e.get("agent") == agent]

    def summary(self, mission_id: str) -> dict:
        entries = self.store.read_blackboard(mission_id)
        sections = {}
        for e in entries:
            sec = e.get("section", "general")
            if sec not in sections:
                sections[sec] = {"count": 0, "agents": set()}
            sections[sec]["count"] += 1
            sections[sec]["agents"].add(e.get("agent", "unknown"))
        return {
            "mission_id": mission_id,
            "total_entries": len(entries),
            "sections": {
                k: {"count": v["count"], "agents": list(v["agents"])}
                for k, v in sections.items()
            },
        }
