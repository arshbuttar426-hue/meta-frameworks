"""
CCF Cube v1.0 — Constitutional Computation Framework applied to 5×5×5 Sensor Array
=================================================================================

Maps the Constitutional Computation Framework's 6 formally distinct layers
onto a 125-voxel sensor array (5 time horizons × 5 categories × 5 transformations).

CCF Layer Map:
  L1: Perception     → Raw canonical observations (25 values: 5×5 Raw)
  L2: Specialization → 4 independent narrow evaluators (Delta, Velocity, Duration, Turbulence)
  L3: Consensus      → Reconciliation of evaluator outputs with disagreement metrics
  L4: Governance     → Constitutional constraint checking (invariant rules)
  L5: Execution      → Authorized state transitions (hypothetical vs realized)
  L6: Persistence    → Causal provenance ledger (every transition links back)
  Observability      → Structural state exposure at every layer (not auxiliary)

No human axioms. No magic weights. No interpretation. No trading decisions.

All voxels: float32 in [0,1]. Complete 5×5×5 tensor every 100ms heartbeat.
"""

from __future__ import annotations

import enum
import math
import sqlite3
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

import sys as _sys  # noqa: E402 — used in hot-path persistence error handling

# ── Sequencer (independent forensic audit module) ────────────────
from sequencer_independent import (
    IndependentSequencer,
    SequencerFeatureFeed,
    SequencerLogEntry,
)

# ═══════════════════════════════════════════════════════════════════
# CONSTANTS & AXES
# ═══════════════════════════════════════════════════════════════════

# Time horizons in seconds (5 values → X-axis)
TIME_HORIZONS: List[int] = [1, 5, 30, 300, 3600]

# Category labels (5 values → Y-axis) — generic, user-remappable
CATEGORIES: List[str] = [
    "signal_0", "signal_1", "signal_2", "signal_3", "signal_4",
]

# Transformation labels (5 values → Z-axis)
#   [0] Raw        — canonical observation (perception)
#   [1] Delta      — rate of change (evaluator 1)
#   [2] Velocity   — directional momentum (evaluator 2)
#   [3] Duration   — state persistence (evaluator 3)
#   [4] Turbulence — local instability (evaluator 4)
TRANSFORMATIONS: List[str] = [
    "Raw", "Delta", "Velocity", "Duration", "Turbulence",
]

# Number of axes
N_TIME = 5
N_CAT = 5
N_TRANS = 5
N_VOXELS = N_TIME * N_CAT * N_TRANS  # 125

# Adaptive calibration: 24-hour half-life at 100ms ticks
ADAPTIVE_HALFLIFE_MS: int = 24 * 3600 * 1000
ADAPTIVE_ALPHA: float = 1.0 - math.exp(-100.0 / ADAPTIVE_HALFLIFE_MS)

# Duration hysteresis band (symmetric around threshold)
DURATION_BAND: float = 0.05

# Heartbeat interval
HEARTBEAT_INTERVAL_MS: float = 100.0

# Ring buffer capacity for short-window turbulence
MAX_RING_BUFFER_TICKS: int = 500

# EWMA smoothing alpha for raw values (per tick)
EMA_ALPHA: float = 0.001

# EWMSD alpha for volatility estimation
EWMSD_ALPHA: float = 0.01


# ═══════════════════════════════════════════════════════════════════
# GENERIC INPUT
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SensorInput:
    """
    Generic multi-channel sensor reading.

    Each element of `values` maps to one category in order.
    The cube treats all channels symmetrically — no channel is
    inherently special.  Adaptive calibration normalises each
    channel independently based on its own empirical distribution.

    Fields:
        values:      shape (5,) — one float per category, unbounded
        timestamp_ns: nanosecond timestamp (monotonic)
        sequence_id:  local monotonic counter
    """
    values: np.ndarray          # shape (5,), float64
    timestamp_ns: int
    sequence_id: int


# ═══════════════════════════════════════════════════════════════════
# CCF: LAYER OUTPUT DATACLASSES
# ═══════════════════════════════════════════════════════════════════

# ── L1: Perception ──────────────────────────────────────────────

@dataclass(frozen=True)
class PerceptionOutput:
    """
    Canonical observations produced by the Perception layer.

    Fields:
        perception_id:   unique identifier for this observation batch
        raw_cube_slice:  shape (5,5) — the Raw transformation values
        timestamp_ns:    observation timestamp
        sequence_id:     originating sequence counter
    """
    perception_id: str
    raw_cube_slice: np.ndarray   # (5,5)  float32
    timestamp_ns: int
    sequence_id: int


# ── L2: Specialization ──────────────────────────────────────────

class EvaluatorID(enum.Enum):
    DELTA = "delta"
    VELOCITY = "velocity"
    DURATION = "duration"
    TURBULENCE = "turbulence"
    SEQUENCER = "sequencer"


@dataclass(frozen=True)
class EvaluatorOutput:
    """
    Output from a single specialised evaluator.

    Each evaluator is intentionally narrow in scope.  It produces
    a structured report containing its observation, a confidence
    measure, a human-readable explanation, and the proposed state
    transition it recommends.

    Fields:
        evaluator_id:   which evaluator produced this output
        observation:    shape (5,5) — the evaluator's view of state
        confidence:     shape (5,5) — confidence in each voxel [0,1]
        explanation:    short text describing what the evaluator saw
        proposed_transition: shape (5,5) — the delta this evaluator
                            recommends applying to state
        transition_type: "update" | "reset" | "noop"
    """
    evaluator_id: EvaluatorID
    observation: np.ndarray         # (5,5) float32 [0,1]
    confidence: np.ndarray          # (5,5) float32 [0,1]
    explanation: str
    proposed_transition: np.ndarray  # (5,5) float32 unbounded
    transition_type: str             # "update" | "reset" | "noop"


# ── L3: Consensus ───────────────────────────────────────────────

@dataclass(frozen=True)
class ConsensusOutput:
    """
    Reconciled view from all evaluators, with explicit disagreement.

    Fields:
        consensus_id:     unique identifier
        reconciled_state: shape (5,5) — confidence-weighted consensus    uncertainty:      shape (5,5) — entropy-based uncertainty [0,1]
    conflict_matrix:  shape (4,4) — pairwise disagreement between
                      evaluators; 0 = perfect agreement, 1 = total
                      disagreement
    evaluator_count:  number of evaluators that participated
    disagreement_detail: str — text summary of where evaluators
                         diverged most
    proposed_transition: shape (5,5) — the consensus-recommended
                        state transition (delta), merged from all
                        evaluator proposals.  This is what gets
                        submitted to governance for authorisation.
    """
    consensus_id: str
    reconciled_state: np.ndarray        # (5,5) float32 [0,1]
    uncertainty: np.ndarray             # (5,5) float32 [0,1]
    conflict_matrix: np.ndarray         # (4,4) float32 [0,1]
    evaluator_count: int
    disagreement_detail: str
    proposed_transition: np.ndarray     # (5,5) float32 — the delta to apply


# ── L4: Governance ──────────────────────────────────────────────

@dataclass(frozen=True)
class GovernanceDecision:
    """
    Constitutional authorisation result.

    The Governance layer evaluates whether a proposed state transition
    is admissible under the system's invariant constraints.

    Fields:
        governance_id:    unique identifier
        authorized:       True if the transition passes all constraints
        reason:           explanation of the decision
        constraints_checked: list of constraint names that were evaluated
        proposed_state:   shape (5,5) — the state that was evaluated
    """
    governance_id: str
    authorized: bool
    reason: str
    constraints_checked: List[str]
    proposed_state: np.ndarray      # (5,5) float32


# ── L5: Execution ───────────────────────────────────────────────

@dataclass(frozen=True)
class ExecutionRecord:
    """
    Record of an enacted state transition.

    Distinguishes hypothetical trajectories (proposed but not enacted)
    from realized trajectories (enacted with external consequences).

    Fields:
        execution_id:     unique identifier
        transition_id:    linkable across layers
        previous_state:   shape (5,5) — state before transition
        new_state:        shape (5,5) — state after transition
        authorized:       True if governance approved
        timestamp_ns:     execution timestamp
        governance_id:    backlink to governance decision
    """
    execution_id: str
    transition_id: str
    previous_state: np.ndarray      # (5,5) float32
    new_state: np.ndarray           # (5,5) float32
    authorized: bool
    timestamp_ns: int
    governance_id: str


# ── L6: Persistence ─────────────────────────────────────────────

@dataclass(frozen=True)
class CausalRecord:
    """
    Full provenance chain for a single state transition.

    Every realized state can be traced backward through a complete
    chain of computational reasoning.

    Fields:
        record_id:        unique causal record ID
        transition_id:    links to the execution transition
        perception_id:    backlink to originating observation
        evaluator_ids:    list of evaluator outputs that participated
        consensus_id:     backlink to consensus
        governance_id:    backlink to governance decision
        execution_id:     backlink to execution record
        timestamp_ns:     when this record was committed
    """
    record_id: str
    transition_id: str
    perception_id: str
    evaluator_ids: List[str]
    consensus_id: str
    governance_id: str
    execution_id: str
    timestamp_ns: int


# ═══════════════════════════════════════════════════════════════════
# INTERNAL: Ring Buffer (short-window statistics)
# ═══════════════════════════════════════════════════════════════════

class _RingBuffer:
    """Fixed-size ring buffer for short-window statistics (<= 30s)."""

    __slots__ = ("buffer",)

    def __init__(self, max_size: int):
        self.buffer: deque = deque(maxlen=max_size)

    def append(self, value: float) -> None:
        self.buffer.append(value)

    def std(self) -> float:
        if len(self.buffer) < 2:
            return 0.0
        arr = np.array(self.buffer, dtype=np.float64)
        return float(np.std(arr, ddof=0))

    def __len__(self) -> int:
        return len(self.buffer)


# ═══════════════════════════════════════════════════════════════════
# L0: CUBE CORE — The mathematical substrate (preserved from v6.0)
# ═══════════════════════════════════════════════════════════════════

class CubeCore:
    """
    125-voxel sensor array with dual-clock update mechanics.

    Two clocks:
      • Per-tick:    updates Raw + Delta (on every SensorInput)
      • 100ms heartbeat: updates Velocity + Duration + Turbulence

    All internal math (EWMA, EWMSD, adaptive quantiles, duration
    hysteresis) is preserved from delt_v6.py but made generic by
    replacing fixed-cap normalisation with adaptive quantile-based
    scaling.

    The CubeCore is intentionally 'dead' — no interpretation, no
    weights, no decisions.  It only transforms signal → voxels.
    """

    __slots__ = (
        "cube", "prev_cube",
        "ema", "ewmsd",
        "duration", "duration_side", "duration_threshold",
        "delta_scale", "turbulence_cap",
        "quantile_95_delta", "quantile_95_turb",
        "quantile_95_raw", "raw_scale",
        "ring_buffers",
        "reference_ema",
        "last_sequence_id", "last_timestamp_ns",
        "tick_count", "heartbeat_count",
    )

    def __init__(self):
        # ── Cube state: [time, category, transformation] ─────────
        self.cube: np.ndarray = np.zeros((N_TIME, N_CAT, N_TRANS), dtype=np.float32)
        self.prev_cube: np.ndarray = np.zeros((N_TIME, N_CAT, N_TRANS), dtype=np.float32)

        # ── EMA states (per time × category) ─────────────────────
        self.ema: np.ndarray = np.zeros((N_TIME, N_CAT), dtype=np.float64)

        # ── EWMSD for volatility estimation ──────────────────────
        self.ewmsd: np.ndarray = np.zeros((N_TIME, N_CAT), dtype=np.float64)

        # ── Duration hysteresis state ────────────────────────────
        self.duration: np.ndarray = np.zeros((N_TIME, N_CAT), dtype=np.float32)
        self.duration_side: np.ndarray = np.zeros((N_TIME, N_CAT), dtype=np.int8)
        self.duration_threshold: np.ndarray = np.full((N_TIME, N_CAT), 0.5, dtype=np.float32)

        # ── Adaptive calibration parameters ──────────────────────
        self.delta_scale: np.ndarray = np.ones((N_TIME, N_CAT), dtype=np.float32)
        self.turbulence_cap: np.ndarray = np.ones((N_TIME, N_CAT), dtype=np.float32)
        self.quantile_95_delta: np.ndarray = np.full((N_TIME, N_CAT), 0.01, dtype=np.float64)
        self.quantile_95_turb: np.ndarray = np.full((N_TIME, N_CAT), 0.01, dtype=np.float64)

        # ── Adaptive raw-value scaling (replaces hardcoded caps) ─
        self.quantile_95_raw: np.ndarray = np.full((N_TIME, N_CAT), 1.0, dtype=np.float64)
        self.raw_scale: np.ndarray = np.ones((N_TIME, N_CAT), dtype=np.float32)

        # ── Ring buffers for short-window turbulence ─────────────
        self.ring_buffers: Dict[Tuple[int, int], _RingBuffer] = {}
        for ti in range(min(3, N_TIME)):
            for ci in range(N_CAT):
                self.ring_buffers[(ti, ci)] = _RingBuffer(MAX_RING_BUFFER_TICKS)

        # ── Reference EMA (rolling average of category_0) ────────
        self.reference_ema: float = 0.0

        # ── Sequence tracking ────────────────────────────────────
        self.last_sequence_id: int = 0
        self.last_timestamp_ns: int = 0

        # ── Counters ─────────────────────────────────────────────
        self.tick_count: int = 0
        self.heartbeat_count: int = 0

    # ── Static helpers ───────────────────────────────────────────

    @staticmethod
    def _clamp(val: float) -> float:
        return max(0.0, min(1.0, float(val)))

    @staticmethod
    def _update_ema(old: float, new_val: float, alpha: float) -> float:
        return alpha * new_val + (1.0 - alpha) * old

    @staticmethod
    def _update_ewmsd(old_var: float, new_val: float, alpha: float) -> float:
        return alpha * (new_val * new_val) + (1.0 - alpha) * old_var

    @staticmethod
    def _update_quantile(old_q: float, new_val: float, alpha: float) -> float:
        """Exponentially weighted 95th percentile approximation."""
        if new_val > old_q:
            return old_q + alpha * (new_val - old_q) * 20.0  # faster rise
        else:
            return old_q * (1.0 - alpha * 0.01)              # slow decay

    # ── Per-tick ingestion ───────────────────────────────────────

    def ingest(self, inp: SensorInput) -> None:
        """
        Ingest a single sensor reading.

        Updates:
          • Raw transformation (canonical observation)
          • Delta transformation (rate of change)
          • Adaptive calibration parameters (quantiles, scales)

        Called on every tick.  Heartbeat-independent.
        """
        self.tick_count += 1
        self.last_sequence_id = inp.sequence_id
        self.last_timestamp_ns = inp.timestamp_ns

        values = inp.values.astype(np.float64)  # (5,)

        # Update reference EMA (running average of category_0)
        if self.reference_ema == 0.0:
            self.reference_ema = float(values[0])
        else:
            self.reference_ema = self._update_ema(
                self.reference_ema, float(values[0]), EMA_ALPHA,
            )

        # Save previous cube for Delta computation
        self.prev_cube[:] = self.cube

        # ── Compute raw values per (time, category) ──────────────
        ref = self.reference_ema if abs(self.reference_ema) > 1e-12 else 1.0

        for ti in range(N_TIME):
            for ci in range(N_CAT):
                raw_val = float(values[ci])

                # Update EW quantile for raw values (adaptive cap)
                abs_raw = abs(raw_val)
                self.quantile_95_raw[ti, ci] = self._update_quantile(
                    self.quantile_95_raw[ti, ci], abs_raw, ADAPTIVE_ALPHA,
                )

                # Adaptive raw scaling: 95th percentile maps to ~0.9
                target_raw_scale = 0.9 / max(self.quantile_95_raw[ti, ci], 1e-12)
                self.raw_scale[ti, ci] = self._clamp(
                    self.raw_scale[ti, ci] * (1.0 - ADAPTIVE_ALPHA)
                    + target_raw_scale * ADAPTIVE_ALPHA,
                )

                scaled = raw_val * float(self.raw_scale[ti, ci])
                self.cube[ti, ci, 0] = self._clamp(scaled * 0.5 + 0.5)

        # ── Compute Delta (rate of change) ────────────────────────
        for ti in range(N_TIME):
            for ci in range(N_CAT):
                raw_delta = float(self.cube[ti, ci, 0]) - float(self.prev_cube[ti, ci, 0])

                # Update quantile for delta (adaptive scaling)
                self.quantile_95_delta[ti, ci] = self._update_quantile(
                    self.quantile_95_delta[ti, ci], abs(raw_delta), ADAPTIVE_ALPHA,
                )

                target_scale = 1.0 / max(self.quantile_95_delta[ti, ci] * 10.0, 0.001)
                self.delta_scale[ti, ci] = self._clamp(
                    self.delta_scale[ti, ci] * (1.0 - ADAPTIVE_ALPHA)
                    + target_scale * ADAPTIVE_ALPHA,
                )

                scaled_delta = raw_delta * float(self.delta_scale[ti, ci]) * 0.5 + 0.5
                self.cube[ti, ci, 1] = self._clamp(scaled_delta)

                # Feed ring buffer for turbulence (short windows only)
                if ti < 3:
                    self.ring_buffers[(ti, ci)].append(raw_delta)

    # ── Heartbeat (100ms) ─────────────────────────────────────────

    def heartbeat(self) -> float:
        """
        100ms periodic update.

        Computes:
          • Velocity   — directional momentum per time window
          • Duration   — persistence with hysteresis
          • Turbulence — local instability (std-dev based)

        Returns latency in milliseconds.
        """
        start = time.perf_counter()
        self.heartbeat_count += 1

        for ti in range(N_TIME):
            window_s = TIME_HORIZONS[ti]

            for ci in range(N_CAT):
                raw = float(self.cube[ti, ci, 0])
                delta = float(self.cube[ti, ci, 1]) - 0.5  # de-center

                # ── Velocity ─────────────────────────────────────
                vel = delta / max(window_s, 1) * float(self.delta_scale[ti, ci]) * 0.5 + 0.5
                self.cube[ti, ci, 2] = self._clamp(vel)

                # ── Duration with hysteresis ─────────────────────
                threshold = float(self.duration_threshold[ti, ci])

                if raw > threshold + DURATION_BAND:
                    new_side = 1
                elif raw < threshold - DURATION_BAND:
                    new_side = -1
                else:
                    new_side = int(self.duration_side[ti, ci])

                if new_side == self.duration_side[ti, ci] and new_side != 0:
                    self.duration[ti, ci] += 0.1  # one heartbeat
                elif new_side == 0:
                    pass  # hysteresis band — maintain
                else:
                    self.duration[ti, ci] = 0.0
                    self.duration_side[ti, ci] = new_side

                max_dur = float(
                    window_s * 10 if window_s < 300
                    else (300 if window_s == 300 else 3600)
                )
                self.cube[ti, ci, 3] = self._clamp(self.duration[ti, ci] / max_dur)

                # ── Turbulence ───────────────────────────────────
                if ti < 3 and (ti, ci) in self.ring_buffers:
                    turb = self.ring_buffers[(ti, ci)].std()
                else:
                    turb = abs(delta) * math.sqrt(window_s)

                self.quantile_95_turb[ti, ci] = self._update_quantile(
                    self.quantile_95_turb[ti, ci], turb, ADAPTIVE_ALPHA,
                )

                target_cap = self.quantile_95_turb[ti, ci] * 2.0
                self.turbulence_cap[ti, ci] = self._clamp(
                    self.turbulence_cap[ti, ci] * (1.0 - ADAPTIVE_ALPHA)
                    + float(target_cap) * ADAPTIVE_ALPHA,
                )

                if self.turbulence_cap[ti, ci] > 0:
                    turb_norm = turb / float(self.turbulence_cap[ti, ci])
                else:
                    turb_norm = 0.0

                self.cube[ti, ci, 4] = self._clamp(turb_norm)

        latency_ms = (time.perf_counter() - start) * 1000.0
        return latency_ms

    # ── Accessors ────────────────────────────────────────────────

    def get_raw_slice(self) -> np.ndarray:
        """Return the Raw transformation (5×5) — canonical observations."""
        return self.cube[:, :, 0].copy()

    def get_delta_slice(self) -> np.ndarray:
        """Return the Delta transformation (5×5)."""
        return self.cube[:, :, 1].copy()

    def get_velocity_slice(self) -> np.ndarray:
        """Return the Velocity transformation (5×5)."""
        return self.cube[:, :, 2].copy()

    def get_duration_slice(self) -> np.ndarray:
        """Return the Duration transformation (5×5)."""
        return self.cube[:, :, 3].copy()

    def get_turbulence_slice(self) -> np.ndarray:
        """Return the Turbulence transformation (5×5)."""
        return self.cube[:, :, 4].copy()

    @property
    def full_cube(self) -> np.ndarray:
        """Return the complete 5×5×5 tensor (read-only copy)."""
        return self.cube.copy()

    @property
    def valid(self) -> bool:
        """True if all 125 voxels are finite and in [0, 1]."""
        return bool(
            np.all(np.isfinite(self.cube))
            and np.all(self.cube >= 0.0)
            and np.all(self.cube <= 1.0)
        )


# ═══════════════════════════════════════════════════════════════════
# L1: PERCEPTION — Canonical observation layer
# ═══════════════════════════════════════════════════════════════════

class PerceptionLayer:
    """
    Constitutional Computation Framework — Layer 1: Perception

    Establishes canonical observations from raw sensor input.
    Functions as the boundary between the environment and the
    computational domain.

    Every downstream process operates upon these observations
    rather than raw environmental signals.  No decision-making.
    """

    __slots__ = ("cube",)

    def __init__(self, cube: CubeCore):
        self.cube: CubeCore = cube

    def observe(self, inp: SensorInput) -> PerceptionOutput:
        """
        Ingest a sensor reading and produce canonical observations.

        Returns a PerceptionOutput that all downstream layers
        will reference as the authoritative observation.
        """
        self.cube.ingest(inp)

        return PerceptionOutput(
            perception_id=str(uuid.uuid4()),
            raw_cube_slice=self.cube.get_raw_slice(),
            timestamp_ns=inp.timestamp_ns,
            sequence_id=inp.sequence_id,
        )

    def observe_batch(self, inputs: List[SensorInput]) -> PerceptionOutput:
        """
        Ingest a batch of sensor readings (burst) and produce
        the final canonical observation.
        """
        for inp in inputs:
            self.cube.ingest(inp)

        last = inputs[-1]
        return PerceptionOutput(
            perception_id=str(uuid.uuid4()),
            raw_cube_slice=self.cube.get_raw_slice(),
            timestamp_ns=last.timestamp_ns,
            sequence_id=last.sequence_id,
        )

    # ── Observability ────────────────────────────────────────────
    @property
    def state(self) -> Dict[str, object]:
        return {
            "layer": "perception",
            "raw_slice_shape": (N_TIME, N_CAT),
            "valid": self.cube.valid,
            "last_sequence": self.cube.last_sequence_id,
        }


# ═══════════════════════════════════════════════════════════════════
# L2: SPECIALIZATION — Independent narrow evaluators
# ═══════════════════════════════════════════════════════════════════

class DeltaEvaluator:
    """
    Specialized evaluator: measures rate-of-change.

    Scope: narrow — only assesses how quickly values are changing.
    Produces confidence based on the stability of the delta signal.
    """

    __slots__ = ()

    def evaluate(self, cube: CubeCore, perception: PerceptionOutput) -> EvaluatorOutput:
        raw = cube.get_raw_slice()
        delta = cube.get_delta_slice()

        # Confidence: high when delta is moderate (not saturated)
        confidence = 1.0 - np.abs(delta - 0.5) * 2.0  # [0,1]
        confidence = np.clip(confidence, 0.0, 1.0)

        # Proposed transition: the delta itself (what's changing)
        proposed = (delta - 0.5) * 2.0  # de-center

        # Determine transition type
        max_abs_delta = float(np.max(np.abs(delta - 0.5)))
        if max_abs_delta > 0.05:
            ttype = "update"
        elif max_abs_delta > 0.01:
            ttype = "noop"
        else:
            ttype = "noop"

        return EvaluatorOutput(
            evaluator_id=EvaluatorID.DELTA,
            observation=delta.copy(),
            confidence=confidence.astype(np.float32),
            explanation=(
                f"Delta range: [{float(np.min(delta)):.3f}, {float(np.max(delta)):.3f}], "
                f"mean confidence: {float(np.mean(confidence)):.3f}"
            ),
            proposed_transition=proposed.astype(np.float32),
            transition_type=ttype,
        )


class VelocityEvaluator:
    """
    Specialized evaluator: measures directional momentum.

    Scope: narrow — only assesses whether movements have
    persistent direction (trending vs oscillating).
    """

    __slots__ = ()

    def evaluate(self, cube: CubeCore, perception: PerceptionOutput) -> EvaluatorOutput:
        velocity = cube.get_velocity_slice()
        raw = cube.get_raw_slice()

        # Confidence: high when velocity is clearly directional
        confidence = np.abs(velocity - 0.5) * 2.0  # [0,1]
        confidence = np.clip(confidence, 0.0, 1.0)

        # Proposed transition: velocity direction
        proposed = (velocity - 0.5) * 2.0  # de-center

        max_abs_vel = float(np.max(np.abs(velocity - 0.5)))
        ttype = "update" if max_abs_vel > 0.05 else "noop"

        return EvaluatorOutput(
            evaluator_id=EvaluatorID.VELOCITY,
            observation=velocity.copy(),
            confidence=confidence.astype(np.float32),
            explanation=(
                f"Velocity range: [{float(np.min(velocity)):.3f}, {float(np.max(velocity)):.3f}], "
                f"mean confidence: {float(np.mean(confidence)):.3f}"
            ),
            proposed_transition=proposed.astype(np.float32),
            transition_type=ttype,
        )


class DurationEvaluator:
    """
    Specialized evaluator: measures state persistence.

    Scope: narrow — only assesses how long the current regime
    has been stable (above/below threshold with hysteresis).
    """

    __slots__ = ()

    def evaluate(self, cube: CubeCore, perception: PerceptionOutput) -> EvaluatorOutput:
        duration = cube.get_duration_slice()

        # Confidence: higher for longer-duration states (more established)
        confidence = duration.copy()  # already [0,1]

        # Proposed transition: reset duration if saturated
        proposed = np.zeros((N_TIME, N_CAT), dtype=np.float32)

        max_dur = float(np.max(duration))
        if max_dur > 0.95:
            # Saturated — propose reset
            proposed = -duration * 0.1  # small negative push
            ttype = "reset"
        else:
            ttype = "noop"

        return EvaluatorOutput(
            evaluator_id=EvaluatorID.DURATION,
            observation=duration.copy(),
            confidence=confidence.astype(np.float32),
            explanation=(
                f"Duration max: {max_dur:.3f}, "
                f"saturated voxels: {int(np.sum(duration > 0.95))}/{N_TIME * N_CAT}"
            ),
            proposed_transition=proposed,
            transition_type=ttype,
        )


class TurbulenceEvaluator:
    """
    Specialized evaluator: measures local instability.

    Scope: narrow — only assesses how noisy/erratic the signal is.
    High turbulence → low confidence in all other evaluators.
    """

    __slots__ = ()

    def evaluate(self, cube: CubeCore, perception: PerceptionOutput) -> EvaluatorOutput:
        turbulence = cube.get_turbulence_slice()

        # Confidence: inverse of turbulence
        confidence = 1.0 - turbulence.copy()
        confidence = np.clip(confidence, 0.0, 1.0)

        # Proposed transition: dampen when turbulence is extreme
        proposed = np.zeros((N_TIME, N_CAT), dtype=np.float32)
        mask = turbulence > 0.8
        proposed[mask] = -0.05  # slight damping

        max_turb = float(np.max(turbulence))
        ttype = "update" if max_turb > 0.5 else "noop"

        return EvaluatorOutput(
            evaluator_id=EvaluatorID.TURBULENCE,
            observation=turbulence.copy(),
            confidence=confidence.astype(np.float32),
            explanation=(
                f"Turbulence range: [{float(np.min(turbulence)):.3f}, {float(np.max(turbulence)):.3f}], "
                f"high-turb voxels (>0.8): {int(np.sum(turbulence > 0.8))}/{N_TIME * N_CAT}"
            ),
            proposed_transition=proposed,
            transition_type=ttype,
        )


class SequencerEvaluator:
    """
    Specialized evaluator: wraps IndependentSequencer for forensic
    microstructure audit.

    Scope: narrow — only analyses price microstructure via Z-module
    decomposition (mod-100, stride-25 groups, symmetry locks, regime
    transitions, anomaly clusters).

    Maintains its own tamper-evident SHA-256 chain log, completely
    independent of the cube's state.  The pipeline can ONLY read
    features via SequencerFeatureFeed — the sequencer's internal
    state is append-only and cryptographically sealed.
    """

    __slots__ = ("sequencer", "feed", "_symbol", "_log_dir")

    def __init__(
        self,
        symbol: str = "PRIMARY",
        log_dir: str = "./sequencer_logs",
        precision: int = 2,
        stride: int = 25,
        z_boundary: float = 0.24,
    ):
        self._symbol = symbol
        self._log_dir = log_dir
        self.sequencer: IndependentSequencer = IndependentSequencer(
            symbol=symbol,
            log_dir=log_dir,
            precision=precision,
            stride=stride,
            z_boundary=z_boundary,
        )
        self.feed: SequencerFeatureFeed = SequencerFeatureFeed(self.sequencer)

    def ingest_tick(self, price: float, timestamp_ms: int, **metadata) -> Optional[SequencerLogEntry]:
        """Feed a single price tick to the sequencer."""
        return self.sequencer.ingest(
            price=price,
            timestamp_ms=timestamp_ms,
            **metadata,
        )

    def evaluate(self, cube: CubeCore, perception: PerceptionOutput) -> EvaluatorOutput:
        """
        Produce an EvaluatorOutput from current sequencer state.

        Maps forensic features into the 5×5 observation space:
          Row layout (by time horizon, replicated across all 5):
            [0] Z-violation rate (signal stress)
            [1] Regime pressure (NORMAL→CRASH mapped 0→1)
            [2] Anomaly cluster activity (binary)
            [3] Symmetry lock density
            [4] Liquidity stress proxy
        """
        ts_ms = perception.timestamp_ns // 1_000_000
        features = self.feed.get_features(ts_ms)

        # ── Build 5×5 observation from sequencer features ────────
        regime_map = {"NORMAL": 0.1, "STRESS": 0.4, "CRASH": 0.8, "RECOVERY": 0.3, "UNKNOWN": 0.5}
        regime_val = regime_map.get(features.get("SEQ_regime", "UNKNOWN"), 0.5)

        obs_row = np.array([
            float(features.get("SEQ_ZV_rate", 0.0)),
            regime_val,
            0.8 if features.get("SEQ_cluster_active", False) else 0.1,
            min(float(features.get("SEQ_lock_count_5m", 0)) / 50.0, 1.0),
            float(features.get("SEQ_liq_stress", 0.0)),
        ], dtype=np.float32)

        # Replicate across all 5 time horizons
        observation = np.tile(obs_row, (N_TIME, 1))  # (5,5)

        # ── Confidence: inversely related to regime entropy ──────
        entropy = float(features.get("SEQ_regime_entropy", 0.0))
        base_confidence = 1.0 - min(entropy, 1.0)
        confidence = np.full((N_TIME, N_CAT), base_confidence, dtype=np.float32)

        # ── Proposed transition: dampen when stress is high ──────
        z_rate = float(features.get("SEQ_ZV_rate", 0.0))
        proposed = np.zeros((N_TIME, N_CAT), dtype=np.float32)
        if z_rate > 0.1:
            proposed[:, :] = -z_rate * 0.05  # slight damping under stress
            ttype = "update"
        else:
            ttype = "noop"

        # ── Explanation ──────────────────────────────────────────
        seq_stats = self.sequencer.get_stats()
        explanation = (
            f"SEQ: z_rate={z_rate:.3f}, regime={features.get('SEQ_regime','?')}, "
            f"cluster={'Y' if features.get('SEQ_cluster_active') else 'N'}, "
            f"locks_5m={features.get('SEQ_lock_count_5m',0)}, "
            f"entropy={entropy:.3f}, "
            f"seq_ticks={seq_stats.get('ticks_processed',0)}"
        )

        return EvaluatorOutput(
            evaluator_id=EvaluatorID.SEQUENCER,
            observation=observation,
            confidence=confidence,
            explanation=explanation,
            proposed_transition=proposed,
            transition_type=ttype,
        )


class SpecializationLayer:
    """
    Constitutional Computation Framework — Layer 2: Specialization

    Hosts a collection of independently operating evaluators.
    Each evaluator is intentionally narrow in scope and produces
    structured outputs.

    The framework rejects the assumption that any single evaluator
    possesses complete knowledge of system reality.
    """

    __slots__ = ("evaluators", "sequencer")

    def __init__(self, sequencer: Optional[SequencerEvaluator] = None):
        self.sequencer: Optional[SequencerEvaluator] = sequencer
        self.evaluators: Dict[EvaluatorID, object] = {
            EvaluatorID.DELTA: DeltaEvaluator(),
            EvaluatorID.VELOCITY: VelocityEvaluator(),
            EvaluatorID.DURATION: DurationEvaluator(),
            EvaluatorID.TURBULENCE: TurbulenceEvaluator(),
        }
        if sequencer is not None:
            self.evaluators[EvaluatorID.SEQUENCER] = sequencer

    def evaluate_all(
        self, cube: CubeCore, perception: PerceptionOutput
    ) -> List[EvaluatorOutput]:
        """
        Run all evaluators on the current perception state.

        Returns one EvaluatorOutput per evaluator.
        """
        outputs: List[EvaluatorOutput] = []
        for ev_id, ev in self.evaluators.items():
            out = ev.evaluate(cube, perception)  # type: ignore
            outputs.append(out)
        return outputs

    # ── Observability ────────────────────────────────────────────
    @property
    def state(self) -> Dict[str, object]:
        return {
            "layer": "specialization",
            "evaluator_count": len(self.evaluators),
            "evaluator_ids": [e.value for e in self.evaluators],
        }


# ═══════════════════════════════════════════════════════════════════
# L3: CONSENSUS — Epistemological reconciliation
# ═══════════════════════════════════════════════════════════════════

class ConsensusLayer:
    """
    Constitutional Computation Framework — Layer 3: Consensus

    Reconciles competing interpretations from specialised evaluators.

    Unlike ensemble methods that aggregate predictions solely for
    accuracy improvement, consensus here serves an epistemological
    role.  Disagreement becomes a measurable quantity rather than
    a hidden implementation detail.

    The system maintains awareness not only of conclusions but also
    of uncertainty and conflict.
    """

    __slots__ = ()

    def reconcile(
        self, evaluator_outputs: List[EvaluatorOutput]
    ) -> ConsensusOutput:
        """
        Produce a consensus view from all evaluator outputs.

        The reconciled state is a confidence-weighted average of
        what each evaluator observes.

        The proposed_transition is a confidence-weighted average
        of the individual evaluators' proposed_transition deltas.
        This is what gets submitted to governance for authorisation.

        Uncertainty is derived from the entropy of confidence
        distributions.  Conflict is pairwise disagreement between
        evaluator observations.
        """
        n_ev = len(evaluator_outputs)
        if n_ev == 0:
            return ConsensusOutput(
                consensus_id=str(uuid.uuid4()),
                reconciled_state=np.zeros((N_TIME, N_CAT), dtype=np.float32),
                uncertainty=np.ones((N_TIME, N_CAT), dtype=np.float32),
                conflict_matrix=np.zeros((0, 0), dtype=np.float32),
                evaluator_count=0,
                disagreement_detail="No evaluators participated.",
                proposed_transition=np.zeros((N_TIME, N_CAT), dtype=np.float32),
            )

        # ── Confidence-weighted reconciled state (observations) ──
        weighted_sum = np.zeros((N_TIME, N_CAT), dtype=np.float64)
        total_weight = np.zeros((N_TIME, N_CAT), dtype=np.float64)

        # ── Confidence-weighted proposed transition (deltas) ─────
        proposal_sum = np.zeros((N_TIME, N_CAT), dtype=np.float64)
        proposal_weight = np.zeros((N_TIME, N_CAT), dtype=np.float64)

        for out in evaluator_outputs:
            w = out.confidence.astype(np.float64)
            weighted_sum += w * out.observation.astype(np.float64)
            total_weight += w

            # Only include proposals that are actual updates
            if out.transition_type in ("update", "reset"):
                proposal_sum += w * out.proposed_transition.astype(np.float64)
                proposal_weight += w

        # Reconciled state (what evaluators agree the world looks like)
        reconciled = np.divide(
            weighted_sum,
            total_weight,
            out=np.full_like(weighted_sum, 0.5),
            where=total_weight > 0,
        )
        reconciled = np.clip(reconciled, 0.0, 1.0).astype(np.float32)

        # Proposed transition (what evaluators want to do)
        proposed = np.divide(
            proposal_sum,
            proposal_weight,
            out=np.zeros_like(proposal_sum),
            where=proposal_weight > 0,
        )
        proposed = proposed.astype(np.float32)

        # ── Uncertainty (entropy of confidence distributions) ────
        conf_stacked = np.stack(
            [out.confidence for out in evaluator_outputs], axis=-1
        )  # (N_TIME, N_CAT, n_ev)

        conf_norm = conf_stacked / (np.sum(conf_stacked, axis=-1, keepdims=True) + 1e-12)
        entropy = -np.sum(
            conf_norm * np.log(conf_norm + 1e-12), axis=-1
        ) / math.log(max(n_ev, 2))
        uncertainty = np.clip(entropy.astype(np.float32), 0.0, 1.0)

        # ── Conflict matrix (pairwise observation disagreement) ──
        conflict = np.zeros((n_ev, n_ev), dtype=np.float32)
        for i in range(n_ev):
            for j in range(i + 1, n_ev):
                diff = np.mean(
                    np.abs(
                        evaluator_outputs[i].observation
                        - evaluator_outputs[j].observation
                    )
                )
                conflict[i, j] = diff
                conflict[j, i] = diff

        # ── Disagreement summary ─────────────────────────────────
        mean_uncertainty = float(np.mean(uncertainty))
        max_conflict = float(np.max(conflict)) if n_ev > 1 else 0.0
        detail = (
            f"Mean uncertainty: {mean_uncertainty:.3f}, "
            f"Max pairwise conflict: {max_conflict:.3f}"
        )

        return ConsensusOutput(
            consensus_id=str(uuid.uuid4()),
            reconciled_state=reconciled,
            uncertainty=uncertainty,
            conflict_matrix=conflict,
            evaluator_count=n_ev,
            disagreement_detail=detail,
            proposed_transition=proposed,
        )

    # ── Observability ────────────────────────────────────────────
    @property
    def state(self) -> Dict[str, object]:
        return {
            "layer": "consensus",
            "method": "confidence-weighted + entropy uncertainty + pairwise conflict",
        }


# ═══════════════════════════════════════════════════════════════════
# L4: GOVERNANCE — Constitutional constraint checking
# ═══════════════════════════════════════════════════════════════════

class ConstitutionalConstraints:
    """
    Invariant system constraints that define admissible transitions.

    These constraints exist independently of the computational
    entities producing recommendations.  They represent:
      • Safety boundaries
      • Resource limitations
      • Operational policies
      • Domain-specific guarantees

    A proposed state transition does not imply authorisation.
    Every proposed transition must pass this constitutional layer.
    """

    __slots__ = (
        "max_voxel_value", "min_voxel_value",
        "max_delta_per_tick", "max_turbulence",
        "min_observations_before_transition",
        "max_saturated_duration_voxels",
    )

    def __init__(
        self,
        max_voxel_value: float = 1.0,
        min_voxel_value: float = 0.0,
        max_delta_per_tick: float = 0.5,
        max_turbulence: float = 0.95,
        min_observations_before_transition: int = 1,
        max_saturated_duration_voxels: int = 20,
    ):
        self.max_voxel_value = max_voxel_value
        self.min_voxel_value = min_voxel_value
        self.max_delta_per_tick = max_delta_per_tick
        self.max_turbulence = max_turbulence
        self.min_observations_before_transition = min_observations_before_transition
        self.max_saturated_duration_voxels = max_saturated_duration_voxels

    def check(
        self,
        current_state: np.ndarray,
        proposed_transition: np.ndarray,
        evaluator_outputs: List[EvaluatorOutput],
        consensus: ConsensusOutput,
        tick_count: int,
    ) -> GovernanceDecision:
        """
        Evaluate whether a proposed state transition is admissible.

        The proposed_transition is a delta (what evaluators want to
        change).  Governance checks whether applying this delta
        to the current state would violate any invariant constraint.

        Per the CCF: "A proposed state transition does not imply
        authorisation."  This layer enforces that separation.

        Returns a GovernanceDecision with authorisation status,
        reasons, and which constraints were checked.
        """
        checked: List[str] = []
        failures: List[str] = []

        result_state = current_state.astype(np.float64) + proposed_transition.astype(np.float64)

        # ── Constraint 1: Value bounds (on resulting state) ──────
        checked.append("value_bounds")
        if np.any(result_state < self.min_voxel_value):
            failures.append(
                f"Result below min ({self.min_voxel_value})"
            )
        if np.any(result_state > self.max_voxel_value):
            failures.append(
                f"Result above max ({self.max_voxel_value})"
            )

        # ── Constraint 2: No NaN / Inf (on proposed transition) ──
        checked.append("finite")
        if not np.all(np.isfinite(proposed_transition)):
            failures.append("Non-finite values in proposed transition (NaN or Inf)")

        # ── Constraint 3: Transition magnitude bound ─────────────
        checked.append("transition_magnitude")
        max_mag = float(np.max(np.abs(proposed_transition)))
        if max_mag > self.max_delta_per_tick:
            failures.append(
                f"Max transition magnitude {max_mag:.4f} exceeds bound {self.max_delta_per_tick}"
            )

        # ── Constraint 4: Turbulence cap ─────────────────────────
        checked.append("turbulence_cap")
        for out in evaluator_outputs:
            if out.evaluator_id == EvaluatorID.TURBULENCE:
                max_turb = float(np.max(out.observation))
                if max_turb > self.max_turbulence:
                    failures.append(
                        f"Turbulence {max_turb:.3f} exceeds cap {self.max_turbulence}"
                    )

        # ── Constraint 5: Minimum observations ───────────────────
        checked.append("min_observations")
        if tick_count < self.min_observations_before_transition:
            failures.append(
                f"Tick count {tick_count} < minimum {self.min_observations_before_transition}"
            )

        # ── Constraint 6: Duration saturation limit ──────────────
        checked.append("duration_saturation")
        for out in evaluator_outputs:
            if out.evaluator_id == EvaluatorID.DURATION:
                saturated = int(np.sum(out.observation > 0.95))
                if saturated > self.max_saturated_duration_voxels:
                    failures.append(
                        f"Duration saturation {saturated} > limit {self.max_saturated_duration_voxels}"
                    )

        authorized = len(failures) == 0
        reason = "All constraints passed." if authorized else "; ".join(failures)

        return GovernanceDecision(
            governance_id=str(uuid.uuid4()),
            authorized=authorized,
            reason=reason,
            constraints_checked=checked,
            proposed_state=result_state.astype(np.float32),
        )


class GovernanceLayer:
    """
    Constitutional Computation Framework — Layer 4: Governance

    The central contribution of the framework.

    Separates recommendation (from Specialization) from permission.
    Decision-producing entities generate proposals; constitutional
    mechanisms determine admissibility.

    Governance becomes a first-class computational construct rather
    than an application-specific afterthought.
    """

    __slots__ = ("constitution",)

    def __init__(self, constitution: Optional[ConstitutionalConstraints] = None):
        self.constitution: ConstitutionalConstraints = (
            constitution or ConstitutionalConstraints()
        )

    def authorize(
        self,
        current_state: np.ndarray,
        proposed_transition: np.ndarray,
        evaluator_outputs: List[EvaluatorOutput],
        consensus: ConsensusOutput,
        tick_count: int,
    ) -> GovernanceDecision:
        """Submit a proposed transition for constitutional review."""
        return self.constitution.check(
            current_state, proposed_transition,
            evaluator_outputs, consensus, tick_count,
        )

    # ── Observability ────────────────────────────────────────────
    @property
    def state(self) -> Dict[str, object]:
        return {
            "layer": "governance",
            "constraints": {
                "max_voxel_value": self.constitution.max_voxel_value,
                "min_voxel_value": self.constitution.min_voxel_value,
                "max_delta_per_tick": self.constitution.max_delta_per_tick,
                "max_turbulence": self.constitution.max_turbulence,
                "min_observations": self.constitution.min_observations_before_transition,
                "max_saturated_duration": self.constitution.max_saturated_duration_voxels,
            },
        }


# ═══════════════════════════════════════════════════════════════════
# L5: EXECUTION — Authorised state transitions
# ═══════════════════════════════════════════════════════════════════

class ExecutionLayer:
    """
    Constitutional Computation Framework — Layer 5: Execution

    Enacts state transitions only after constitutional validation.

    Distinguishes between hypothetical state trajectories and
    realized state trajectories.  Only realized transitions possess
    external consequences.

    Execution serves as the unique boundary between internal
    computational models and the external environment.
    """

    __slots__ = (
        "hypothetical_trail",    # proposed but not enacted
        "realized_trail",        # enacted with governance approval
        "max_trail_length",
    )

    def __init__(self, max_trail_length: int = 1000):
        self.hypothetical_trail: List[ExecutionRecord] = []
        self.realized_trail: List[ExecutionRecord] = []
        self.max_trail_length: int = max_trail_length

    def enact(
        self,
        previous_state: np.ndarray,
        proposed_state: np.ndarray,
        governance: GovernanceDecision,
        timestamp_ns: int,
    ) -> ExecutionRecord:
        """
        Attempt to enact a state transition.

        If governance authorised the transition, it becomes a
        realized trajectory.  Otherwise it is recorded as
        hypothetical.
        """
        transition_id = str(uuid.uuid4())
        new_state = proposed_state.copy() if governance.authorized else previous_state.copy()

        record = ExecutionRecord(
            execution_id=str(uuid.uuid4()),
            transition_id=transition_id,
            previous_state=previous_state.copy(),
            new_state=new_state,
            authorized=governance.authorized,
            timestamp_ns=timestamp_ns,
            governance_id=governance.governance_id,
        )

        if governance.authorized:
            self.realized_trail.append(record)
            if len(self.realized_trail) > self.max_trail_length:
                self.realized_trail.pop(0)
        else:
            self.hypothetical_trail.append(record)
            if len(self.hypothetical_trail) > self.max_trail_length:
                self.hypothetical_trail.pop(0)

        return record

    # ── Observability ────────────────────────────────────────────
    @property
    def state(self) -> Dict[str, object]:
        return {
            "layer": "execution",
            "realized_count": len(self.realized_trail),
            "hypothetical_count": len(self.hypothetical_trail),
            "last_realized": (
                self.realized_trail[-1].transition_id
                if self.realized_trail else None
            ),
            "last_hypothetical": (
                self.hypothetical_trail[-1].transition_id
                if self.hypothetical_trail else None
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# L6: PERSISTENCE — Causal provenance ledger
# ═══════════════════════════════════════════════════════════════════

class PersistenceLayer:
    """
    Constitutional Computation Framework — Layer 6: Persistence

    Establishes a permanent causal record.  Every state transition
    retains links to its originating observations, participating
    evaluators, consensus outcomes, governance decisions, and
    execution results.

    Enables computational provenance: the ability to reconstruct
    not merely what occurred but why it occurred.

    Every realized state can be traced backward through a complete
    chain of computational reasoning.
    """

    __slots__ = ("causal_ledger", "max_ledger_size", "db_path", "_conn")

    def __init__(self, db_path: Optional[str] = None, max_ledger_size: int = 10000):
        self.causal_ledger: List[CausalRecord] = []
        self.max_ledger_size: int = max_ledger_size
        self.db_path: Optional[str] = db_path
        self._conn: Optional[sqlite3.Connection] = None

        if db_path is not None:
            self._init_db()

    def _init_db(self) -> None:
        """Initialise the SQLite causal ledger database."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS causal_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE,
                transition_id TEXT,
                perception_id TEXT,
                evaluator_ids TEXT,
                consensus_id TEXT,
                governance_id TEXT,
                execution_id TEXT,
                timestamp_ns INTEGER,
                authorized INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT UNIQUE,
                transition_id TEXT,
                authorized INTEGER,
                governance_id TEXT,
                timestamp_ns INTEGER,
                previous_state_blob BLOB,
                new_state_blob BLOB
            )
        """)
        conn.commit()
        self._conn = conn

    def commit(
        self,
        perception: PerceptionOutput,
        evaluator_outputs: List[EvaluatorOutput],
        consensus: ConsensusOutput,
        governance: GovernanceDecision,
        execution: ExecutionRecord,
    ) -> CausalRecord:
        """
        Commit a full causal record linking all layers.

        This creates the provenance chain:
          observation → evaluators → consensus → governance → execution
        """
        record = CausalRecord(
            record_id=str(uuid.uuid4()),
            transition_id=execution.transition_id,
            perception_id=perception.perception_id,
            evaluator_ids=[out.evaluator_id.value for out in evaluator_outputs],
            consensus_id=consensus.consensus_id,
            governance_id=governance.governance_id,
            execution_id=execution.execution_id,
            timestamp_ns=perception.timestamp_ns,
        )

        self.causal_ledger.append(record)
        if len(self.causal_ledger) > self.max_ledger_size:
            self.causal_ledger.pop(0)

        # ── Write to SQLite if database is configured ────────────
        if self._conn is not None:
            try:
                self._conn.execute(
                    """INSERT OR IGNORE INTO causal_ledger
                    (record_id, transition_id, perception_id, evaluator_ids,
                     consensus_id, governance_id, execution_id, timestamp_ns, authorized)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.record_id,
                        record.transition_id,
                        record.perception_id,
                        ",".join(record.evaluator_ids),
                        record.consensus_id,
                        record.governance_id,
                        record.execution_id,
                        record.timestamp_ns,
                        int(execution.authorized),
                    ),
                )
                self._conn.execute(
                    """INSERT OR IGNORE INTO execution_trail
                    (execution_id, transition_id, authorized, governance_id,
                     timestamp_ns, previous_state_blob, new_state_blob)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        execution.execution_id,
                        execution.transition_id,
                        int(execution.authorized),
                        execution.governance_id,
                        execution.timestamp_ns,
                        execution.previous_state.astype(np.float32).tobytes(),
                        execution.new_state.astype(np.float32).tobytes(),
                    ),
                )
                self._conn.commit()
            except sqlite3.Error as e:
                # Persistence failure does not crash the engine
                print(f"[PERSISTENCE] Write error: {e}", file=_sys.stderr)

        return record

    def trace(self, transition_id: str) -> List[CausalRecord]:
        """Return the causal chain for a given transition ID."""
        return [r for r in self.causal_ledger if r.transition_id == transition_id]

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ── Observability ────────────────────────────────────────────
    @property
    def state(self) -> Dict[str, object]:
        return {
            "layer": "persistence",
            "ledger_size": len(self.causal_ledger),
            "max_ledger_size": self.max_ledger_size,
            "db_connected": self._conn is not None,
            "last_record": (
                self.causal_ledger[-1].record_id if self.causal_ledger else None
            ),
        }


# ═══════════════════════════════════════════════════════════════════
# CCF ENGINE — Full orchestrator
# ═══════════════════════════════════════════════════════════════════

class CCFEngine:
    """
    Orchestrator for the Constitutional Computation Framework.

    Stitches all 6 layers into a single pipeline:
      Perception → Specialization → Consensus → Governance → Execution → Persistence

    Plus structural observability at every layer.
    """

    __slots__ = (
        "cube", "perception", "specialization", "consensus_layer",
        "governance", "execution", "persistence",
        "sequencer_evaluator",
        "tick_count", "heartbeat_count",
        "_layer_states",
    )

    def __init__(
        self,
        constitution: Optional[ConstitutionalConstraints] = None,
        db_path: Optional[str] = None,
        sequencer_config: Optional[Dict[str, object]] = None,
    ):
        self.cube: CubeCore = CubeCore()
        self.perception: PerceptionLayer = PerceptionLayer(self.cube)

        # ── Sequencer (5th evaluator, independent forensic audit) ─
        self.sequencer_evaluator: Optional[SequencerEvaluator] = None
        if sequencer_config is not None:
            self.sequencer_evaluator = SequencerEvaluator(
                symbol=str(sequencer_config.get("symbol", "PRIMARY")),
                log_dir=str(sequencer_config.get("log_dir", "./sequencer_logs")),
                precision=int(sequencer_config.get("precision", 2)),
                stride=int(sequencer_config.get("stride", 25)),
                z_boundary=float(sequencer_config.get("z_boundary", 0.24)),
            )

        self.specialization: SpecializationLayer = SpecializationLayer(
            sequencer=self.sequencer_evaluator,
        )
        self.consensus_layer: ConsensusLayer = ConsensusLayer()
        self.governance: GovernanceLayer = GovernanceLayer(constitution)
        self.execution: ExecutionLayer = ExecutionLayer()
        self.persistence: PersistenceLayer = PersistenceLayer(db_path=db_path)

        self.tick_count: int = 0
        self.heartbeat_count: int = 0

        # Snapshot of all layer states for observability
        self._layer_states: Dict[str, Dict[str, object]] = {}

    # ── Tick ingestion (perception only) ─────────────────────────

    def ingest(self, inp: SensorInput) -> PerceptionOutput:
        """
        Ingest a sensor reading.

        Updates the Perception layer (Raw values + Delta) AND feeds
        the primary signal channel to the Sequencer evaluator for
        independent forensic audit.

        The full CCF pipeline runs on each heartbeat.
        """
        self.tick_count += 1
        perception = self.perception.observe(inp)

        # Feed primary signal to sequencer (audit trail)
        if self.sequencer_evaluator is not None:
            ts_ms = inp.timestamp_ns // 1_000_000
            self.sequencer_evaluator.ingest_tick(
                price=float(inp.values[0]),
                timestamp_ms=ts_ms,
                volume=float(inp.values[1]) if len(inp.values) > 1 else 0.0,
            )

        self._update_observability()
        return perception

    def ingest_batch(self, inputs: List[SensorInput]) -> PerceptionOutput:
        """
        Ingest a burst of sensor readings.

        All readings go through perception before the heartbeat
        triggers the full pipeline.
        """
        self.tick_count += len(inputs)
        perception = self.perception.observe_batch(inputs)
        self._update_observability()
        return perception

    # ── Heartbeat (full CCF pipeline) ────────────────────────────

    def heartbeat(self) -> Dict[str, object]:
        """
        Execute one full CCF pipeline cycle.

        Returns a report containing the outputs of all 6 layers
        for this heartbeat, enabling full observability.

        Pipeline:
          1. Heartbeat updates cube (Velocity, Duration, Turbulence)
          2. Specialization (4 evaluators)
          3. Consensus (reconciliation)
          4. Governance (constitutional check)
          5. Execution (authorized vs hypothetical)
          6. Persistence (causal record)
        """
        self.heartbeat_count += 1

        # ── Step 0: Cube heartbeat ───────────────────────────────
        cube_latency = self.cube.heartbeat()

        # ── Step 1: Perception (canonical observation) ───────────
        # After heartbeat, the Raw slice is the canonical observation
        perception = PerceptionOutput(
            perception_id=str(uuid.uuid4()),
            raw_cube_slice=self.cube.get_raw_slice(),
            timestamp_ns=self.cube.last_timestamp_ns,
            sequence_id=self.cube.last_sequence_id,
        )

        # ── Step 2: Specialization ───────────────────────────────
        evaluator_outputs = self.specialization.evaluate_all(self.cube, perception)

        # Sequencer audit: verify cryptographic chain integrity every 10 heartbeats
        if self.sequencer_evaluator is not None and self.heartbeat_count % 10 == 0:
            chain_valid, broken_at = self.sequencer_evaluator.sequencer.verify_chain()
            if not chain_valid:
                print(f"[CCF ENGINE] ⚠ SEQUENCER CHAIN INTEGRITY FAILURE at seq {broken_at}",
                      file=_sys.stderr)

        # ── Step 3: Consensus ────────────────────────────────────
        consensus = self.consensus_layer.reconcile(evaluator_outputs)

        # ── Step 4: Governance ───────────────────────────────────
        current_state = self.cube.get_raw_slice()  # state before transition
        proposed_transition = consensus.proposed_transition  # what evaluators recommend
        governance = self.governance.authorize(
            current_state, proposed_transition,
            evaluator_outputs, consensus, self.tick_count,
        )

        # ── Step 5: Execution ────────────────────────────────────
        # Apply the proposed transition to current state to get new state
        if governance.authorized:
            new_state = np.clip(
                current_state.astype(np.float64) + proposed_transition.astype(np.float64),
                0.0, 1.0,
            ).astype(np.float32)
        else:
            new_state = current_state.copy()

        execution = self.execution.enact(
            current_state, new_state,
            governance, self.cube.last_timestamp_ns,
        )

        # ── Step 6: Persistence ──────────────────────────────────
        causal = self.persistence.commit(
            perception, evaluator_outputs,
            consensus, governance, execution,
        )

        # ── Build observability report ───────────────────────────
        report = self._build_heartbeat_report(
            perception, evaluator_outputs, consensus,
            governance, execution, causal, cube_latency,
        )

        self._update_observability()
        return report

    # ── Observability ────────────────────────────────────────────

    def _update_observability(self) -> None:
        """Snap all layer states for structural observability."""
        self._layer_states = {
            "cube": {
                "valid": self.cube.valid,
                "tick_count": self.cube.tick_count,
                "heartbeat_count": self.cube.heartbeat_count,
                "voxel_min": float(np.min(self.cube.cube)),
                "voxel_max": float(np.max(self.cube.cube)),
                "voxel_mean": float(np.mean(self.cube.cube)),
            },
            "perception": self.perception.state,
            "specialization": self.specialization.state,
            "consensus": self.consensus_layer.state,
            "governance": self.governance.state,
            "execution": self.execution.state,
            "persistence": self.persistence.state,
        }

    def _build_heartbeat_report(
        self,
        perception: PerceptionOutput,
        evaluator_outputs: List[EvaluatorOutput],
        consensus: ConsensusOutput,
        governance: GovernanceDecision,
        execution: ExecutionRecord,
        causal: CausalRecord,
        cube_latency: float,
    ) -> Dict[str, object]:
        """Assemble a structured heartbeat report with all layer outputs."""
        return {
            "heartbeat": self.heartbeat_count,
            "tick": self.tick_count,
            "cube_latency_ms": cube_latency,
            "perception_id": perception.perception_id,
            "evaluators": {
                out.evaluator_id.value: {
                    "observation_range": (
                        float(np.min(out.observation)),
                        float(np.max(out.observation)),
                    ),
                    "mean_confidence": float(np.mean(out.confidence)),
                    "transition_type": out.transition_type,
                    "explanation": out.explanation,
                }
                for out in evaluator_outputs
            },
            "consensus": {
                "id": consensus.consensus_id,
                "mean_uncertainty": float(np.mean(consensus.uncertainty)),
                "max_conflict": float(np.max(consensus.conflict_matrix)),
                "detail": consensus.disagreement_detail,
            },
            "governance": {
                "authorized": governance.authorized,
                "reason": governance.reason,
                "constraints_checked": governance.constraints_checked,
            },
            "execution": {
                "authorized": execution.authorized,
                "transition_id": execution.transition_id,
            },
            "causal": {
                "record_id": causal.record_id,
            },
            "layer_states": self._layer_states,
        }

    @property
    def observability(self) -> Dict[str, object]:
        """Structural observability: every layer exposed."""
        return dict(self._layer_states)

    def close(self) -> None:
        """Clean shutdown."""
        self.persistence.close()


# ═══════════════════════════════════════════════════════════════════
# DEMO — Synthetic data validation
# ═══════════════════════════════════════════════════════════════════

def _demo() -> None:
    """
    Run a demonstration of the CCF Cube v1.0.

    Generates synthetic sensor data, runs 100 ticks with heartbeats,
    and prints a structured report showing all 6 layers operating.
    """
    import sys

    print("=" * 72)
    print("CCF CUBE v1.0 — CONSTITUTIONAL COMPUTATION FRAMEWORK")
    print("=" * 72)
    print(f"  Voxels: {N_VOXELS}  ({N_TIME}×{N_CAT}×{N_TRANS})")
    print(f"  Axes:")
    print(f"    X (time):     {TIME_HORIZONS}")
    print(f"    Y (category): {CATEGORIES}")
    print(f"    Z (trans):    {TRANSFORMATIONS}")
    print(f"  Layers:")
    print(f"    L1: Perception      — canonical raw observations")
    print(f"    L2: Specialization  — 4 independent evaluators")
    print(f"    L3: Consensus       — reconciliation + disagreement")
    print(f"    L4: Governance      — constitutional constraints")
    print(f"    L5: Execution       — authorized transitions")
    print(f"    L6: Persistence     — causal provenance ledger")
    print(f"    Obs: Observability  — structural at every layer")
    print("=" * 72)

    # ── Initialise engine with sequencer ─────────────────────────
    engine = CCFEngine(
        db_path="ccf_cube_demo.db",
        sequencer_config={
            "symbol": "CH0",
            "log_dir": "./sequencer_logs",
            "precision": 2,
            "stride": 25,
            "z_boundary": 0.24,
        },
    )

    # ── Generate synthetic data ──────────────────────────────────
    # Simulate 5 channels with different characteristics:
    #   ch0: slow sine wave (regime A)
    #   ch1: fast oscillation (regime B)
    #   ch2: random walk (regime C)
    #   ch3: step function (regime D)
    #   ch4: white noise (regime E)
    rng = np.random.RandomState(42)
    n_ticks = 200
    n_heartbeats = 20  # every 10 ticks

    t = np.linspace(0, 4 * np.pi, n_ticks)
    ch0 = np.sin(t) * 50 + 100           # slow sine:  50-150
    ch1 = np.sin(t * 5) * 10 + 50        # fast osc:   40-60
    ch2 = np.cumsum(rng.randn(n_ticks)) * 0.5 + 30  # random walk
    ch3 = (np.sin(t * 0.5) > 0).astype(float) * 40 + 20  # step: 20 or 60
    ch4 = rng.randn(n_ticks) * 5 + 10    # white noise: ~10±5

    signals = np.column_stack([ch0, ch1, ch2, ch3, ch4])  # (n_ticks, 5)

    print(f"  Sequencer:    enabled=True, evaluators=5 (delta, velocity, duration, turbulence, sequencer)")
    print(f"  Sequencer DB: ./sequencer_logs/sequencer_CH0.db")
    print("=" * 72)

    # ── Run simulation ──────────────────────────────────────────
    tick_count = 0
    hb_count = 0

    for i in range(n_ticks):
        inp = SensorInput(
            values=signals[i].astype(np.float64),
            timestamp_ns=i * 10_000_000,  # 10ms per tick
            sequence_id=i,
        )
        engine.ingest(inp)
        tick_count += 1

        # Heartbeat every 10 ticks (simulating 100ms)
        if i > 0 and i % 10 == 0:
            report = engine.heartbeat()
            hb_count += 1

            # Print periodic summary
            if hb_count % 5 == 0 or hb_count == 1:
                ls = report["layer_states"]
                gov = report["governance"]
                con = report["consensus"]
                ev = report["evaluators"]
                print()
                print(f"── Heartbeat #{hb_count} (tick {tick_count}) ──────────────")
                print(f"  Cube:  valid={ls['cube']['valid']}, "
                      f"voxels [{ls['cube']['voxel_min']:.3f}, {ls['cube']['voxel_max']:.3f}]")
                print(f"  L1:    perception_id={report['perception_id'][:8]}…")
                print(f"  L2:    evaluators={list(ev.keys())}")
                for ev_id, ev_data in ev.items():
                    print(f"         {ev_id}: confidence={ev_data['mean_confidence']:.3f}, "
                          f"type={ev_data['transition_type']}")
                # Show sequencer explanation specifically
                if "sequencer" in ev:
                    print(f"         sequencer.explanation: {ev['sequencer']['explanation']}")
                print(f"  L3:    uncertainty={con['mean_uncertainty']:.3f}, "
                      f"conflict={con['max_conflict']:.4f}")
                print(f"  L4:    authorized={gov['authorized']}, "
                      f"reason=\"{gov['reason']}\"")
                print(f"  L5:    trail: realized={ls['execution']['realized_count']}, "
                      f"hypothetical={ls['execution']['hypothetical_count']}")
                print(f"  L6:    ledger_size={ls['persistence']['ledger_size']}")

    # ── Final validation ────────────────────────────────────────
    print()
    print("=" * 72)
    print("FINAL VALIDATION")
    print("=" * 72)

    # Validate all 125 voxels
    cube_valid = engine.cube.valid
    cube_min = float(np.min(engine.cube.cube))
    cube_max = float(np.max(engine.cube.cube))
    cube_mean = float(np.mean(engine.cube.cube))
    has_nan = bool(np.any(np.isnan(engine.cube.cube)))

    print(f"  125 voxels in [0,1]:     {'✓' if cube_valid else '✗'}")
    print(f"  Min voxel value:         {cube_min:.6f}")
    print(f"  Max voxel value:         {cube_max:.6f}")
    print(f"  Mean voxel value:        {cube_mean:.6f}")
    print(f"  NaN values:             {'✗ NAN DETECTED' if has_nan else '✓ none'}")
    print(f"  Ticks processed:         {tick_count}")
    print(f"  Heartbeats:              {hb_count}")
    print(f"  Realized transitions:    {engine.execution.state['realized_count']}")
    print(f"  Hypothetical transitions:{engine.execution.state['hypothetical_count']}")
    print(f"  Causal ledger records:   {engine.persistence.state['ledger_size']}")

    # Demonstrate causal provenance
    if engine.execution.realized_trail:
        last_realized = engine.execution.realized_trail[-1]
        traces = engine.persistence.trace(last_realized.transition_id)
        print()
        print("  ── Provenance example (last realized transition) ──")
        print(f"     Transition ID: {last_realized.transition_id[:16]}…")
        if traces:
            t = traces[0]
            print(f"     Perception:   {t.perception_id[:16]}…")
            print(f"     Evaluators:   {', '.join(t.evaluator_ids)}")
            print(f"     Consensus:    {t.consensus_id[:16]}…")
            print(f"     Governance:   {t.governance_id[:16]}…")
            print(f"     Execution:    {t.execution_id[:16]}…")

    # All layer states for observability
    print()
    print("  ── Observability (all layer states) ──")
    obs = engine.observability
    for layer_name, layer_state in obs.items():
        items = ", ".join(f"{k}={v}" for k, v in layer_state.items())
        print(f"     {layer_name}: {items}")

    engine.close()
    print()
    print("CCF Cube v1.0 demonstration complete.")


if __name__ == "__main__":
    import sys as _sys
    try:
        _demo()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        _sys.exit(0)
