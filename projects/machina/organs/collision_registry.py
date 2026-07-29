"""
Collision Registry — Group-indexed behavioral registry with thread-safe swap.

Tracks which LLM outputs fall into which behavioral groups. Supports:
- Group-indexed lookups by behavior group ID
- Thread-safe bulk operations
- Per-group size tracking
- Atomic swap for re-derivation updates
"""

import threading
from typing import Dict, List, Optional


class CollisionRegistry:
    """Group-indexed registry of behavioral patterns with thread-safe operations."""

    def __init__(self, codec=None):
        self.codec = codec
        self._lock = threading.RLock()
        self._groups: Dict[str, List[dict]] = {}
        self._source_index: Dict[str, str] = {}  # source → group_id
        self._total_records = 0

    def register(self, output_text: str, group_id: str,
                 source: str = "") -> str:
        """
        Register an LLM output into its behavioral collision group.

        Returns the group_id. Thread-safe.
        """
        with self._lock:
            # Build record
            record = {
                "text_preview": output_text[:100],
                "group_id": group_id,
                "source": source,
            }

            # Update group index
            if group_id not in self._groups:
                self._groups[group_id] = []
            self._groups[group_id].append(record)

            # Update source index
            if source:
                self._source_index[source] = group_id
            self._total_records += 1

            return group_id

    def get_group(self, group_id: str) -> List[dict]:
        """Get all records in a behavioral collision group."""
        return self._groups.get(group_id, [])

    def get_source_group(self, source: str) -> Optional[str]:
        """Get the behavioral group for a source."""
        return self._source_index.get(source)

    def swap_group(self, group_id: str, new_records: List[dict]) -> List[dict]:
        """
        Atomically replace all records in a behavioral group.

        Returns the old records. Thread-safe.
        """
        with self._lock:
            old = self._groups.get(group_id, [])
            # Remove old source index entries
            for record in old:
                src = record.get("source")
                if src and self._source_index.get(src) == group_id:
                    del self._source_index[src]

            self._groups[group_id] = new_records
            # Rebuild source index for new records
            for record in new_records:
                src = record.get("source")
                if src:
                    self._source_index[src] = group_id

            return old

    def get_stats(self) -> dict:
        """Get registry statistics."""
        with self._lock:
            return {
                "total_groups": len(self._groups),
                "total_records": self._total_records,
                "groups": {gid: len(recs) for gid, recs in self._groups.items()},
            }

    @property
    def total_groups(self) -> int:
        return len(self._groups)
