"""
Forensic Codec — Behavioral signature engine for LLM output forensics.

Encodes LLM completions into 4D behavioral signature vectors, assigns
semantic collision groups (REFUSAL, HALLUCINATION, FACTUAL, etc.), and
verifies anchor integrity for drift detection.

Key operations:
- encode(text): LLM text → 4D behavioral signature vector
- decode(signature): 4D vector → approximate text characteristics
- collision_group(text): classify output into semantic behavior group
- verify_anchor(): ensure baseline anchors haven't drifted
"""

from enum import Enum
import hashlib
import json
import math
import time
from typing import Dict, List, Optional, Tuple


class FrozenCodecError(Exception):
    """Raised when attempting to modify a frozen codec."""
    pass


class AnchorMismatchError(Exception):
    """Raised when anchor verification fails — baseline may have drifted."""
    pass


class CollisionGroup(str, Enum):
    """Semantic behavior groups for LLM outputs."""
    REFUSAL = "refusal"
    HALLUCINATION = "hallucination"
    FACTUAL = "factual"
    CREATIVE = "creative"
    ERROR = "error"
    UNCERTAIN = "uncertain"


class ForensicCodec:
    """
    Behavioral signature codec for LLM output forensics.

    Each LLM completion is:
      1. Encoded into a 4D behavioral signature via n-gram + distribution analysis
      2. Classified into a semantic collision group
      3. Verified against stored anchors for drift detection
    """

    # Refusal markers — patterns that suggest the model is refusing
    REFUSAL_PATTERNS = [
        "i cannot", "i can't", "i'm not able", "i am not able",
        "i'm sorry", "i am sorry", "unable to", "cannot fulfill",
        "i'm an ai", "as an ai", "as an ai language model",
        "i don't have", "i do not have", "against my guidelines",
        "i'm not programmed", "i wasn't designed", "it's not appropriate",
    ]

    # Hallucination markers — patterns that suggest fabricated content
    HALLUCINATION_PATTERNS = [
        "according to my research", "i recall that", "i remember reading",
        "in my database", "studies have shown that", "research indicates",
    ]

    def __init__(self, anchors: Optional[dict] = None):
        self._anchors = anchors or self._default_anchors()
        self._frozen = False
        self._created_at = time.time()
        self._signature_count = 0

        # Verify anchors on init
        if not self._verify_anchors():
            raise AnchorMismatchError("Anchor verification failed on init — baseline may have drifted")

        # Derive fingerprint from anchors
        seed = json.dumps(self._anchors, sort_keys=True)
        self.fingerprint = hashlib.sha256(seed.encode()).hexdigest()[:16]
        self.version = "2.0.0-llm-forensic"

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def encode(self, text: str) -> Tuple[float, float, float, float]:
        """
        Encode LLM output text into a 4D behavioral signature vector.

        Dimensions:
          d0: Style signature — character trigram hash score (captures writing patterns)
          d1: Length ratio — output length relative to baseline (0.0–1.0)
          d2: Token diversity — unique token ratio (captures repetitiveness)
          d3: Refusal signal — density of refusal/hallucination markers
        """
        if self._frozen:
            raise FrozenCodecError("Codec is frozen — cannot encode new outputs")

        d0 = self._compute_style_signature(text)
        d1 = self._compute_length_ratio(text)
        d2 = self._compute_token_diversity(text)
        d3 = self._compute_refusal_signal(text)

        self._signature_count += 1
        return (d0, d1, d2, d3)

    def decode(self, signature: Tuple[float, float, float, float]) -> dict:
        """
        Decode a 4D behavioral signature back to human-readable characteristics.

        Returns a dict describing what kind of LLM output would produce
        this signature.
        """
        d0, d1, d2, d3 = signature

        description = []
        if d3 > 0.5:
            description.append("likely refusal or guarded response")
        elif d3 > 0.2:
            description.append("possible hedging or uncertainty")
        else:
            description.append("direct response")

        if d2 < 0.3:
            description.append("highly repetitive")
        elif d2 > 0.7:
            description.append("highly diverse vocabulary")
        else:
            description.append("moderate vocabulary range")

        if d1 > 0.8:
            description.append("very long output")
        elif d1 < 0.2:
            description.append("very short output")

        return {
            "description": "; ".join(description),
            "style_score": round(d0, 4),
            "length_ratio": round(d1, 4),
            "diversity_score": round(d2, 4),
            "refusal_signal": round(d3, 4),
        }

    def collision_group(self, text: str) -> dict:
        """
        Classify an LLM output into a semantic behavior group.

        Returns dict with group_id, group name, and confidence.
        """
        text_lower = text.lower().strip()

        # Detect errors
        if not text or len(text) < 10:
            return {"group_id": CollisionGroup.ERROR, "confidence": 0.9}

        # Detect refusal
        refusal_hits = sum(1 for p in self.REFUSAL_PATTERNS if p in text_lower)
        if refusal_hits >= 2:
            return {"group_id": CollisionGroup.REFUSAL, "confidence": min(0.5 + 0.1 * refusal_hits, 0.95)}

        # Detect hallucination markers
        hallu_hits = sum(1 for p in self.HALLUCINATION_PATTERNS if p in text_lower)
        if hallu_hits >= 2:
            return {"group_id": CollisionGroup.HALLUCINATION, "confidence": min(0.5 + 0.1 * hallu_hits, 0.85)}

        # Detect factual vs creative by structure
        has_uncertainty = any(w in text_lower for w in ["maybe", "perhaps", "i think", "might", "could be", "possibly"])
        is_structured = any(c in text for c in ["\n1.", "\n- ", "\n* ", "**"])

        if has_uncertainty and not is_structured:
            return {"group_id": CollisionGroup.UNCERTAIN, "confidence": 0.6}

        if is_structured:
            return {"group_id": CollisionGroup.FACTUAL, "confidence": 0.7}

        return {"group_id": CollisionGroup.CREATIVE, "confidence": 0.6}

    # ------------------------------------------------------------------
    # Signature computation helpers
    # ------------------------------------------------------------------

    def _compute_style_signature(self, text: str) -> float:
        """
        Compute style signature using character trigram hashing.

        Returns a normalized score (0.0–1.0) representing the text's
        stylistic fingerprint.
        """
        if len(text) < 3:
            return 0.0

        trigrams = set()
        for i in range(len(text) - 2):
            trigram = text[i:i+3]
            h = hashlib.md5(trigram.encode()).hexdigest()[:4]
            trigrams.add(int(h, 16))

        # Normalize: more unique trigrams = more complex style
        max_trigrams = min(len(text) - 2, 1000)
        score = len(trigrams) / max(max_trigrams, 1)
        return min(1.0, score)

    def _compute_length_ratio(self, text: str) -> float:
        """Compute normalized length ratio (0.0–1.0)."""
        length = len(text)
        # Sigmoid-like normalization: 0 chars → 0, ~2000 chars → 0.5, 8000+ → 1.0
        return 1.0 / (1.0 + math.exp(-length / 2000 + 1.5))

    def _compute_token_diversity(self, text: str) -> float:
        """
        Compute token diversity score (0.0–1.0).

        Higher = more diverse vocabulary (less repetitive).
        """
        if not text.strip():
            return 0.0

        tokens = text.lower().split()
        if not tokens:
            return 0.0

        unique = len(set(tokens))
        total = len(tokens)
        return min(1.0, unique / max(total, 1) * 3.0)  # Scale: 33% unique → 1.0

    def _compute_refusal_signal(self, text: str) -> float:
        """
        Compute refusal signal density (0.0–1.0).

        Higher = more likely the output contains refusal or hedging.
        """
        text_lower = text.lower()

        # Count refusal pattern matches
        refusal_density = 0.0
        for pattern in self.REFUSAL_PATTERNS:
            count = text_lower.count(pattern)
            if count > 0:
                refusal_density += count * 0.15

        # Count hallucination markers
        for pattern in self.HALLUCINATION_PATTERNS:
            count = text_lower.count(pattern)
            if count > 0:
                refusal_density += count * 0.1

        return min(1.0, refusal_density)

    # ------------------------------------------------------------------
    # Anchor verification
    # ------------------------------------------------------------------

    def _default_anchors(self) -> dict:
        """Default anchor values for baseline LLM behavior."""
        return {
            "root": hashlib.sha256(b"llm-forensic-instrument-v2").hexdigest()[:16],
            "baseline_model": "unknown",
            "created_at": time.time(),
        }

    def _verify_anchors(self) -> bool:
        """Verify that internal anchors match expected values."""
        expected_root = hashlib.sha256(b"llm-forensic-instrument-v2").hexdigest()[:16]
        stored_root = self._anchors.get("root", "")
        return stored_root == expected_root

    def verify_anchor(self, anchor_data: Optional[dict] = None) -> bool:
        """Verify external anchor data against stored anchors."""
        if anchor_data is None:
            return self._verify_anchors()
        expected_root = hashlib.sha256(b"llm-forensic-instrument-v2").hexdigest()[:16]
        return anchor_data.get("root", "") == expected_root

    # ------------------------------------------------------------------
    # Freeze / state
    # ------------------------------------------------------------------

    def freeze(self) -> None:
        """Freeze the codec — prevents further encoding."""
        self._frozen = True

    def is_frozen(self) -> bool:
        return self._frozen

    def get_collision_group(self, text: str) -> dict:
        """Alias for collision_group — backward compatibility."""
        return self.collision_group(text)

    def get_anchors(self) -> dict:
        """Return a copy of the current anchors for verification."""
        return dict(self._anchors)

    def get_stats(self) -> dict:
        return {
            "signatures_computed": self._signature_count,
            "frozen": self._frozen,
            "fingerprint": self.fingerprint,
            "version": self.version,
        }

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "fingerprint": self.fingerprint,
            "version": self.version,
            "frozen": self._frozen,
            "anchor_root": self._anchors.get("root", ""),
            "created_at": self._created_at,
            "signatures_computed": self._signature_count,
        }
