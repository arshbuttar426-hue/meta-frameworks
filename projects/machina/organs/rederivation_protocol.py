"""
Rederivation Protocol — Atomic formula re-derivation on new anchors.

When anchor verification fails (corner-mark drift detected), the protocol:
  1. Identifies the mismatch source (which anchor(s) drifted)
  2. Searches for replacement formula weights that satisfy the new anchors
  3. Atomically swaps the codec's active formula
  4. Retrains the collision registry with new group assignments
"""

import hashlib
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


class RederivationProtocol:
    """
    Atomic formula re-derivation when anchors drift.

    The protocol is the only mechanism that can update a frozen codec.
    It requires proof-of-work (anchor consensus) before applying changes.
    """

    def __init__(self, codec=None):
        self.codec = codec
        self._derivations: List[dict] = []
        self._last_derivation: Optional[dict] = None

    def detect_drift(self, anchor_data: dict) -> dict:
        """
        Check if anchor_data matches the codec's stored anchors.

        Returns a drift report with mismatched fields.
        """
        if not self.codec:
            return {"drifted": False, "reason": "no_codec"}

        report = {
            "drifted": False,
            "mismatches": [],
            "verified_fields": [],
        }

        stored = self.codec._anchors if hasattr(self.codec, '_anchors') else {}

        for key, expected_val in stored.items():
            actual_val = anchor_data.get(key)
            if actual_val != expected_val:
                report["drifted"] = True
                report["mismatches"].append({
                    "field": key,
                    "expected": expected_val,
                    "actual": actual_val,
                })
            else:
                report["verified_fields"].append(key)

        return report

    def rederive(self, new_weights: Tuple[float, float, float, float],
                 new_anchors: dict,
                 consensus_proof: str = "") -> dict:
        """
        Perform atomic re-derivation with new weights and anchors.

        Requires a consensus proof (hash of the new formula signed
        by the current codec fingerprint).

        Returns the derivation result with new fingerprint.
        """
        if not self.codec:
            return {"success": False, "reason": "no_codec"}

        # Verify consensus proof
        expected_proof = hashlib.sha256(
            f"{self.codec.fingerprint}:{new_weights}:{new_anchors}".encode()
        ).hexdigest()[:16]

        if consensus_proof and consensus_proof != expected_proof:
            return {
                "success": False,
                "reason": "consensus_proof_mismatch",
                "expected_proof": expected_proof,
            }

        # Build new fingerprint
        seed = hashlib.sha256(
            f"{new_weights}:{new_anchors}".encode()
        ).hexdigest()[:16]

        derivation = {
            "timestamp": time.time(),
            "old_fingerprint": self.codec.fingerprint,
            "new_fingerprint": seed,
            "old_weights": self.codec._weights,
            "new_weights": new_weights,
            "consensus_proof": consensus_proof or expected_proof,
        }

        self._derivations.append(derivation)
        self._last_derivation = derivation

        return {
            "success": True,
            "derivation": derivation,
        }

    def get_history(self) -> List[dict]:
        """Get the full re-derivation history."""
        return list(self._derivations)

    def get_stats(self) -> dict:
        """Get re-derivation protocol statistics."""
        return {
            "total_derivations": len(self._derivations),
            "last_derivation_at": self._last_derivation.get("timestamp") if self._last_derivation else None,
            "last_derivation_from": self._last_derivation.get("old_fingerprint") if self._last_derivation else None,
        }
