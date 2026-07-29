from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class GraveyardEntry:
    idea: str
    reason: str
    mission_id: str
    source_model: str
    survivability_score: float
    axioms: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: list[str] = field(default_factory=list)
    resurrected: bool = False
    resurrection_count: int = 0


class IdeaGraveyard:
    def __init__(self):
        self._entries: list[GraveyardEntry] = []

    def bury(self, idea: str, reason: str, mission_id: str,
             source_model: str = "unknown",
             survivability_score: float = 0.0,
             axioms: Optional[list[str]] = None,
             tags: Optional[list[str]] = None) -> GraveyardEntry:
        entry = GraveyardEntry(
            idea=idea,
            reason=reason,
            mission_id=mission_id,
            source_model=source_model,
            survivability_score=survivability_score,
            axioms=axioms or [],
            tags=tags or [],
        )
        self._entries.append(entry)
        return entry

    def recall(self, tag: Optional[str] = None,
               min_survivability: float = 0.0,
               max_results: int = 10) -> list[GraveyardEntry]:
        matches = self._entries
        if tag:
            matches = [e for e in matches if tag in e.tags]
        if min_survivability > 0:
            matches = [e for e in matches if e.survivability_score >= min_survivability]
        matches.sort(key=lambda e: e.survivability_score, reverse=True)
        return matches[:max_results]

    def resurrect(self, idea_text: str) -> Optional[GraveyardEntry]:
        for entry in self._entries:
            if entry.idea == idea_text and not entry.resurrected:
                entry.resurrected = True
                entry.resurrection_count += 1
                return entry
        return None

    def stats(self) -> dict:
        total = len(self._entries)
        dead = sum(1 for e in self._entries if not e.resurrected)
        revived = sum(1 for e in self._entries if e.resurrected)
        avg_survivability = (
            sum(e.survivability_score for e in self._entries) / max(total, 1)
        )
        return {
            "total_buried": total,
            "currently_dead": dead,
            "resurrected": revived,
            "avg_survivability": round(avg_survivability, 3),
        }

    def clear(self) -> None:
        self._entries.clear()
