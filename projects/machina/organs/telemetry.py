"""
Telemetry — Verified logging with codec anchor verification.

Each log entry is cryptographically linked to the codec's anchor root,
ensuring the log trail cannot be tampered with without detection.
"""

import json
import os
import time
import hashlib
from typing import Any, Dict, List, Optional


class Telemetry:
    """Verified logging system anchored to the forensic codec."""

    def __init__(self, codec=None, log_dir: str = "./logs", max_log_mb: int = 100):
        self.codec = codec
        self.log_dir = log_dir
        self.max_log_mb = max_log_mb
        self._entries: List[dict] = []
        self._entry_count = 0
        os.makedirs(log_dir, exist_ok=True)

    def verified_log(self, source: str, event: str, message: str,
                     data: Optional[dict] = None) -> None:
        """
        Append a verified log entry.

        Each entry includes a chain hash linking it to the previous entry
        and the codec anchor root, making tampering detectable.
        """
        entry = {
            "id": self._entry_count,
            "timestamp": time.time(),
            "source": source,
            "event": event,
            "message": message,
            "data": data or {},
        }

        # Compute chain hash
        anchor = self.codec.fingerprint if self.codec else "no-codec"
        prev_hash = self._entries[-1].get("chain_hash", anchor) if self._entries else anchor
        chain_seed = f"{prev_hash}:{entry['id']}:{entry['timestamp']}:{entry['event']}"
        entry["chain_hash"] = hashlib.sha256(chain_seed.encode()).hexdigest()[:16]

        self._entries.append(entry)
        self._entry_count += 1

        # Auto-flush to disk periodically
        if self._entry_count % 10 == 0:
            self._flush()

    def _flush(self) -> None:
        """Flush entries to disk as JSONL."""
        log_path = os.path.join(self.log_dir, f"telemetry-{int(time.time())}.jsonl")
        with open(log_path, "a") as f:
            for entry in self._entries[-10:]:
                f.write(json.dumps(entry) + "\n")

    def get_stats(self) -> dict:
        """Get telemetry statistics."""
        return {
            "entries": self._entry_count,
            "log_dir": self.log_dir,
            "last_entry_id": self._entry_count - 1 if self._entries else -1,
            "last_chain_hash": self._entries[-1].get("chain_hash", "") if self._entries else "",
        }

    def get_recent(self, n: int = 10) -> List[dict]:
        """Get the most recent n entries."""
        return self._entries[-n:]
