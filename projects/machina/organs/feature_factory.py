"""
Feature Factory — Computes behavioral features from LLM outputs.

Each LLM completion is analyzed for:
  - behavioral_signature: 4D codec signature (style, length, diversity, refusal)
  - collision_group: semantic behavior group (refusal, factual, creative, etc.)
  - refusal_probability: estimated likelihood of refusal
  - output_quality: coherence and structure score
"""

from typing import Optional, Tuple


class FeatureFactory:
    """Feature computation for LLM output forensics."""

    def __init__(self, codec=None, registry=None):
        self.codec = codec
        self.registry = registry
        self._features_computed = 0

    def compute(self, text: str) -> dict:
        """
        Compute behavioral features from an LLM output text.

        Returns a feature dict with:
          - behavioral_signature: 4D codec signature (d0–d3)
          - collision_group_id: semantic behavior group
          - group_size: how many outputs share this group
          - refusal_probability: estimated refusal likelihood (0.0–1.0)
          - output_quality: coherence/structure score (0.0–1.0)
          - length_chars: raw character count
        """
        if self.codec:
            signature = self.codec.encode(text)
            group_info = self.codec.collision_group(text)
            group_id = group_info["group_id"].value
        else:
            signature = (0.0, 0.0, 0.0, 0.0)
            group_id = "uncertain"

        # Look up group size from registry
        group_size = 1
        if self.registry:
            group_records = self.registry.get_group(group_id)
            group_size = len(group_records)

        # Compute refusal probability from signature d3
        refusal_probability = signature[3] if len(signature) > 3 else 0.0

        # Compute output quality (inverse of refusal + diversity bonus)
        diversity = signature[2] if len(signature) > 2 else 0.0
        output_quality = min(1.0, (1.0 - refusal_probability * 0.5) * (0.5 + diversity * 0.5))

        features = {
            "behavioral_signature": {
                "d0_style": round(signature[0], 4),
                "d1_length": round(signature[1], 4),
                "d2_diversity": round(signature[2], 4),
                "d3_refusal": round(signature[3], 4),
            },
            "collision_group_id": group_id,
            "group_size": group_size,
            "refusal_probability": round(refusal_probability, 4),
            "output_quality": round(output_quality, 4),
            "length_chars": len(text),
        }

        self._features_computed += 1
        return features

    def check_codec_health(self) -> dict:
        return {
            "status": "healthy",
            "features": self._features_computed,
            "codec_attached": self.codec is not None,
            "registry_attached": self.registry is not None,
        }
