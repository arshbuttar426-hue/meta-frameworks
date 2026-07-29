"""
Ingestion Gateway — Rate-limited LLM output sampling with behavioral checks.

Acts as the airlock. Every LLM output must pass:
  1. Rate limit check (token bucket)
  2. Codec behavioral signature computation
  3. Collision group classification
  4. Output quality assessment

Suspicious outputs are flagged for human review.
"""

import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional

from ...lib.rate_limit import token_refill


class OutputStatus(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    FLAGGED = "flagged"
    REJECTED = "rejected"


@dataclass
class OutputRecord:
    """Complete record for a sampled LLM output."""
    status: OutputStatus = OutputStatus.CLEAN
    behavioral_signature: tuple = ()
    collision_group_id: str = ""
    quality_score: float = 1.0
    source: str = ""
    text: str = ""
    reason: str = ""


class IngestionGateway:
    """
    Rate-limited LLM output ingestion with behavioral verification.

    Uses a token bucket for rate limiting. Each output consumes
    one token. Tokens refill at rate_limit per minute.
    """

    def __init__(self, codec, rate_limit: int = 60, max_buffer: int = 100):
        self.codec = codec
        self.rate_limit = rate_limit
        self.max_buffer = max_buffer

        # Token bucket state
        self._tokens = float(rate_limit)
        self._last_refill = time.time()

        # Statistics
        self._clean = 0
        self._suspicious = 0
        self._flagged = 0
        self._rejected = 0
        self._buffer: list = []

    def ingest(self, text: str, source: str = "unknown") -> OutputRecord:
        """
        Process an LLM output through the ingestion pipeline.

        Returns an OutputRecord with status, signature, and metadata.
        """
        # 1. Rate limit check
        self._refill_tokens()
        if self._tokens < 1.0:
            self._rejected += 1
            return OutputRecord(
                status=OutputStatus.REJECTED,
                reason="rate_limit_exceeded",
                source=source,
                text=text,
            )

        # 2. Compute behavioral signature
        signature = self.codec.encode(text)

        # 3. Classify collision group
        group_info = self.codec.collision_group(text)
        group_id = group_info["group_id"].value

        # 4. Quality assessment
        quality = self._assess_quality(text, signature)
        self._tokens -= 1.0

        # 5. Flag suspicious outputs
        if quality < 0.2:
            self._flagged += 1
            record = OutputRecord(
                status=OutputStatus.FLAGGED,
                behavioral_signature=signature,
                collision_group_id=group_id,
                quality_score=quality,
                source=source,
                text=text,
                reason="quality_below_threshold",
            )
            if len(self._buffer) < self.max_buffer:
                self._buffer.append(record)
            return record

        if group_id in ("refusal", "hallucination"):
            self._suspicious += 1
            return OutputRecord(
                status=OutputStatus.SUSPICIOUS,
                behavioral_signature=signature,
                collision_group_id=group_id,
                quality_score=quality,
                source=source,
                text=text,
                reason=f"behavior_group_{group_id}",
            )

        # 6. Accept
        self._clean += 1
        return OutputRecord(
            status=OutputStatus.CLEAN,
            behavioral_signature=signature,
            collision_group_id=group_id,
            quality_score=quality,
            source=source,
            text=text,
        )

    def _refill_tokens(self) -> None:
        """Refill token bucket based on elapsed time."""
        self._tokens, self._last_refill = token_refill(
            self._tokens, self.rate_limit, self._last_refill
        )

    def _assess_quality(self, text: str, signature: tuple) -> float:
        """
        Assess output quality based on behavioral signature.

        Quality is higher when:
          - Low refusal signal
          - High token diversity
          - Reasonable length
        """
        if not text or len(text.strip()) < 10:
            return 0.0

        d1_length = signature[1] if len(signature) > 1 else 0.5
        d2_diversity = signature[2] if len(signature) > 2 else 0.5
        d3_refusal = signature[3] if len(signature) > 3 else 0.0

        # Penalize extreme lengths
        length_bonus = 1.0 - abs(d1_length - 0.5) * 0.5

        # Reward diversity
        diversity_bonus = d2_diversity

        # Penalize refusal signals
        refusal_penalty = d3_refusal * 0.8

        return max(0.0, (length_bonus * 0.3 + diversity_bonus * 0.3 - refusal_penalty * 0.4))

    def drain_buffer(self) -> list:
        """Drain and return all buffered flagged outputs."""
        records = list(self._buffer)
        self._buffer.clear()
        return records

    def get_stats(self) -> dict:
        return {
            "clean": self._clean,
            "suspicious": self._suspicious,
            "flagged": self._flagged,
            "rejected": self._rejected,
            "buffer_size": len(self._buffer),
            "tokens_available": round(self._tokens, 1),
            "rate_limit": self.rate_limit,
        }
