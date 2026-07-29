# Copyright © 2026 Arsh Buttar. All rights reserved. Confidential and proprietary.
# Unauthorized copying, distribution, or use of this work is prohibited.

#!/usr/bin/env python3
"""
================================================================================
LLM FORENSIC INSTRUMENT — MAIN ENGINE
================================================================================
Detects behavioral drift in LLM outputs. Initializes all organs, runs the
analysis cycle, enforces trust boundaries.

PILLARS ENFORCED:
All five pillars are enforced by the organs themselves. The engine is just
the conductor — it never bypasses an organ's checks.

FLOW:
1. Config -> 2. Codec (text→signature) -> 3. Ingestion (sample→record) -> 4. Registry (cluster)
   -> 5. Feature Factory (extract features) -> 6. Validator (assess pattern) -> 7. Risk (trust score) -> 8. Telemetry
================================================================================
"""

import os, sys, time, signal
from typing import Dict, List, Optional, Any

# Ensure organs are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from organs.config_loader import ConfigLoader
from organs.forensic_codec import ForensicCodec, FrozenCodecError, AnchorMismatchError, CollisionGroup
from organs.ingestion_gateway import IngestionGateway, OutputRecord, OutputStatus
from organs.collision_registry import CollisionRegistry
from organs.feature_factory import FeatureFactory
from organs.forensic_validator import ForensicValidator, ValidatorResult, ParetoPattern
from organs.risk_manager import RiskManager, OutputSignal, TrustDecision, TrustLevel
from organs.rederivation_protocol import RederivationProtocol
from organs.telemetry import Telemetry

# ------------------------------------------------------------------------------
# ENGINE
# ------------------------------------------------------------------------------

class ForensicEngine:
    """
    Main orchestrator for LLM output forensics.
    One instance = one instrument monitoring one model/deployment.
    """

    def __init__(self, config_path: str = "config.json"):
        self.config = ConfigLoader(config_path)
        self.telemetry: Optional[Telemetry] = None

        # Initialize organs in dependency order
        self._init_codec()
        self._init_ingestion()
        self._init_registry()
        self._init_factory()
        self._init_validator()
        self._init_risk()
        self._init_rederivation()
        self._init_telemetry()

        self._running = False
        self._cycle_count = 0

    def _init_codec(self):
        """Initialize the behavioral signature codec."""
        try:
            self.codec = ForensicCodec()
            print("[ENGINE] Codec initialized: " + self.codec.fingerprint)
            print("[ENGINE] Anchors verified -- codec ACTIVE")
        except AnchorMismatchError as e:
            print("[ENGINE] CODEC ANCHOR MISMATCH: " + str(e))
            print("[ENGINE] System cannot start. Re-derivation required.")
            raise

    def _init_ingestion(self):
        """Initialize the output sampling airlock."""
        rate_limit = self.config.get("sampling_rate_limit", 60)
        buffer_max = self.config.get("buffer_max_size", 100)
        self.gateway = IngestionGateway(self.codec, rate_limit, buffer_max)
        print("[ENGINE] Ingestion gateway ready (rate_limit=" + str(rate_limit) + "/min)")

    def _init_registry(self):
        """Initialize collision-aware behavioral registry."""
        self.registry = CollisionRegistry(self.codec)
        print("[ENGINE] Behavior registry ready")

    def _init_factory(self):
        """Initialize feature factory."""
        self.factory = FeatureFactory(self.codec, self.registry)
        print("[ENGINE] Feature factory ready")

    def _init_validator(self):
        """Initialize behavioral pattern validator."""
        min_acc = self.config.get("min_accuracy", 0.505)
        lambda_c = self.config.get("lambda_complexity", 0.3)
        max_patterns = self.config.get("max_patterns", 100)

        self.validator = ForensicValidator(
            self.codec, self.registry, self.factory,
            min_accuracy=min_acc,
            lambda_complexity=lambda_c,
            balance_groups=True,
            max_patterns=max_patterns,
        )
        print("[ENGINE] Validator ready (min_acc=" + str(min_acc) + ", max_patterns=" + str(max_patterns) + ")")

    def _init_risk(self):
        """Initialize trust scoring engine."""
        min_conf = self.config.get("min_confidence", 0.3)
        drift_thresh = self.config.get("drift_threshold", 0.7)
        budget = self.config.get("trust_budget_per_group", 1000)

        self.risk = RiskManager(
            self.codec, self.factory,
            min_confidence=min_conf,
            drift_threshold=drift_thresh,
            trust_budget_per_group=budget,
        )
        print("[ENGINE] Risk manager ready (min_confidence=" + str(min_conf) + ", drift_threshold=" + str(drift_thresh) + ")")

    def _init_rederivation(self):
        """Initialize re-derivation protocol."""
        self.rederivation = RederivationProtocol(self.codec)
        print("[ENGINE] Re-derivation protocol ready")

    def _init_telemetry(self):
        """Initialize telemetry."""
        log_dir = self.config.get("log_dir", "./logs")
        max_log_mb = self.config.get("max_log_size_mb", 100)

        self.telemetry = Telemetry(self.codec, log_dir, max_log_mb)
        self.telemetry.verified_log(
            "ENGINE", "INIT", "LLM Forensic engine initialized",
            {
                "codec_fingerprint": self.codec.fingerprint,
                "codec_version": self.codec.version,
                "config_version": self.config.version,
            }
        )
        print("[ENGINE] Telemetry ready (log_dir=" + log_dir + ")")

    # ------------------------------------------------------------------
    # PUBLIC API — LLM Forensic Operations
    # ------------------------------------------------------------------

    def analyze_output(self, text: str, source: str = "manual") -> Dict:
        """
        Analyze a single LLM output through the full forensic pipeline.

        1. Ingestion gateway → behavioral signature + collision group
        2. Register in collision registry
        3. Compute features
        4. Log to telemetry

        Returns the complete forensic record.
        """
        # 1. Ingest through gateway
        record = self.gateway.ingest(text, source)

        # 2. Register behavior group
        self.registry.register(text, record.collision_group_id, source)

        # 3. Compute features
        features = self.factory.compute(text)

        # 4. Log
        if self.telemetry:
            self.telemetry.verified_log(
                "INGESTION", record.status.value,
                "Output from " + source + " analyzed",
                {
                    "source": source,
                    "collision_group": record.collision_group_id,
                    "quality_score": record.quality_score,
                    "length_chars": len(text),
                }
            )

        return {
            "record": record,
            "features": features,
            "registry_stats": self.registry.get_stats(),
            "gateway_stats": self.gateway.get_stats(),
        }

    def assess_behavior(self, outputs: List[tuple]) -> Dict:
        """
        Run behavioral assessment on a batch of LLM outputs.

        outputs: List of (source_label, output_text)
        """
        result = self.validator.evaluate(outputs)

        if self.telemetry:
            self.telemetry.verified_log(
                "VALIDATOR", "CYCLE_COMPLETE",
                "Assessment cycle " + str(result.cycle) + " complete",
                {
                    "cycle": result.cycle,
                    "patterns_evaluated": result.patterns_evaluated,
                    "patterns_passed": result.patterns_passed,
                    "pareto_size": len(result.pareto_front),
                    "anchored_present": result.anchored_present,
                    "best_error": result.best_error,
                    "best_pattern": result.best_pattern_id,
                }
            )

        return {
            "result": result,
            "pareto_patterns": [
                {
                    "id": p.pattern_id,
                    "desc": p.description,
                    "error": p.error,
                    "accuracy": p.accuracy,
                    "anchored": p.is_anchored,
                }
                for p in result.pareto_front
            ],
        }

    def score_trust(self, text: str, source: str = "unknown") -> Dict:
        """
        Full trust scoring pipeline: features → validator → risk manager.

        1. Compute features from output text
        2. Assess behavioral patterns via validator
        3. Build trust signal
        4. Evaluate via risk manager
        """
        # 1. Compute features
        features = self.factory.compute(text)

        # 2. Assess behavioral patterns
        assessment = self.validator.assess(text)

        # 3. Build output signal for trust engine
        group_id = features.get("collision_group_id", "uncertain")
        signal = OutputSignal(
            refusal_probability=features.get("refusal_probability", 0.0),
            output_quality=features.get("output_quality", 0.0),
            confidence=assessment["confidence"],
            collision_group_id=group_id,
            source=source,
            text_length=len(text),
        )

        # 4. Trust evaluation
        decision = self.risk.evaluate_output(signal)

        if self.telemetry:
            self.telemetry.verified_log(
                "RISK", "OUTPUT_EVALUATED",
                "Trust decision for output from " + source,
                {
                    "source": source,
                    "trust_level": decision.trust_level.value,
                    "score": decision.score,
                    "allowed": decision.allowed,
                    "reason": decision.reason,
                    "collision_group": group_id,
                }
            )

        return {
            "features": features,
            "assessment": assessment,
            "signal": signal,
            "trust_decision": decision,
            "allowed": decision.allowed,
        }

    def detect_drift(self, anchor_data: Optional[dict] = None) -> Dict:
        """
        Check for behavioral drift by verifying codec anchors.

        Returns drift report with mismatches if any anchors have drifted.
        """
        anchors = self.codec.get_anchors()
        drift_report = self.rederivation.detect_drift(
            anchor_data or {"root": anchors.get("root", "")}
        )

        # Also check current refusal rate via risk manager
        risk_stats = self.risk.get_stats()

        return {
            "anchor_drift": drift_report,
            "behavioral_drift": risk_stats.get("drift_detected", False),
            "drift_score": risk_stats.get("drift_score", 0.0),
            "system_healthy": not drift_report["drifted"] and not risk_stats.get("drift_detected", False),
        }

    def health_check(self) -> Dict:
        """Full system health check."""
        return {
            "codec": {
                "frozen": self.codec.is_frozen(),
                "fingerprint": self.codec.fingerprint,
                "version": self.codec.version,
            },
            "registry": self.registry.get_stats(),
            "gateway": self.gateway.get_stats(),
            "factory": self.factory.check_codec_health(),
            "validator": self.validator.check_health(),
            "risk": self.risk.get_stats(),
            "telemetry": self.telemetry.get_stats() if self.telemetry else {},
            "config": {
                "version": self.config.version,
                "fingerprint": self.config.fingerprint,
            },
        }

    def get_status(self) -> str:
        """One-line status."""
        h = self.health_check()
        if h["codec"]["frozen"]:
            return "FROZEN -- Codec alarm active"
        if h["risk"].get("drift_detected", False):
            return "DRIFT DETECTED -- Behavioral shift alert"
        return "ACTIVE -- Cycle " + str(self._cycle_count) + ", Pareto " + str(h["validator"]["pareto_size"]) + " patterns"

# ------------------------------------------------------------------------------
# CLI ENTRY POINT
# ------------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("LLM FORENSIC INSTRUMENT v2.0.0")
    print("=" * 60)

    # Ensure env vars
    if not os.environ.get("FORENSIC_CONFIG_KEY"):
        print("WARNING: FORENSIC_CONFIG_KEY not set. Config will not be HMAC-signed.")

    engine = ForensicEngine()
    print("")
    print(engine.get_status())
    print("")
    print("Engine ready. Use:")
    print("  engine.analyze_output(text, source)  — analyze a single LLM output")
    print("  engine.assess_behavior(outputs)      — batch behavioral assessment")
    print("  engine.score_trust(text, source)     — full trust scoring pipeline")
    print("  engine.detect_drift()                — check for anchor drift")

    return engine

if __name__ == "__main__":
    engine = main()
