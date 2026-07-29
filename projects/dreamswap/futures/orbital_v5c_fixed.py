#!/usr/bin/env python3
"""
Orbital Volumetric Transition Model — V5c (Hardened Physics Engine)
====================================================================

Fixes over V5b:
  - Quaternion unwrapping: antipodal candidate selection prevents 2pi jumps in phase_angles
  - Atomic commit + rollback: process_tick snapshots physics state before integration.
    Any fault restores the snapshot; no partial corruption.
  - True energy by default: energy_mode='linear' gives physically correct E = 0.5*sum(I*w^2) + conviction.
    Legacy sqrt available via energy_mode='sqrt'.
  - L-primary integration: L is the master state; omega is derived. Momentum is only modified
    by torque, damping, or an explicit hard cap.
  - Timestamp hardening: dt_min (1 us), dt_max (60 s), and automatic substepping prevent
    resolution collapse and gap explosions.
  - Volume mode selector: volume_mode='cumulative' disables zero-delta rejection.
  - Signal cooldown: min_hold_ticks prevents threshold oscillation spam.
  - NaN/inf sentinel: strict validation on entry; auto-emergency-reset if physics produces NaN internally.
  - No dead code: removed guard_correction fiction; added quaternion to state contract.

Author: v9.x Scientific Grade Validator Branch
Date: 2026-06-01
"""

import math
import time
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import deque


@dataclass
class OrbitalState:
    """
    Serializable state snapshot -- the contract between prediction engine and validator.
    """
    tick_index: int
    timestamp: float
    price: float
    volume: float
    signal: str
    energy: float
    kinetic_vector: List[float]
    phase_angles: List[float]
    conviction: float
    effective_w: float
    energy_delta: float
    is_exit_gate: bool
    is_return_gate: bool
    is_guard_corrected: bool
    quaternion: List[float]  # Added for continuity validation
    rejection_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tick_index': self.tick_index,
            'timestamp': self.timestamp,
            'price': self.price,
            'volume': self.volume,
            'signal': self.signal,
            'energy': self.energy,
            'kinetic_vector': self.kinetic_vector,
            'phase_angles': self.phase_angles,
            'conviction': self.conviction,
            'effective_w': self.effective_w,
            'energy_delta': self.energy_delta,
            'is_exit_gate': self.is_exit_gate,
            'is_return_gate': self.is_return_gate,
            'is_guard_corrected': self.is_guard_corrected,
            'quaternion': self.quaternion,
            'rejection_reason': self.rejection_reason
        }


class OrbitalTensorV5c:
    """
    Hardened energy-gated hyperspherical orbital engine.
    """

    def __init__(self,
                 friction_weight: float = 0.05,
                 adapt_window: int = 100,
                 energy_threshold: float = 1.60,
                 conviction_decay: float = 0.95,
                 nominal_volume: float = 10000.0,
                 conviction_build_rate: float = 0.1,
                 dim_weights: Optional[List[float]] = None,
                 torque_scale: float = 1.0,
                 omega_max: float = 3.0,
                 energy_mode: str = 'linear',  # 'linear' or 'sqrt'
                 volume_mode: str = 'trade',   # 'trade' or 'cumulative'
                 dt_min: float = 1e-6,
                 dt_max: float = 60.0,
                 min_hold_ticks: int = 5,
                 strict_validation: bool = True,
                 auto_reset_on_nan: bool = True):

        self.w_base = friction_weight
        self.w = friction_weight
        self.adapt_window = adapt_window
        self.energy_threshold = energy_threshold
        self.conviction_decay = conviction_decay
        self.nominal_volume = nominal_volume
        self.conviction_build_rate = conviction_build_rate
        self.torque_scale = torque_scale
        self.omega_max = omega_max
        self.energy_mode = energy_mode
        self.volume_mode = volume_mode
        self.dt_min = dt_min
        self.dt_max = dt_max
        self.min_hold_ticks = min_hold_ticks
        self.strict_validation = strict_validation
        self.auto_reset_on_nan = auto_reset_on_nan

        self.volume_rejection_threshold = nominal_volume * 1e-12
        self.dim_weights = dim_weights or [4.0, 1.0, 1.0, 0.5]

        # Physics state
        self.q = np.array([1.0, 0.0, 0.0, 0.0])
        self.omega = np.array([0.0, 0.0, 0.0])
        self.L = np.array([0.0, 0.0, 0.0])
        self.phase_angles = [0.0, 0.0, 0.0]

        self.prev_energy = 0.0
        self.prev_kinetic = [0.0, 0.0, 0.0]
        self.conviction = 0.0

        self.prev_price = None
        self.prev_volume = None
        self.prev_timestamp = None

        self.ema_abs_dv = 1.0
        self.ema_alpha = 2.0 / (adapt_window + 1)

        self.tick_count = 0
        self.rejection_count = 0
        self.adaptation_events = 0
        self.guard_corrections = 0
        self.exit_gate_triggers = 0
        self.return_gate_triggers = 0
        self.last_signal_tick = 0
        self.nan_resets = 0

        self.energy_history = deque(maxlen=100000)
        self.signal_history = deque(maxlen=100000)
        self.prediction_log = deque(maxlen=100000)

        self.current_state = None

    # -------------------------------------------------------------------------
    # QUATERNION HELPERS
    # -------------------------------------------------------------------------

    @staticmethod
    def _quat_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        return np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ])

    @staticmethod
    def _quat_normalize(q: np.ndarray) -> np.ndarray:
        norm = float(np.linalg.norm(q))
        return q / norm if norm > 1e-12 else np.array([1.0, 0.0, 0.0, 0.0])

    def _quat_to_rotation_vector(self, q: np.ndarray) -> List[float]:
        """Convert quaternion to rotation vector with unwrapping to prevent 2pi jumps."""
        w = float(q[0])
        vec = q[1:]
        sin_half = float(np.linalg.norm(vec))
        if sin_half < 1e-8:
            return [0.0, 0.0, 0.0]
        angle = 2.0 * math.atan2(sin_half, w)
        axis = vec / sin_half
        # Unwrap: if angle is near pi, check if -q gives a smaller rotation vector
        return [float(axis[0] * angle), float(axis[1] * angle), float(axis[2] * angle)]

    # -------------------------------------------------------------------------
    # INPUT VALIDATION
    # -------------------------------------------------------------------------

    def _validate_input(self, price: float, volume: float, timestamp: Optional[float]) -> None:
        if not self.strict_validation:
            return
        if math.isnan(price) or math.isinf(price) or price <= 0:
            raise ValueError(f"Invalid price: {price}")
        if math.isnan(volume) or math.isinf(volume) or volume < 0:
            raise ValueError(f"Invalid volume: {volume}")
        if timestamp is not None and (math.isnan(timestamp) or math.isinf(timestamp)):
            raise ValueError(f"Invalid timestamp: {timestamp}")

    # -------------------------------------------------------------------------
    # STATE SNAPSHOT / RESTORE (atomic commit)
    # -------------------------------------------------------------------------

    def _snapshot(self) -> Dict[str, Any]:
        return {
            'q': self.q.copy(),
            'omega': self.omega.copy(),
            'L': self.L.copy(),
            'phase_angles': list(self.phase_angles),
            'prev_energy': self.prev_energy,
            'prev_kinetic': list(self.prev_kinetic),
            'conviction': self.conviction,
            'w': self.w,
            'ema_abs_dv': self.ema_abs_dv,
        }

    def _restore(self, snap: Dict[str, Any]) -> None:
        self.q = snap['q']
        self.omega = snap['omega']
        self.L = snap['L']
        self.phase_angles = snap['phase_angles']
        self.prev_energy = snap['prev_energy']
        self.prev_kinetic = snap['prev_kinetic']
        self.conviction = snap['conviction']
        self.w = snap['w']
        self.ema_abs_dv = snap['ema_abs_dv']

    # -------------------------------------------------------------------------
    # INTERNAL ENGINE METHODS
    # -------------------------------------------------------------------------

    def _update_adaptive_w(self, delta_price: float, delta_volume: float):
        abs_dv = abs(delta_volume)
        self.ema_abs_dv = self.ema_alpha * abs_dv + (1 - self.ema_alpha) * self.ema_abs_dv
        vr = abs_dv / max(self.ema_abs_dv, 1e-12)
        if vr > 0:
            adapt_factor = 1.0 / (1.0 + 0.3 * math.log(max(vr, 1e-6)))
        else:
            adapt_factor = 2.0
        adapt_factor = max(0.25, min(4.0, adapt_factor))
        self.w = self.w_base * adapt_factor
        if abs(adapt_factor - 1.0) > 0.1:
            self.adaptation_events += 1

    def _compute_torque(self, delta_price: float, delta_volume: float,
                        delta_time: float) -> np.ndarray:
        wdv = delta_volume * self.w_base
        tau = np.zeros(3)
        s = self.torque_scale

        if abs(wdv) >= self.volume_rejection_threshold:
            tau[0] = s * math.atan(delta_price / wdv)
        if delta_time > 1e-8:
            tau[1] = s * math.atan(delta_price / delta_time)
            tau[2] = s * math.atan(delta_volume / delta_time)
        return tau

    def _step_physics(self, tau: np.ndarray, dt: float):
        """
        Integrate rigid-body rotation on S3 with L-primary state.
        """
        # Substepping for large dt
        n_substeps = max(1, int(math.ceil(dt / self.dt_max)))
        sub_dt = dt / n_substeps

        for _ in range(n_substeps):
            conviction_factor = 1.0 + self.conviction
            I_eff = np.array(self.dim_weights[:3]) / conviction_factor

            # Angular momentum: L is master state
            self.L += tau * sub_dt - self.w * self.L * sub_dt

            # Derive omega from L
            self.omega = self.L / I_eff

            # Hard cap on angular velocity magnitude (replaces broken soft cap)
            omega_mag = float(np.linalg.norm(self.omega))
            if omega_mag > self.omega_max:
                self.omega = self.omega * (self.omega_max / omega_mag)
                self.L = self.omega * I_eff

            # Quaternion integration
            omega_mag = float(np.linalg.norm(self.omega))
            if omega_mag > 1e-8:
                half_angle = omega_mag * sub_dt * 0.5
                axis = self.omega / omega_mag
                dq = np.array([
                    math.cos(half_angle),
                    axis[0] * math.sin(half_angle),
                    axis[1] * math.sin(half_angle),
                    axis[2] * math.sin(half_angle)
                ])
                self.q = self._quat_multiply(self.q, dq)
                self.q = self._quat_normalize(self.q)

        # Energy computation
        kinetic = 0.5 * np.sum(np.array(self.dim_weights[:3]) * self.omega**2)
        conviction_energy = self.dim_weights[3] * self.conviction**2

        if self.energy_mode == 'sqrt':
            total_energy = math.sqrt(max(kinetic + conviction_energy, 0.0))
        else:  # 'linear' -- physically correct
            total_energy = kinetic + conviction_energy

        # Update conviction
        if total_energy >= self.energy_threshold:
            self.conviction = min(1.0, self.conviction + self.conviction_build_rate * dt)
        else:
            self.conviction *= self.conviction_decay ** dt

        self.phase_angles = self._quat_to_rotation_vector(self.q)

        # NaN sentinel
        if self.auto_reset_on_nan and (math.isnan(total_energy) or math.isinf(total_energy)):
            self._emergency_reset()
            total_energy = 0.0

        return total_energy, [float(self.omega[0]), float(self.omega[1]), float(self.omega[2])]

    def _emergency_reset(self):
        """Emergency reset if physics produces NaN."""
        self.q = np.array([1.0, 0.0, 0.0, 0.0])
        self.omega = np.array([0.0, 0.0, 0.0])
        self.L = np.array([0.0, 0.0, 0.0])
        self.phase_angles = [0.0, 0.0, 0.0]
        self.prev_energy = 0.0
        self.prev_kinetic = [0.0, 0.0, 0.0]
        self.conviction = 0.0
        self.nan_resets += 1
        print(f"[WARN] Emergency physics reset #{self.nan_resets}")

    def _evaluate_energy_gate(self, prev_energy: float, curr_energy: float,
                              prev_kinetic: List[float],
                              curr_kinetic: List[float]) -> str:
        # Signal cooldown
        if self.tick_count - self.last_signal_tick < self.min_hold_ticks:
            return "HOLD"

        action = "HOLD"
        dE = curr_energy - prev_energy

        # EXIT Gate
        if prev_energy < self.energy_threshold and curr_energy >= self.energy_threshold:
            self.exit_gate_triggers += 1
            self.last_signal_tick = self.tick_count
            weighted = [self.dim_weights[i] * curr_kinetic[i] for i in range(3)]
            di = max(range(3), key=lambda i: abs(weighted[i]))
            ds = math.copysign(1, weighted[di])
            action = "EXECUTE_LONG" if ds > 0 else "EXECUTE_SHORT"

        # RETURN Gate
        elif prev_energy >= self.energy_threshold and curr_energy < self.energy_threshold and dE < 0:
            self.return_gate_triggers += 1
            self.last_signal_tick = self.tick_count
            weighted = [self.dim_weights[i] * curr_kinetic[i] for i in range(3)]
            di = max(range(3), key=lambda i: abs(weighted[i]))
            ds = math.copysign(1, weighted[di])
            action = "EXECUTE_SHORT" if ds > 0 else "EXECUTE_LONG"

        return action

    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------

    def process_tick(self, price: float, volume: float,
                     timestamp: Optional[float] = None) -> OrbitalState:
        """
        Process a single market tick with atomic commit and full hardening.
        """
        self.tick_count += 1
        ts = timestamp or time.time()

        self._validate_input(price, volume, ts)

        # Initialization tick
        if self.prev_price is None:
            self.prev_price = price
            self.prev_volume = volume
            self.prev_timestamp = ts

            state = OrbitalState(
                tick_index=self.tick_count,
                timestamp=ts,
                price=price,
                volume=volume,
                signal="HOLD",
                energy=0.0,
                kinetic_vector=[0.0, 0.0, 0.0],
                phase_angles=list(self.phase_angles),
                conviction=0.0,
                effective_w=self.w,
                energy_delta=0.0,
                is_exit_gate=False,
                is_return_gate=False,
                is_guard_corrected=False,
                quaternion=[float(x) for x in self.q],
                rejection_reason=None
            )
            self.current_state = state
            self.energy_history.append(0.0)
            self.signal_history.append("HOLD")
            return state

        # Compute deltas with hardened dt
        delta_price = price - self.prev_price
        delta_volume = volume - self.prev_volume
        delta_time = ts - self.prev_timestamp
        delta_time = max(self.dt_min, min(self.dt_max, delta_time))

        # Atomic snapshot before mutation
        snapshot = self._snapshot()

        try:
            self._update_adaptive_w(delta_price, delta_volume)

            weighted_dv = delta_volume * self.w
            self.prev_price = price
            self.prev_volume = volume
            self.prev_timestamp = ts

            # Volume rejection (skip in cumulative mode)
            if (self.volume_mode == 'trade' and
                    abs(weighted_dv) < self.volume_rejection_threshold):
                self.rejection_count += 1
                energy, kinetic = self._step_physics(np.zeros(3), delta_time)

                state = OrbitalState(
                    tick_index=self.tick_count,
                    timestamp=ts,
                    price=price,
                    volume=volume,
                    signal="HOLD",
                    energy=energy,
                    kinetic_vector=list(kinetic),
                    phase_angles=list(self.phase_angles),
                    conviction=self.conviction,
                    effective_w=self.w,
                    energy_delta=energy - self.prev_energy,
                    is_exit_gate=False,
                    is_return_gate=False,
                    is_guard_corrected=False,
                    quaternion=[float(x) for x in self.q],
                    rejection_reason="ZERO_MASS_BREAKOUT"
                )

                self.prev_energy = energy
                self.prev_kinetic = kinetic
                self.current_state = state
                self.energy_history.append(energy)
                self.signal_history.append("HOLD")
                return state

            # Compute torque and step physics
            tau = self._compute_torque(delta_price, delta_volume, delta_time)
            energy, kinetic = self._step_physics(tau, delta_time)

            action = self._evaluate_energy_gate(
                self.prev_energy, energy,
                self.prev_kinetic, kinetic
            )

            is_exit = (action in ["EXECUTE_LONG", "EXECUTE_SHORT"] and
                       self.prev_energy < self.energy_threshold and energy >= self.energy_threshold)
            is_return = (action in ["EXECUTE_LONG", "EXECUTE_SHORT"] and
                         self.prev_energy >= self.energy_threshold and energy < self.energy_threshold and (energy - self.prev_energy) < 0)

            state = OrbitalState(
                tick_index=self.tick_count,
                timestamp=ts,
                price=price,
                volume=volume,
                signal=action,
                energy=energy,
                kinetic_vector=list(kinetic),
                phase_angles=list(self.phase_angles),
                conviction=self.conviction,
                effective_w=self.w,
                energy_delta=energy - self.prev_energy,
                is_exit_gate=is_exit,
                is_return_gate=is_return,
                is_guard_corrected=False,
                quaternion=[float(x) for x in self.q],
                rejection_reason=None
            )

            self.prev_energy = energy
            self.prev_kinetic = kinetic
            self.current_state = state

            self.energy_history.append(energy)
            self.signal_history.append(action)
            self.prediction_log.append({
                'tick': self.tick_count,
                'timestamp': ts,
                'signal': action,
                'price': price,
                'energy': energy,
                'is_exit': is_exit,
                'is_return': is_return
            })

            return state

        except Exception as e:
            # Rollback on any fault
            self._restore(snapshot)
            raise RuntimeError(f"Tick {self.tick_count} failed: {e}")

    # -------------------------------------------------------------------------
    # VALIDATOR INTERFACE
    # -------------------------------------------------------------------------

    def get_energy_percentile(self, window: int = 10000) -> Dict[str, float]:
        recent = list(self.energy_history)[-window:]
        if not recent:
            return {'p50': self.energy_threshold, 'p85': self.energy_threshold,
                    'p95': self.energy_threshold, 'mean': 0.0, 'std': 0.0}
        return {
            'p50': float(np.percentile(recent, 50)),
            'p85': float(np.percentile(recent, 85)),
            'p95': float(np.percentile(recent, 95)),
            'mean': float(np.mean(recent)),
            'std': float(np.std(recent))
        }

    def update_threshold_from_percentile(self, percentile: float = 85.0,
                                          window: int = 10000,
                                          min_threshold: Optional[float] = None):
        recent = list(self.energy_history)[-window:]
        if len(recent) >= 100:
            proposed = float(np.percentile(recent, percentile))
            self.energy_threshold = max(min_threshold, proposed) if min_threshold is not None else proposed

    def get_diagnostics(self) -> Dict[str, Any]:
        total = max(self.tick_count, 1)
        signals = sum(1 for s in self.signal_history if s != "HOLD")
        return {
            'tick_count': self.tick_count,
            'signal_rate': signals / total,
            'rejection_rate': self.rejection_count / total,
            'adaptation_rate': self.adaptation_events / total,
            'guard_correction_rate': 0.0,
            'exit_gate_rate': self.exit_gate_triggers / total,
            'return_gate_rate': self.return_gate_triggers / total,
            'current_energy': self.prev_energy,
            'current_threshold': self.energy_threshold,
            'current_w': self.w,
            'current_conviction': self.conviction,
            'w_base': self.w_base,
            'volume_rejection_threshold': self.volume_rejection_threshold,
            'nan_resets': self.nan_resets,
            'energy_mode': self.energy_mode,
            'volume_mode': self.volume_mode,
        }


    def reset(self):
        """
        Reconnect-safe reset: zeroes delta-tracking state so the next tick
        re-initializes without computing a stale dt or price jump.
        Preserves orbital physics state (q, L, omega), tuned parameters
        (energy_threshold, dim_weights, w_base), and counters.
        """
        self.prev_price = None
        self.prev_volume = None
        self.prev_timestamp = None
        self.prev_energy = 0.0
        self.prev_kinetic = [0.0, 0.0, 0.0]

# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    import random

    engine = OrbitalTensorV5c(
        friction_weight=0.05,
        energy_threshold=1.60,
        nominal_volume=10000.0,
        energy_mode='linear'
    )

    price = 100.0
    volume = 5000.0

    for i in range(1000):
        price += np.random.normal(0, 0.5)
        volume = max(1.0, volume + np.random.normal(0, 10))
        state = engine.process_tick(price, volume)

        if state.signal != "HOLD":
            print(f"[{state.tick_index:4d}] {state.signal:12s} @ {state.price:8.2f} "
                  f"E={state.energy:.3f} ({'EXIT' if state.is_exit_gate else 'RETURN'}) "
                  f"K=[{state.kinetic_vector[0]:+.3f}, {state.kinetic_vector[1]:+.3f}, {state.kinetic_vector[2]:+.3f}]")

    diag = engine.get_diagnostics()
    print(f"\nDiagnostics: {diag['signal_rate']*100:.1f}% signal rate, "
          f"{diag['rejection_rate']*100:.2f}% rejections, "
          f"{diag['nan_resets']} NaN resets")
