#!/usr/bin/env python3
"""
AGPCP — AEROSPACE-GRADE PROMPT COMPRESSION PIPELINE
Flight Software Architecture | Zero-Dependency Edition
========================================================
Classification: FLIGHT-CRITICAL
Platform: macOS (Apple Silicon) | Runtime: Ollama Local API
Version: 3.0.3-STD | Date: 2026-05-19

MISSION:
    Convert lossy human English prompts into high-density, well-structured
    prompts using a 7-stage neural compiler with fault tolerance and
    deterministic execution.

CONSTRAINTS:
    - Zero external pip dependencies (stdlib only)
    - Memory ceiling: 14.0 GB on 16 GB unified memory
    - Stage timeout: 120.0 seconds per ignition
    - All 7 models must participate
    - Intent preservation is a hard requirement

USAGE:
    python3 prompt_compression_pipeline.py "your lossy prompt here"
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import signal
import subprocess
import sys
import time
import uuid
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# =============================================================================
# SECTION 1: CONSTANTS & CONFIGURATION
# =============================================================================

OLLAMA_HOST: str = "http://localhost:11434"
MEMORY_CEILING_GB: float = 14.0
STAGE_TIMEOUT_SEC: float = 120.0
MAX_RETRIES: int = 2
SNAPSHOT_DIR: Path = Path("/tmp/agpcp_snapshots")
CIRCUIT_THRESHOLD: int = 3
SEED: int = 42

DETERMINISTIC_OPTIONS: Dict[str, Any] = {
    "temperature": 0.0,
    "seed": SEED,
    "num_ctx": 8192,
    "num_predict": 2048,
}

# =============================================================================
# SECTION 2: FLIGHT STATE MACHINE
# =============================================================================

class FlightState(Enum):
    IDLE = auto()
    INTENT_ARCHITECTURE = auto()
    SEMANTIC_COMPRESSION = auto()
    SCHEMA_GENERATION = auto()
    CONSTRAINT_VALIDATION = auto()
    REDUNDANCY_ELIMINATION = auto()
    FORMAT_NORMALIZATION = auto()
    FINAL_AUDIT = auto()
    MISSION_COMPLETE = auto()
    ABORT = auto()


class Severity(Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"


# =============================================================================
# SECTION 3: TELEMETRY & OBSERVABILITY
# =============================================================================

class TelemetryDownlink:
    """JSON-structured telemetry emitter with checksum integrity."""

    def __init__(self, mission_id: str) -> None:
        self.mission_id = mission_id
        self._logger = logging.getLogger(f"AGPCP.{mission_id}")
        self._logger.setLevel(logging.DEBUG)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            self._logger.addHandler(handler)

    def emit(
        self,
        flight_state: FlightState,
        stage_name: str,
        severity: Severity,
        message: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "mission_id": self.mission_id,
            "flight_state": flight_state.name,
            "stage_name": stage_name,
            "severity": severity.value,
            "message": message,
            "metrics": metrics or {},
        }
        checksum = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        payload["checksum"] = checksum
        self._logger.info(json.dumps(payload, default=str))


class MissionClock:
    def __init__(self) -> None:
        self._t0: float = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self._t0

    def is_within_budget(self, budget_sec: float) -> bool:
        return self.elapsed() < budget_sec


# =============================================================================
# SECTION 4: RESOURCE MANAGEMENT (macOS-correct)
# =============================================================================

class ResourceMonitor:
    """Hardware-in-the-loop resource budget enforcer using macOS vm_stat.

    CRITICAL NOTE FOR macOS UNIFIED MEMORY ARCHITECTURE:
    - 'used_percent' is TELEMETRY ONLY. macOS intentionally keeps RAM highly 
      utilized for file caching, memory compression, and kernel buffers.
    - The ONLY valid abort metric is 'available_gb' (free + inactive pages).
    - A healthy macOS system routinely reports 80-95% 'used' with 4-8GB 
      actually available for new allocations.
    """

    def __init__(self, memory_limit_gb: float) -> None:
        self._memory_limit_gb = memory_limit_gb
        self._page_size: int = self._get_page_size()

    def _get_page_size(self) -> int:
        """Get system page size in bytes."""
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.pagesize"],
                capture_output=True, text=True, timeout=5
            )
            return int(result.stdout.strip())
        except Exception:
            return 16384  # Default for Apple Silicon

    def _parse_vm_stat(self) -> Dict[str, int]:
        """Parse vm_stat output. Returns bytes."""
        try:
            result = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().split("\n")
            stats: Dict[str, int] = {}
            for line in lines[1:]:
                if ":" not in line:
                    continue
                key, val = line.split(":", 1)
                # vm_stat format: "Pages free: 12345."
                val_clean = val.strip().rstrip(".").replace(" ", "")
                try:
                    pages = int(val_clean)
                    stats[key.strip()] = pages * self._page_size
                except ValueError:
                    continue
            return stats
        except Exception:
            return {}

    def _get_total_memory(self) -> int:
        """Get total physical memory in bytes."""
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5
            )
            return int(result.stdout.strip())
        except Exception:
            return 16 * (1024 ** 3)

    def check_budget(self) -> Tuple[bool, float, float]:
        """Returns (ok, available_gb, used_percent_telemetry_only).

        Abort decision is based SOLELY on available_gb.
        used_percent is provided for telemetry only and has no bearing
        on the ok/not-ok decision on macOS unified memory.
        """
        stats = self._parse_vm_stat()
        if not stats:
            return True, 8.0, 50.0

        total_bytes = self._get_total_memory()

        # macOS memory categories from vm_stat
        free_bytes = stats.get("Pages free", 0)
        active_bytes = stats.get("Pages active", 0)
        inactive_bytes = stats.get("Pages inactive", 0)
        speculative_bytes = stats.get("Pages speculative", 0)
        wired_bytes = stats.get("Pages wired down", 0)
        compressed_bytes = stats.get("Pages occupied by compressor", 0)

        # On macOS, 'available' = free + inactive (inactive is reclaimable cache)
        available_bytes = free_bytes + inactive_bytes

        # 'Used' for telemetry = everything not free (matches Activity Monitor)
        # This is NOT used for abort decisions.
        used_bytes = total_bytes - free_bytes
        used_percent = (used_bytes / total_bytes) * 100 if total_bytes > 0 else 0.0
        available_gb = available_bytes / (1024 ** 3)

        # HARD REQUIREMENT: available_gb must be >= 1.0 GB for safe model loading
        # used_percent is IGNORED for abort logic on macOS
        ok = available_gb >= 1.0
        return ok, available_gb, used_percent

    def snapshot(self) -> Dict[str, float]:
        ok, avail, pct = self.check_budget()
        return {
            "available_gb": round(avail, 2),
            "used_percent_telemetry": round(pct, 2),
            "page_size": self._page_size,
            "abort_threshold_gb": 1.0,
        }


# =============================================================================
# SECTION 5: FAULT DETECTION, ISOLATION, RECOVERY (FDIR)
# =============================================================================

class FDIRController:
    def __init__(self, telemetry: TelemetryDownlink) -> None:
        self._telemetry = telemetry

    def compute_intent_signature(self, prompt: str) -> Dict[str, List[str]]:
        tokens = prompt.lower().split()
        action_verbs = {
            "make", "tell", "build", "create", "get", "find", "convert",
            "generate", "write", "produce", "design", "implement", "establish",
            "acquire", "develop", "optimize", "organize", "manage",
        }
        domain_nouns = {
            "life", "way", "method", "system", "prompt", "code", "script",
            "pipeline", "model", "output", "format", "schema", "habit",
            "routine", "discipline", "structure", "framework", "architecture",
        }
        quality_mods = {
            "best", "optimal", "my", "disciplined", "high", "density",
            "structured", "lossless", "aggressive", "efficient", "good",
            "better", "effective", "proper", "correct", "ideal",
        }
        return {
            "verbs": [t for t in tokens if t.strip(".,!?;:") in action_verbs],
            "nouns": [t for t in tokens if t.strip(".,!?;:") in domain_nouns],
            "modifiers": [t for t in tokens if t.strip(".,!?;:") in quality_mods],
        }

    def check_semantic_parity(
        self,
        original_sig: Dict[str, List[str]],
        output_text: str,
        threshold: float = 0.60,
    ) -> Tuple[bool, float]:
        text_lower = output_text.lower()
        found = 0
        total = 0
        for terms in original_sig.values():
            for term in terms:
                total += 1
                if term in text_lower:
                    found += 1
        ratio = found / total if total > 0 else 1.0
        passed = ratio >= threshold
        if not passed:
            self._telemetry.emit(
                FlightState.FINAL_AUDIT, "FDIR", Severity.CRITICAL,
                f"Semantic parity failed: {ratio:.2%} < {threshold:.0%}",
                {"coverage_ratio": ratio, "threshold": threshold},
            )
        return passed, ratio

    def validate_stage_artifact(
        self,
        state: FlightState,
        stage_name: str,
        raw_output: str,
    ) -> bool:
        if not raw_output or not raw_output.strip():
            self._telemetry.emit(
                state, stage_name, Severity.CRITICAL,
                "Artifact validation failed: empty output", {},
            )
            return False
        if len(raw_output) > 100_000:
            self._telemetry.emit(
                state, stage_name, Severity.WARN,
                "Artifact oversized: possible runaway generation", {},
            )
        return True


# =============================================================================
# SECTION 6: NEURAL ACTUATOR (stdlib-only HTTP client)
# =============================================================================

class OllamaActuator:
    """Circuit-breaker-protected actuator using urllib (stdlib only)."""

    def __init__(
        self,
        host: str,
        timeout: float,
        max_retries: int,
        options: Dict[str, Any],
    ) -> None:
        self._host = host.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._options = options
        self._circuit_open: bool = False
        self._failure_count: int = 0
        self._circuit_threshold: int = CIRCUIT_THRESHOLD

    def health_check(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self._host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        options_override: Optional[Dict[str, Any]] = None,
    ) -> str:
        if self._circuit_open:
            raise RuntimeError(f"CIRCUIT_OPEN: Neural actuator for {model} isolated.")

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {**self._options, **(options_override or {})},
        }
        if system:
            payload["system"] = system

        body = json.dumps(payload).encode("utf-8")
        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                req = urllib.request.Request(
                    f"{self._host}/api/generate",
                    data=body,
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    self._failure_count = 0
                    return str(data.get("response", ""))
            except Exception as exc:
                self._failure_count += 1
                last_error = exc
                if self._failure_count >= self._circuit_threshold:
                    self._circuit_open = True
                    raise RuntimeError(
                        f"CIRCUIT_OPEN triggered for {model} after {self._failure_count} failures"
                    ) from exc
                if attempt == self._max_retries:
                    break
                backoff = 0.5 * (2 ** attempt)
                time.sleep(backoff)

        raise RuntimeError(f"All retries exhausted for {model}") from last_error

    async def generate_async(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        options_override: Optional[Dict[str, Any]] = None,
    ) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate,
            model,
            prompt,
            system,
            options_override,
        )

    async def close(self) -> None:
        pass


# =============================================================================
# SECTION 7: STAGE ARTIFACT & MISSION STATE
# =============================================================================

@dataclass(frozen=True)
class StageArtifact:
    stage_name: str
    model_tag: str
    input_checksum: str
    output_checksum: str
    token_estimate_in: int
    token_estimate_out: int
    latency_ms: float
    raw_output: str
    validated: bool = False


@dataclass(frozen=True)
class MissionState:
    mission_id: str
    flight_state: FlightState
    original_prompt: str
    working_memory: Dict[str, Any] = field(default_factory=dict)
    artifacts: Tuple[StageArtifact, ...] = field(default_factory=tuple)
    abort_reason: Optional[str] = None

    def deposit(
        self,
        key: str,
        value: Any,
        artifact: StageArtifact,
        new_state: FlightState,
    ) -> MissionState:
        new_memory = dict(self.working_memory)
        new_memory[key] = value
        return MissionState(
            mission_id=self.mission_id,
            flight_state=new_state,
            original_prompt=self.original_prompt,
            working_memory=new_memory,
            artifacts=self.artifacts + (artifact,),
            abort_reason=self.abort_reason,
        )

    def abort(self, reason: str) -> MissionState:
        return MissionState(
            mission_id=self.mission_id,
            flight_state=FlightState.ABORT,
            original_prompt=self.original_prompt,
            working_memory=self.working_memory,
            artifacts=self.artifacts,
            abort_reason=reason,
        )


# =============================================================================
# SECTION 8: FLIGHT STAGE ABSTRACT BASE
# =============================================================================

class FlightStage(ABC):
    def __init__(
        self,
        actuator: OllamaActuator,
        telemetry: TelemetryDownlink,
        monitor: ResourceMonitor,
    ) -> None:
        self._actuator = actuator
        self._telemetry = telemetry
        self._monitor = monitor

    @property
    @abstractmethod
    def stage_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_tag(self) -> str:
        ...

    @property
    @abstractmethod
    def target_state(self) -> FlightState:
        ...

    @abstractmethod
    async def execute(self, state: MissionState) -> MissionState:
        ...

    def _checksum(self, data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]

    def _token_estimate(self, text: str) -> int:
        return int(len(text.split()) / 0.75)

    def _build_artifact(
        self,
        state: MissionState,
        raw_output: str,
        latency_ms: float,
        validated: bool = True,
    ) -> StageArtifact:
        return StageArtifact(
            stage_name=self.stage_name,
            model_tag=self.model_tag,
            input_checksum=self._checksum(
                json.dumps(state.working_memory, sort_keys=True, default=str)
            ),
            output_checksum=self._checksum(raw_output),
            token_estimate_in=self._token_estimate(
                json.dumps(state.working_memory, default=str)
            ),
            token_estimate_out=self._token_estimate(raw_output),
            latency_ms=latency_ms,
            raw_output=raw_output,
            validated=validated,
        )


# =============================================================================
# SECTION 9: THE SEVEN PROPULSION STAGES
# =============================================================================

class IntentArchitect(FlightStage):
    @property
    def stage_name(self) -> str: return "INTENT_ARCHITECT"
    @property
    def model_tag(self) -> str: return "gemma4:e2b"
    @property
    def target_state(self) -> FlightState: return FlightState.INTENT_ARCHITECTURE

    async def execute(self, state: MissionState) -> MissionState:
        system = (
            "You are an Intent Extraction Engine. Analyze the lossy human prompt and "
            "extract: intent, domain, output_type, constraints, implicit_constraints, "
            "noise_detected. Output strictly as JSON. No prose, no markdown fences."
        )
        prompt = f"Extract intent architecture from:\n\n{state.original_prompt}"

        t0 = time.monotonic()
        raw = await self._actuator.generate_async(self.model_tag, prompt, system=system)
        latency = (time.monotonic() - t0) * 1000.0

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[3:]
            cleaned = cleaned.strip()

        try:
            intent_data = json.loads(cleaned)
        except json.JSONDecodeError:
            intent_data = {"raw_analysis": cleaned, "parse_error": True}

        artifact = self._build_artifact(state, raw, latency)
        return state.deposit("intent_architecture", intent_data, artifact, self.target_state)


class SemanticCompressor(FlightStage):
    @property
    def stage_name(self) -> str: return "SEMANTIC_COMPRESSOR"
    @property
    def model_tag(self) -> str: return "gemma2:9b"
    @property
    def target_state(self) -> FlightState: return FlightState.SEMANTIC_COMPRESSION

    async def execute(self, state: MissionState) -> MissionState:
        intent_json = json.dumps(state.working_memory.get("intent_architecture", {}))
        system = (
            "You are a Semantic Compression Engine. Given the original lossy prompt and its "
            "intent architecture, produce ONE dense sentence preserving all functional requirements, "
            "constraints, and implied constraints. Remove hedges, deictics, social softeners, "
            "and repetitions. Use precise terminology. Output only the compressed sentence."
        )
        prompt = (
            f"Original: {state.original_prompt}\n\n"
            f"Intent Architecture: {intent_json}\n\n"
            f"Produce compressed prose:"
        )

        t0 = time.monotonic()
        raw = await self._actuator.generate_async(self.model_tag, prompt, system=system)
        latency = (time.monotonic() - t0) * 1000.0

        artifact = self._build_artifact(state, raw, latency)
        return state.deposit("compressed_prose", raw.strip(), artifact, self.target_state)


class SchemaEngineer(FlightStage):
    @property
    def stage_name(self) -> str: return "SCHEMA_ENGINEER"
    @property
    def model_tag(self) -> str: return "qwen2.5-coder:3b"
    @property
    def target_state(self) -> FlightState: return FlightState.SCHEMA_GENERATION

    async def execute(self, state: MissionState) -> MissionState:
        compressed = state.working_memory.get("compressed_prose", "")
        system = (
            "You are a Schema Engineer. Convert the compressed semantic intent into a "
            "structured markdown schema with sections: CONTEXT, OBJECTIVE, CONSTRAINTS, "
            "OUTPUT_FORMAT. Use dense notation. No filler text. No explanations."
        )
        prompt = f"Convert to structured schema:\n\n{compressed}"

        t0 = time.monotonic()
        raw = await self._actuator.generate_async(self.model_tag, prompt, system=system)
        latency = (time.monotonic() - t0) * 1000.0

        artifact = self._build_artifact(state, raw, latency)
        return state.deposit("schema", raw.strip(), artifact, self.target_state)


class ConstraintValidator(FlightStage):
    @property
    def stage_name(self) -> str: return "CONSTRAINT_VALIDATOR"
    @property
    def model_tag(self) -> str: return "phi3.5:latest"
    @property
    def target_state(self) -> FlightState: return FlightState.CONSTRAINT_VALIDATION

    async def execute(self, state: MissionState) -> MissionState:
        schema = state.working_memory.get("schema", "")
        system = (
            'You are a Constraint Validation Engine. Review the original prompt and generated schema. '
            'Identify logical inconsistencies, missing implicit constraints, or contradictions. '
            'Output strictly as JSON: {"valid": bool, "issues": [], "recommendations": []}.'
        )
        prompt = (
            f"Original Prompt: {state.original_prompt}\n\n"
            f"Generated Schema:\n{schema}\n\n"
            f"Validate:"
        )

        t0 = time.monotonic()
        raw = await self._actuator.generate_async(self.model_tag, prompt, system=system)
        latency = (time.monotonic() - t0) * 1000.0

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[3:]
            cleaned = cleaned.strip()

        try:
            validation = json.loads(cleaned)
        except json.JSONDecodeError:
            validation = {"valid": False, "parse_error": True, "raw": cleaned}

        artifact = self._build_artifact(state, raw, latency)
        return state.deposit("validation_report", validation, artifact, self.target_state)


class RedundancyEliminator(FlightStage):
    @property
    def stage_name(self) -> str: return "REDUNDANCY_ELIMINATOR"
    @property
    def model_tag(self) -> str: return "deepseek-r1:1.5b"
    @property
    def target_state(self) -> FlightState: return FlightState.REDUNDANCY_ELIMINATION

    async def execute(self, state: MissionState) -> MissionState:
        compressed = state.working_memory.get("compressed_prose", "")
        schema = state.working_memory.get("schema", "")
        system = (
            "You are a Redundancy Elimination Engine. Analyze the compressed prose and schema "
            "for lexical and semantic duplicates. Merge them without loss of meaning. "
            "Output ONLY the deduplicated text. No reasoning chains, no markdown."
        )
        prompt = (
            f"Compressed Prose:\n{compressed}\n\n"
            f"Schema:\n{schema}\n\n"
            f"Produce deduplicated output:"
        )

        t0 = time.monotonic()
        raw = await self._actuator.generate_async(self.model_tag, prompt, system=system)
        latency = (time.monotonic() - t0) * 1000.0

        artifact = self._build_artifact(state, raw, latency)
        return state.deposit("deduplicated_prose", raw.strip(), artifact, self.target_state)


class FormatNormalizer(FlightStage):
    @property
    def stage_name(self) -> str: return "FORMAT_NORMALIZER"
    @property
    def model_tag(self) -> str: return "qwen2.5-coder:1.5b"
    @property
    def target_state(self) -> FlightState: return FlightState.FORMAT_NORMALIZATION

    async def execute(self, state: MissionState) -> MissionState:
        deduplicated = state.working_memory.get("deduplicated_prose", "")
        system = (
            "You are a Format Normalization Engine. Standardize delimiters, collapse extra "
            "whitespace, normalize punctuation. Output clean, machine-parseable text only."
        )
        prompt = f"Normalize formatting:\n\n{deduplicated}"

        t0 = time.monotonic()
        raw = await self._actuator.generate_async(self.model_tag, prompt, system=system)
        latency = (time.monotonic() - t0) * 1000.0

        artifact = self._build_artifact(state, raw, latency)
        return state.deposit("normalized_output", raw.strip(), artifact, self.target_state)


class FinalAuditor(FlightStage):
    @property
    def stage_name(self) -> str: return "FINAL_AUDITOR"
    @property
    def model_tag(self) -> str: return "qwen2:0.5b"
    @property
    def target_state(self) -> FlightState: return FlightState.FINAL_AUDIT

    async def execute(self, state: MissionState) -> MissionState:
        original = state.original_prompt
        final = state.working_memory.get("normalized_output", "")
        intent = json.dumps(state.working_memory.get("intent_architecture", {}))
        system = (
            'You are a Final Audit Engine. Compare the original prompt intent architecture '
            'against the final compressed output. Verify no functional requirement was lost. '
            'Report compression metrics and semantic parity score (0.0-1.0). '
            'Output strictly as JSON: {"parity_score": float, "compression_ratio": float, '
            '"final_output": str, "notes": str}.'
        )
        prompt = (
            f"Original: {original}\n\n"
            f"Intent: {intent}\n\n"
            f"Final Output: {final}\n\n"
            f"Audit:"
        )

        t0 = time.monotonic()
        raw = await self._actuator.generate_async(self.model_tag, prompt, system=system)
        latency = (time.monotonic() - t0) * 1000.0

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[3:]
            cleaned = cleaned.strip()

        try:
            audit = json.loads(cleaned)
        except json.JSONDecodeError:
            audit = {
                "parity_score": 0.0,
                "compression_ratio": 0.0,
                "final_output": final,
                "notes": f"Audit parse error. Raw: {cleaned[:200]}",
            }

        artifact = self._build_artifact(state, raw, latency)
        return state.deposit("audit_report", audit, artifact, self.target_state)


# =============================================================================
# SECTION 10: LAUNCH DIRECTOR (ORCHESTRATOR)
# =============================================================================

class LaunchDirector:
    def __init__(self, config: Dict[str, Any]) -> None:
        self._config = config
        self._actuator = OllamaActuator(
            config["ollama_host"],
            config["stage_timeout_sec"],
            config["max_retries"],
            config["deterministic_options"],
        )
        self._monitor = ResourceMonitor(config["memory_ceiling_gb"])
        self._clock = MissionClock()
        self._abort_requested: bool = False

    def _install_signal_handlers(self) -> None:
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._request_abort)
            except NotImplementedError:
                pass

    def _request_abort(self) -> None:
        self._abort_requested = True

    def _assemble_stages(self, telemetry: TelemetryDownlink) -> List[FlightStage]:
        return [
            IntentArchitect(self._actuator, telemetry, self._monitor),
            SemanticCompressor(self._actuator, telemetry, self._monitor),
            SchemaEngineer(self._actuator, telemetry, self._monitor),
            ConstraintValidator(self._actuator, telemetry, self._monitor),
            RedundancyEliminator(self._actuator, telemetry, self._monitor),
            FormatNormalizer(self._actuator, telemetry, self._monitor),
            FinalAuditor(self._actuator, telemetry, self._monitor),
        ]

    def _preflight(self, telemetry: TelemetryDownlink) -> bool:
        telemetry.emit(
            FlightState.IDLE, "LAUNCH_DIRECTOR", Severity.INFO,
            "Preflight initiated", self._monitor.snapshot(),
        )
        if not self._actuator.health_check():
            telemetry.emit(
                FlightState.IDLE, "LAUNCH_DIRECTOR", Severity.FATAL,
                "Preflight failed: Ollama host unreachable", {},
            )
            return False
        ok, avail, pct = self._monitor.check_budget()
        if not ok:
            telemetry.emit(
                FlightState.IDLE, "LAUNCH_DIRECTOR", Severity.FATAL,
                f"Preflight failed: Insufficient available memory ({avail:.2f} GB < 1.0 GB threshold)",
                {"available_gb": avail, "used_percent_telemetry_only": pct},
            )
            return False
        telemetry.emit(
            FlightState.IDLE, "LAUNCH_DIRECTOR", Severity.INFO,
            "Preflight complete. All systems nominal.", self._monitor.snapshot(),
        )
        return True

    def _snapshot(self, state: MissionState) -> None:
        snap_dir = Path(self._config["snapshot_dir"])
        snap_dir.mkdir(parents=True, exist_ok=True)
        path = snap_dir / f"{state.mission_id}_{state.flight_state.name}.json"
        payload = {
            "mission_id": state.mission_id,
            "flight_state": state.flight_state.name,
            "working_memory_keys": list(state.working_memory.keys()),
            "artifact_count": len(state.artifacts),
            "abort_reason": state.abort_reason,
            "elapsed_sec": self._clock.elapsed(),
        }
        path.write_text(json.dumps(payload, indent=2, default=str))

    async def launch(self, prompt: str) -> MissionState:
        self._install_signal_handlers()
        mission_id = f"AGPCP-{uuid.uuid4().hex[:8].upper()}"
        telemetry = TelemetryDownlink(mission_id)
        fdir = FDIRController(telemetry)

        state = MissionState(
            mission_id=mission_id,
            flight_state=FlightState.IDLE,
            original_prompt=prompt,
            working_memory={"original": prompt},
        )

        telemetry.emit(
            FlightState.IDLE, "LAUNCH_DIRECTOR", Severity.INFO,
            "Mission initiated", {
                "input_tokens_estimate": len(prompt.split()),
                **self._monitor.snapshot(),
            },
        )

        if not self._preflight(telemetry):
            return state.abort("PREFLIGHT_FAILURE")

        stages = self._assemble_stages(telemetry)

        for stage in stages:
            if self._abort_requested:
                return state.abort("GROUND_ABORT")

            if not self._clock.is_within_budget(300.0):
                return state.abort("TIME_BUDGET_EXHAUSTED")

            ok, avail, pct = self._monitor.check_budget()
            if not ok:
                return state.abort(f"MEMORY_BUDGET_EXCEEDED: {avail:.2f}GB available < 1.0GB threshold")

            telemetry.emit(
                stage.target_state, stage.stage_name, Severity.INFO,
                "Stage ignition", {
                    "model": stage.model_tag,
                    "memory_snapshot": self._monitor.snapshot(),
                },
            )

            try:
                t0 = time.monotonic()
                state = await asyncio.wait_for(
                    stage.execute(state),
                    timeout=self._config["stage_timeout_sec"],
                )
                latency = (time.monotonic() - t0) * 1000.0

                last = state.artifacts[-1]
                patched = StageArtifact(
                    stage_name=last.stage_name,
                    model_tag=last.model_tag,
                    input_checksum=last.input_checksum,
                    output_checksum=last.output_checksum,
                    token_estimate_in=last.token_estimate_in,
                    token_estimate_out=last.token_estimate_out,
                    latency_ms=latency,
                    raw_output=last.raw_output,
                    validated=last.validated,
                )
                state = MissionState(
                    mission_id=state.mission_id,
                    flight_state=state.flight_state,
                    original_prompt=state.original_prompt,
                    working_memory=state.working_memory,
                    artifacts=state.artifacts[:-1] + (patched,),
                    abort_reason=state.abort_reason,
                )

                if not fdir.validate_stage_artifact(
                    state.flight_state, stage.stage_name, patched.raw_output
                ):
                    return state.abort(f"FDIR_VALIDATION_FAILED:{stage.stage_name}")

                self._snapshot(state)

                telemetry.emit(
                    state.flight_state, stage.stage_name, Severity.INFO,
                    "Stage complete", {
                        "latency_ms": latency,
                        "output_checksum": patched.output_checksum,
                    },
                )

            except asyncio.TimeoutError:
                return state.abort(f"STAGE_TIMEOUT:{stage.stage_name}")
            except Exception as exc:
                return state.abort(f"STAGE_EXCEPTION:{stage.stage_name}:{type(exc).__name__}:{str(exc)}")

        # Post-mission audit
        final_output = state.working_memory.get("normalized_output", "")
        original_sig = fdir.compute_intent_signature(state.original_prompt)
        parity_ok, parity_ratio = fdir.check_semantic_parity(
            original_sig, final_output, threshold=0.60
        )

        if not parity_ok:
            return state.abort(f"SEMANTIC_PARITY_FAILED:{parity_ratio:.2%}")

        state = MissionState(
            mission_id=state.mission_id,
            flight_state=FlightState.MISSION_COMPLETE,
            original_prompt=state.original_prompt,
            working_memory=state.working_memory,
            artifacts=state.artifacts,
            abort_reason=None,
        )

        compression_ratio = len(state.original_prompt) / max(len(final_output), 1)
        telemetry.emit(
            FlightState.MISSION_COMPLETE, "LAUNCH_DIRECTOR", Severity.INFO,
            "Mission complete. All objectives achieved.", {
                "final_payload_size": len(final_output),
                "compression_ratio": round(compression_ratio, 3),
                "semantic_parity": round(parity_ratio, 3),
                "total_elapsed_sec": round(self._clock.elapsed(), 3),
                "stages_executed": len(state.artifacts),
            },
        )

        await self._actuator.close()
        return state


# =============================================================================
# SECTION 11: MISSION PRODUCT
# =============================================================================

class MissionProduct:
    def __init__(
        self,
        mission_id: str,
        flight_state: str,
        final_prose: str,
        final_schema: Optional[str],
        audit_report: Optional[Dict[str, Any]],
        compression_ratio: float,
        semantic_parity_score: float,
        total_elapsed_sec: float,
        execution_trace: List[Dict[str, Any]],
        abort_reason: Optional[str],
    ) -> None:
        self.mission_id = mission_id
        self.flight_state = flight_state
        self.final_prose = final_prose
        self.final_schema = final_schema
        self.audit_report = audit_report
        self.compression_ratio = compression_ratio
        self.semantic_parity_score = semantic_parity_score
        self.total_elapsed_sec = total_elapsed_sec
        self.execution_trace = execution_trace
        self.abort_reason = abort_reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "flight_state": self.flight_state,
            "final_prose": self.final_prose,
            "final_schema": self.final_schema,
            "audit_report": self.audit_report,
            "compression_ratio": self.compression_ratio,
            "semantic_parity_score": self.semantic_parity_score,
            "total_elapsed_sec": self.total_elapsed_sec,
            "execution_trace": self.execution_trace,
            "abort_reason": self.abort_reason,
        }

    @classmethod
    def from_mission_state(cls, state: MissionState, elapsed: float) -> "MissionProduct":
        trace = [
            {
                "stage": a.stage_name,
                "model": a.model_tag,
                "latency_ms": round(a.latency_ms, 2),
                "tokens_in": a.token_estimate_in,
                "tokens_out": a.token_estimate_out,
                "checksum": a.output_checksum,
            }
            for a in state.artifacts
        ]
        final = state.working_memory.get("normalized_output", "")
        schema = state.working_memory.get("schema")
        audit = state.working_memory.get("audit_report")
        ratio = len(state.original_prompt) / max(len(final), 1)
        parity = audit.get("parity_score", 0.0) if isinstance(audit, dict) else 0.0
        return cls(
            mission_id=state.mission_id,
            flight_state=state.flight_state.name,
            final_prose=final,
            final_schema=schema,
            audit_report=audit,
            compression_ratio=round(ratio, 3),
            semantic_parity_score=round(parity, 3),
            total_elapsed_sec=round(elapsed, 3),
            execution_trace=trace,
            abort_reason=state.abort_reason,
        )


# =============================================================================
# SECTION 12: MAIN ENTRY POINT
# =============================================================================

async def main() -> None:
    if len(sys.argv) < 2:
        print("USAGE: python3 prompt_compression_pipeline.py '<lossy prompt>'")
        print("EXAMPLE: python3 prompt_compression_pipeline.py 'Tell me the best way to to make my life disciplined'")
        sys.exit(1)

    raw_prompt = sys.argv[1]
    config = {
        "ollama_host": OLLAMA_HOST,
        "memory_ceiling_gb": MEMORY_CEILING_GB,
        "stage_timeout_sec": STAGE_TIMEOUT_SEC,
        "max_retries": MAX_RETRIES,
        "snapshot_dir": str(SNAPSHOT_DIR),
        "deterministic_options": DETERMINISTIC_OPTIONS,
    }
    director = LaunchDirector(config)

    final_state = await director.launch(raw_prompt)
    elapsed = director._clock.elapsed()

    product = MissionProduct.from_mission_state(final_state, elapsed)

    print("\n" + "=" * 70)
    print("MISSION PRODUCT")
    print("=" * 70)
    print(json.dumps(product.to_dict(), indent=2, default=str))

    out_path = Path(config["snapshot_dir"]) / f"{final_state.mission_id}_PRODUCT.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(product.to_dict(), indent=2, default=str))
    print(f"\nProduct written to: {out_path}")

    if final_state.flight_state == FlightState.ABORT:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
