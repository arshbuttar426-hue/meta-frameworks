# =============================================================================
# MULTI-ASSET FLEET ROUTER — FUSION EDITION v4.1  (BTCUSDT WEBSOCKET ONLY)
# Python 3.14 Compatible | Time-Bucketed Delta1 Integration
# 
# Integrated: River Doctrine v4.0 time-bucketed feed + per-asset fusion
# =============================================================================

import asyncio
import sqlite3
import threading
import time
import json
import math
import random
import os
import sys
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Tuple
from enum import Enum
from collections import deque

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPE_DB_PATH = os.environ.get("TRADING_PIPE_DB_PATH") or os.path.join(_SCRIPT_DIR, "pipeline_macro.db")
MARKET_TICKS_TABLE = "market_ticks"
SQLITE_TIMEOUT_SEC = 30.0
SQLITE_BUSY_TIMEOUT_MS = 5000

FUSION_WINDOW = 64
FUSION_LOG_INTERVAL_MS = 5000
ROUTE_MIN_INTERVAL_MS = 500
ROUTE_DELTA_THRESHOLD = 0.05
RECENT_EMERGENCY_LOCK_MS = 8000
RECOVERY_WINDOW_MS = 30000
BASE_CONFIDENCE_THRESHOLD = 0.32
BASE_ENTROPY_THRESHOLD = 0.74


def _open_sqlite(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(
        db_path,
        check_same_thread=False,
        timeout=SQLITE_TIMEOUT_SEC,
    )
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=" + str(SQLITE_BUSY_TIMEOUT_MS))
    return conn


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# =============================================================================
# FLEET MANAGER DATA STRUCTURES
# =============================================================================

@dataclass(frozen=True)
class Tick:
    timestamp_ms: int
    price: float
    volume: float
    top_bid_qty: float
    top_ask_qty: float
    l2_bids: Optional[List[Any]] = None
    l2_asks: Optional[List[Any]] = None


class EngineState(Enum):
    NEUTRAL = 0
    LONG = 1
    SHORT = -1
    EMERGENCY = 99
    RECOVERY = 88


# =============================================================================
# FUSION ENGINE INTERNAL STRUCTURES
# =============================================================================

class State(Enum):
    VOID = "VOID"
    EMERGENCY = "EMERGENCY"
    CAUTIOUS = "CAUTIOUS"
    ACTIVE = "ACTIVE"


@dataclass
class InternalTick:
    price: float
    volume: float
    bid: float
    ask: float
    timestamp: float
    best_bid_qty: float = 0.0
    best_ask_qty: float = 0.0


@dataclass
class QuadrantSnapshot:
    q1: float
    q2: float
    q3: float
    q4: float


@dataclass
class CalibratedParams:
    slab_width_pct: float
    coherence_threshold: float
    emotion_threshold: float
    void_threshold: float
    mass_emergency_multiplier: float
    median_mass: float
    q2_floor: float
    geometric_mass_floor: float
    warmup_count: int
    mass_emergency_abs: float = field(init=False)

    def __post_init__(self):
        self.mass_emergency_abs = self.median_mass * self.mass_emergency_multiplier


# =============================================================================
# AUTO-CALIBRATOR (v2.5.2 verbatim)
# =============================================================================

class AutoCalibrator:
    def __init__(self, warmup_ticks: int = 50):
        if warmup_ticks < 20:
            raise ValueError("warmup_ticks must be >= 20")
        self.warmup_ticks = warmup_ticks
        self.ticks: List[InternalTick] = []
        self.is_ready = False
        self._cached_params: Optional[CalibratedParams] = None

    def ingest(self, tick: InternalTick) -> bool:
        self.ticks.append(tick)
        if len(self.ticks) >= self.warmup_ticks and not self.is_ready:
            self._cached_params = self._calibrate()
            self.is_ready = True
            return True
        return False

    def get_params(self) -> CalibratedParams:
        if not self.is_ready or self._cached_params is None:
            raise RuntimeError("Calibrator not ready")
        return self._cached_params

    def _calibrate(self) -> CalibratedParams:
        prices = np.array([t.price for t in self.ticks], dtype=np.float64)
        volumes = np.array([t.volume for t in self.ticks], dtype=np.float64)

        atr = self._compute_atr(prices, period=min(14, len(prices) - 1))
        mean_price = float(np.mean(prices))
        slab_width_pct = (atr / mean_price) * 2.5
        slab_width_pct = max(slab_width_pct, 0.0005)

        coherences: List[float] = []
        emotions: List[float] = []
        void_volumes: List[float] = []
        masses: List[float] = []

        for tick in self.ticks:
            spread = tick.ask - tick.bid
            mid = (tick.ask + tick.bid) / 2.0
            slab_width = mid * slab_width_pct
            q = self._synthetic_quadrants_from_tick(tick, mid, spread, slab_width)
            mass = self._compute_geometric_mass_raw(q)
            masses.append(mass)

            total = q.q1 + q.q2 + q.q3 + q.q4 + 1e-12
            near_mid = (q.q1 + q.q3) / total
            coherences.append(float(near_mid))

            bid_sum = q.q1 + q.q2
            ask_sum = q.q3 + q.q4
            imbalance = abs(bid_sum - ask_sum) / (bid_sum + ask_sum + 1e-12)
            emotions.append(float(imbalance))

            void_vol = (q.q2 + q.q4) / total
            void_volumes.append(float(void_vol))

        coherence_threshold = float(np.percentile(coherences, 95))
        emotion_threshold = float(np.percentile(emotions, 95))
        void_threshold = float(np.percentile(void_volumes, 95))
        median_mass = float(np.median(masses))

        coherence_threshold = max(coherence_threshold, 0.55)
        emotion_threshold = max(emotion_threshold, 0.30)
        void_threshold = max(void_threshold, 0.20)

        return CalibratedParams(
            slab_width_pct=slab_width_pct,
            coherence_threshold=coherence_threshold,
            emotion_threshold=emotion_threshold,
            void_threshold=void_threshold,
            mass_emergency_multiplier=10.0,
            median_mass=median_mass,
            q2_floor=0.01,
            geometric_mass_floor=0.01,
            warmup_count=self.warmup_ticks,
        )

    @staticmethod
    def _compute_atr(prices: np.ndarray, period: int) -> float:
        if len(prices) < 2:
            return 0.0
        if len(prices) < period + 1:
            period = len(prices) - 1
        tr_list = np.abs(prices[1:] - prices[:-1])
        return float(np.mean(tr_list[-period:]))

    @staticmethod
    def _synthetic_quadrants_from_tick(tick, mid, spread, slab_width):
        q1 = tick.best_bid_qty if tick.best_bid_qty > 0 else tick.volume * 0.25
        q3 = tick.best_ask_qty if tick.best_ask_qty > 0 else tick.volume * 0.25
        far_decay = math.exp(-spread / max(slab_width, 1e-9))
        q2 = q1 * far_decay * 0.5
        q4 = q3 * far_decay * 0.5
        noise = tick.volume * 0.05
        return QuadrantSnapshot(
            q1=q1 + noise * random.random(),
            q2=q2 + noise * random.random(),
            q3=q3 + noise * random.random(),
            q4=q4 + noise * random.random(),
        )

    @staticmethod
    def _compute_geometric_mass_raw(q):
        masses = [max(q.q1, 0.01), max(q.q2, 0.01), max(q.q3, 0.01), max(q.q4, 0.01)]
        return float(np.exp(np.mean(np.log(masses))))


# =============================================================================
# RIVER DOCTRINE FUSION ENGINE v4.0
# =============================================================================

class RiverDoctrineFusionEngine:
    """
    v4.0 Fusion: Per-asset calibrated engine with time-bucketed inputs.
    Accepts Fleet Manager Tick. Returns Fleet Manager EngineState.
    """

    def __init__(self, asset: str, warmup_ticks: int = 50, max_leverage: float = 1.0):
        self.asset = asset
        self.max_leverage = max_leverage
        self.tick_count = 0
        self.last_diagnostic: Optional[Dict[str, Any]] = None

        self.calibrator = AutoCalibrator(warmup_ticks=warmup_ticks)
        self.params: Optional[CalibratedParams] = None
        self.state = State.VOID
        self.void_entry_time: Optional[float] = None
        self._emergency_entry_tick: Optional[int] = None
        self._min_emergency_ticks = 5
        self._recovery_lock_ticks = 3
        self._recovery_lock_end: Optional[int] = None
        self._prev_price: Optional[float] = None
        self._velocity_window = deque(maxlen=5)

        self.position = 0.0
        self.entry_price = 0.0
        self.entry_target = 0.0
        self.entry_stop = 0.0
        self.active_target = 0.0
        self.active_stop = 0.0
        self.entry_regime = None
        self.last_entry_time = 0
        self.entry_cooldown_ms = 5000
        self.position_gate = True

        self.price_history: List[float] = []
        self.max_history = 100

    def ingest(self, tick: Tick) -> EngineState:
        self.tick_count += 1

        self.price_history.append(tick.price)
        if len(self.price_history) > self.max_history:
            self.price_history.pop(0)

        internal_tick = self._convert_tick(tick)

        if not self.calibrator.is_ready:
            ready = self.calibrator.ingest(internal_tick)
            if ready:
                self.params = self.calibrator.get_params()
                print("[CALIBRATION COMPLETE] " + self.asset
                      + " armed after " + str(self.params.warmup_count) + " ticks")
            self.last_diagnostic = {
                "asset": self.asset,
                "tick_count": self.tick_count,
                "price": tick.price,
                "state": "WARMUP",
                "engine_state": "NEUTRAL",
                "position": 0.0,
                "action": "CALIBRATING",
            }
            return EngineState.NEUTRAL

        mid = (internal_tick.ask + internal_tick.bid) / 2.0
        slab_width = mid * self.params.slab_width_pct
        q = self._build_quadrants(internal_tick, mid, slab_width)
        mass = self._compute_geometric_mass(q)
        mass_ratio = mass / max(self.params.median_mass, 1e-12)
        coherence = self._compute_coherence(q)
        emotion = self._compute_emotion(q)
        void_volume = self._compute_void_volume(q)
        velocity = self._compute_velocity(internal_tick.price)

        self._update_threat_state(mass_ratio, coherence, emotion, void_volume,
                                   velocity, internal_tick.timestamp)

        if self.state == State.EMERGENCY:
            had_position = self.position != 0.0
            self._reset_position()
            self.last_diagnostic = {
                "asset": self.asset,
                "tick_count": self.tick_count,
                "price": tick.price,
                "state": State.EMERGENCY.name,
                "engine_state": "EMERGENCY",
                "position": 0.0,
                "mass_ratio": mass_ratio,
                "action": "CLOSE_ALL" if had_position else "HOLD",
                "reason": "EMERGENCY: Mass divergence or void+emotion spike",
            }
            return EngineState.EMERGENCY

        exit_state = self._check_exit(tick.price)
        if exit_state is not None:
            self.last_diagnostic = {
                "asset": self.asset,
                "tick_count": self.tick_count,
                "price": tick.price,
                "state": self.state.name,
                "engine_state": exit_state.name,
                "position": self.position,
                "action": "EXIT",
                "reason": "Target or stop hit",
            }
            return exit_state

        if self.state == State.ACTIVE and self.position == 0.0:
            entry_state = self._check_entry(tick.price, q, coherence, emotion,
                                            void_volume, tick.timestamp_ms)
            if entry_state is not None:
                self.last_diagnostic = {
                    "asset": self.asset,
                    "tick_count": self.tick_count,
                    "price": tick.price,
                    "state": self.state.name,
                    "engine_state": entry_state.name,
                    "position": self.position,
                    "action": "ENTRY",
                    "reason": "Snapback entry triggered",
                }
                return entry_state

        result = EngineState.NEUTRAL
        if self.position > 0.0:
            result = EngineState.LONG
        elif self.position < 0.0:
            result = EngineState.SHORT

        self.last_diagnostic = {
            "asset": self.asset,
            "tick_count": self.tick_count,
            "price": tick.price,
            "state": self.state.name,
            "engine_state": result.name,
            "position": self.position,
            "mass_ratio": mass_ratio,
            "coherence": coherence,
            "emotion": emotion,
            "void_volume": void_volume,
            "velocity": velocity,
            "action": "HOLD",
        }
        return result

    def _convert_tick(self, tick: Tick) -> InternalTick:
        if self.params is not None:
            spread = tick.price * self.params.slab_width_pct
        else:
            spread = tick.price * 0.0005
        bid = tick.price - spread / 2.0
        ask = tick.price + spread / 2.0
        return InternalTick(
            price=tick.price,
            volume=tick.volume,
            bid=bid,
            ask=ask,
            timestamp=tick.timestamp_ms / 1000.0,
            best_bid_qty=tick.top_bid_qty,
            best_ask_qty=tick.top_ask_qty,
        )

    def _update_threat_state(self, mass_ratio: float, coherence: float,
                              emotion: float, void_volume: float,
                              velocity: float, timestamp: float) -> None:
        assert self.params is not None
        prev_state = self.state
        mult = self.params.mass_emergency_multiplier

        in_recovery_lock = (
            self._recovery_lock_end is not None
            and self.tick_count <= self._recovery_lock_end
        )

        if self.state == State.VOID:
            if mass_ratio > mult:
                self.state = State.EMERGENCY
                self._emergency_entry_tick = self.tick_count
            elif (coherence > self.params.coherence_threshold
                  and emotion > self.params.emotion_threshold):
                self.state = State.ACTIVE
            else:
                if self.void_entry_time is None:
                    self.void_entry_time = timestamp

        elif self.state == State.EMERGENCY:
            time_in_emergency = self.tick_count - (
                self._emergency_entry_tick or self.tick_count
            )
            can_exit = (
                time_in_emergency >= self._min_emergency_ticks
                and mass_ratio < mult * 0.3
            )
            if can_exit:
                self.state = State.CAUTIOUS
                self._emergency_entry_tick = None
                self._recovery_lock_end = self.tick_count + self._recovery_lock_ticks

        elif self.state == State.CAUTIOUS:
            if not in_recovery_lock and mass_ratio > mult:
                self.state = State.EMERGENCY
                self._emergency_entry_tick = self.tick_count
            elif (coherence < self.params.coherence_threshold * 0.8
                  and emotion < self.params.emotion_threshold * 0.5):
                self.state = State.VOID
                self.void_entry_time = timestamp

        elif self.state == State.ACTIVE:
            if (void_volume > self.params.void_threshold
                and emotion > self.params.emotion_threshold):
                self.state = State.EMERGENCY
                self._emergency_entry_tick = self.tick_count
            elif coherence < self.params.coherence_threshold * 0.7:
                self.state = State.VOID
                self.void_entry_time = timestamp

        if self.state == State.VOID and self.void_entry_time is not None:
            time_in_void = timestamp - self.void_entry_time
            if time_in_void > 300.0:
                self.void_entry_time = timestamp

        if prev_state != self.state:
            price_str = ""
            if self.price_history:
                price_str = format(self.price_history[-1], ".2f")
            print("[TRANSITION] " + self.asset + " | " + prev_state.name + "->"
                  + self.state.name + " at tick " + str(self.tick_count)
                  + " | price=" + price_str)

    def _check_exit(self, price: float) -> Optional[EngineState]:
        if self.position == 0.0:
            return None

        if self.position > 0.0:
            if price >= self.active_target:
                self._reset_position()
                return EngineState.NEUTRAL
            if price <= self.active_stop:
                self._reset_position()
                return EngineState.NEUTRAL

        if self.position < 0.0:
            if price <= self.active_target:
                self._reset_position()
                return EngineState.NEUTRAL
            if price >= self.active_stop:
                self._reset_position()
                return EngineState.NEUTRAL

        return None

    def _check_entry(self, price: float, q: QuadrantSnapshot, coherence: float,
                      emotion: float, void_volume: float,
                      timestamp_ms: int) -> Optional[EngineState]:
        if self.position != 0.0:
            return None
        if timestamp_ms - self.last_entry_time < self.entry_cooldown_ms:
            return None

        tick_velocity = 0.0
        if len(self.price_history) >= 2:
            tick_velocity = abs(self.price_history[-1] - self.price_history[-2])
        compression_ratio = 1.0 / (tick_velocity + 1e-10)
        is_exhausted = (compression_ratio > 2.0) or (void_volume > 0.3)

        if not is_exhausted:
            return None

        if len(self.price_history) < 10:
            return None
        reference = float(np.mean(self.price_history[-20:]))
        band = reference * self.params.slab_width_pct * 1.0
        lower_band = reference - band
        upper_band = reference + band

        if price < lower_band and q.q1 > q.q2 * 1.2:
            drop_depth = lower_band - price
            self.active_target = reference + drop_depth
            self.active_stop = price - drop_depth
            self.position = 1.0
            self.entry_price = price
            self.entry_target = self.active_target
            self.entry_stop = self.active_stop
            self.last_entry_time = timestamp_ms
            print("[ENTRY LONG] " + self.asset + " at " + format(price, ".2f")
                  + " | target=" + format(self.active_target, ".2f")
                  + " | stop=" + format(self.active_stop, ".2f"))
            return EngineState.LONG

        if price > upper_band and q.q3 > q.q4 * 1.2:
            pump_height = price - upper_band
            self.active_target = reference - pump_height
            self.active_stop = price + pump_height
            self.position = -1.0
            self.entry_price = price
            self.entry_target = self.active_target
            self.entry_stop = self.active_stop
            self.last_entry_time = timestamp_ms
            print("[ENTRY SHORT] " + self.asset + " at " + format(price, ".2f")
                  + " | target=" + format(self.active_target, ".2f")
                  + " | stop=" + format(self.active_stop, ".2f"))
            return EngineState.SHORT

        return None

    def _reset_position(self) -> None:
        if self.position != 0.0:
            pnl = 0.0
            if self.price_history:
                pnl = self.price_history[-1] - self.entry_price
                if self.position < 0.0:
                    pnl = -pnl
            print("[EXIT] " + self.asset + " at " + format(self.price_history[-1], ".2f")
                  + " | PnL=" + format(pnl, ".2f"))
        self.position = 0.0
        self.entry_price = 0.0
        self.entry_target = 0.0
        self.entry_stop = 0.0
        self.active_target = 0.0
        self.active_stop = 0.0
        self.entry_regime = None

    def _compute_geometric_mass(self, q: QuadrantSnapshot) -> float:
        floor = self.params.geometric_mass_floor if self.params else 0.01
        q2_floor = self.params.q2_floor if self.params else 0.01
        masses = [
            max(q.q1, floor),
            max(q.q2, q2_floor),
            max(q.q3, floor),
            max(q.q4, floor),
        ]
        log_masses = np.log(masses)
        return float(np.exp(np.mean(log_masses)))

    @staticmethod
    def _compute_coherence(q: QuadrantSnapshot) -> float:
        total = q.q1 + q.q2 + q.q3 + q.q4 + 1e-12
        near_mid = (q.q1 + q.q3) / total
        return float(near_mid)

    @staticmethod
    def _compute_emotion(q: QuadrantSnapshot) -> float:
        bid_sum = q.q1 + q.q2
        ask_sum = q.q3 + q.q4
        imbalance = abs(bid_sum - ask_sum) / (bid_sum + ask_sum + 1e-12)
        return float(imbalance)

    @staticmethod
    def _compute_void_volume(q: QuadrantSnapshot) -> float:
        total = q.q1 + q.q2 + q.q3 + q.q4 + 1e-12
        far = (q.q2 + q.q4) / total
        return float(far)

    def _compute_velocity(self, price: float) -> float:
        if self._prev_price is None:
            self._prev_price = price
            return 0.0
        vel = (price - self._prev_price) / max(self._prev_price, 1e-9)
        self._velocity_window.append(vel)
        self._prev_price = price
        return float(np.mean(self._velocity_window)) if self._velocity_window else 0.0

    def _build_quadrants(self, tick: InternalTick, mid: float,
                          slab_width: float) -> QuadrantSnapshot:
        spread = tick.ask - tick.bid
        return AutoCalibrator._synthetic_quadrants_from_tick(tick, mid, spread, slab_width)


# =============================================================================
# FLEET MANAGER INFRASTRUCTURE
# =============================================================================

class Calibrator:
    def __init__(self, min_ticks: int = 50):
        self.min_ticks = min_ticks
        self.tick_count = 0

    def ingest(self, tick: Tick) -> None:
        self.tick_count += 1

    @property
    def is_ready(self) -> bool:
        return self.tick_count >= self.min_ticks


class PositionRouter:
    def __init__(self, max_leverage: float = 1.0):
        self.max_leverage = max_leverage
        self.state_direction = {
            "NEUTRAL": 0.0,
            "LONG": 1.0,
            "SHORT": -1.0,
            "EMERGENCY": 0.0,
            "RECOVERY": 0.0,
        }

    def directional_signal_from_state(self, state_name: str) -> float:
        return self.state_direction.get(state_name, 0.0)

    def weighted_target_exposure(
        self,
        directional_signal: float,
        confidence_score: float,
        regime_multiplier: float,
        emergency_suppression: float,
    ) -> float:
        weighted = (
            directional_signal
            * confidence_score
            * regime_multiplier
            * emergency_suppression
            * self.max_leverage
        )
        return _clamp(weighted, -1.0, 1.0)

    def get_exposure_command(
        self,
        asset: str,
        state_name: str,
        target_exposure: float,
    ) -> Dict[str, Any]:
        return {
            "asset": asset,
            "state": state_name,
            "target_exposure": _clamp(float(target_exposure), -1.0, 1.0),
            "timestamp_ms": int(time.time() * 1000),
        }


class PipelineLogger:
    def __init__(self, db_path: str = PIPE_DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _conn(self):
        if not hasattr(self._local, "conn"):
            self._local.conn = _open_sqlite(self.db_path)
        return self._local.conn

    def _init_db(self):
        c = self._conn().cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS exposure_commands ("
            + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            + "asset TEXT NOT NULL, "
            + "state TEXT NOT NULL, "
            + "target_exposure REAL NOT NULL, "
            + "timestamp_ms INTEGER NOT NULL, "
            + "UNIQUE(asset, timestamp_ms)"
            + ")"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS diagnostics ("
            + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            + "asset TEXT NOT NULL, "
            + "diagnostic_json TEXT NOT NULL, "
            + "latency_ms REAL, "
            + "timestamp_ms INTEGER NOT NULL"
            + ")"
        )
        self._conn().commit()

    def get_latest_exposure(self, asset: str) -> Optional[Dict[str, Any]]:
        c = self._conn().cursor()
        c.execute(
            "SELECT state, target_exposure FROM exposure_commands "
            + "WHERE asset = ? ORDER BY timestamp_ms DESC LIMIT 1",
            (asset,),
        )
        row = c.fetchone()
        if row:
            return {"state": row[0], "target_exposure": row[1]}
        return None

    def log_exposure_command(self, command: Dict[str, Any]) -> None:
        c = self._conn().cursor()
        ts = int(command["timestamp_ms"])
        inserted = False
        for _ in range(5):
            try:
                c.execute(
                    "INSERT INTO exposure_commands (asset, state, target_exposure, timestamp_ms) "
                    + "VALUES (?, ?, ?, ?)",
                    (
                        command["asset"],
                        command["state"],
                        command["target_exposure"],
                        ts,
                    ),
                )
                inserted = True
                command["timestamp_ms"] = ts
                break
            except sqlite3.IntegrityError:
                ts += 1
        if not inserted:
            c.execute(
                "INSERT OR REPLACE INTO exposure_commands (asset, state, target_exposure, timestamp_ms) "
                + "VALUES (?, ?, ?, ?)",
                (
                    command["asset"],
                    command["state"],
                    command["target_exposure"],
                    ts,
                ),
            )
            command["timestamp_ms"] = ts
        self._conn().commit()

    def log_diagnostic(self, asset: str, diagnostic: Dict[str, Any], latency_ms: float) -> None:
        c = self._conn().cursor()
        c.execute(
            "INSERT INTO diagnostics (asset, diagnostic_json, latency_ms, timestamp_ms) "
            + "VALUES (?, ?, ?, ?)",
            (
                asset,
                json.dumps(diagnostic),
                latency_ms,
                int(time.time() * 1000),
            ),
        )
        self._conn().commit()


class FleetManager:
    def __init__(self, assets: List[str], warmup_ticks: int = 50, max_leverage: float = 1.0):
        self.assets = assets
        self.warmup_ticks = warmup_ticks
        self.max_leverage = max_leverage

        self.engines: Dict[str, RiverDoctrineFusionEngine] = {}
        self.calibrators: Dict[str, Calibrator] = {}
        self._calibrated: Dict[str, bool] = {}
        self._lock = threading.Lock()

        self.position_router = PositionRouter(max_leverage=max_leverage)
        self.logger = PipelineLogger(db_path=PIPE_DB_PATH)
        self.asset_contexts: Dict[str, Dict[str, Any]] = {}
        self._last_route_ms: Dict[str, int] = {}
        self._last_fusion_log_ms: Dict[str, int] = {}
        self._last_logged_regime: Dict[str, str] = {}
        self._last_logged_state: Dict[str, str] = {}

        for asset in assets:
            self.engines[asset] = RiverDoctrineFusionEngine(asset=asset, warmup_ticks=warmup_ticks)
            self.calibrators[asset] = Calibrator(min_ticks=warmup_ticks)
            self._calibrated[asset] = False
            self.asset_contexts[asset] = self._new_asset_context()
            self._last_route_ms[asset] = 0
            self._last_fusion_log_ms[asset] = 0
            self._last_logged_regime[asset] = "NEUTRAL"
            self._last_logged_state[asset] = "NEUTRAL"

    @staticmethod
    def _new_asset_context() -> Dict[str, Any]:
        return {
            "velocity_score": 0.0,
            "forensic_score": 0.0,
            "confidence_score": 0.0,
            "regime_state": "NEUTRAL",
            "recent_emergency_count": 0,
            "entropy_score": 0.0,
            "last_transition_ms": 0,
            "_last_price": None,
            "_returns": deque(maxlen=FUSION_WINDOW),
            "_volumes": deque(maxlen=FUSION_WINDOW),
            "_signed_imbalances": deque(maxlen=FUSION_WINDOW),
            "_directions": deque(maxlen=FUSION_WINDOW),
            "_state_history": deque(maxlen=FUSION_WINDOW),
            "_velocity_direction": 0.0,
            "_structure_direction": 0.0,
            "_last_state": "NEUTRAL",
            "_last_emergency_ms": 0,
            "_active_state": "NEUTRAL",
            "_active_exposure": 0.0,
            "_active_since_ms": 0,
        }

    @staticmethod
    def _state_flip_rate(history: deque) -> float:
        if len(history) < 2:
            return 0.0
        flips = 0
        vals = list(history)
        for i in range(1, len(vals)):
            if vals[i] != vals[i - 1]:
                flips += 1
        return flips / float(max(len(vals) - 1, 1))

    @staticmethod
    def _directional_instability(directions: deque) -> float:
        if not directions:
            return 1.0
        return 1.0 - abs(float(np.mean(np.array(directions, dtype=np.float64))))

    def _classify_regime(
        self,
        volatility: float,
        persistence: float,
        volume_asymmetry: float,
        entropy_score: float,
        recent_emergency_count: int,
        last_emergency_ms: int,
        now_ms: int,
    ) -> str:
        if recent_emergency_count >= 3 or entropy_score > 0.82:
            return "CHAOTIC"
        if last_emergency_ms > 0 and now_ms - last_emergency_ms < RECOVERY_WINDOW_MS:
            return "RECOVERY"
        if volatility < 0.00035 and persistence < 0.25:
            return "COMPRESSED"
        if persistence > 0.58 and volatility >= 0.00025 and volume_asymmetry > 0.08:
            return "TRENDING"
        if volatility < 0.00075 and entropy_score < 0.60:
            return "CALM"
        if entropy_score > 0.70:
            return "CHAOTIC"
        return "TRENDING" if persistence > 0.45 else "CALM"

    @staticmethod
    def _regime_multiplier(regime: str, now_ms: int, last_emergency_ms: int) -> float:
        if regime == "TRENDING":
            return 1.20
        if regime == "COMPRESSED":
            return 1.08
        if regime == "CHAOTIC":
            return 0.30
        if regime == "RECOVERY":
            elapsed = now_ms - last_emergency_ms
            ratio = _clamp(elapsed / float(RECOVERY_WINDOW_MS), 0.0, 1.0)
            return 0.35 + (0.65 * ratio)
        return 0.82

    @staticmethod
    def _confidence_threshold_for_regime(regime: str) -> float:
        if regime == "TRENDING":
            return BASE_CONFIDENCE_THRESHOLD - 0.06
        if regime == "COMPRESSED":
            return BASE_CONFIDENCE_THRESHOLD - 0.08
        if regime == "CHAOTIC":
            return BASE_CONFIDENCE_THRESHOLD + 0.15
        if regime == "RECOVERY":
            return BASE_CONFIDENCE_THRESHOLD + 0.10
        return BASE_CONFIDENCE_THRESHOLD

    @staticmethod
    def _entropy_threshold_for_regime(regime: str) -> float:
        if regime == "TRENDING":
            return BASE_ENTROPY_THRESHOLD + 0.06
        if regime == "COMPRESSED":
            return BASE_ENTROPY_THRESHOLD + 0.04
        if regime == "CHAOTIC":
            return BASE_ENTROPY_THRESHOLD - 0.20
        if regime == "RECOVERY":
            return BASE_ENTROPY_THRESHOLD - 0.10
        return BASE_ENTROPY_THRESHOLD

    def _update_fusion_context(self, asset: str, tick: Tick, river_state_name: str) -> Dict[str, Any]:
        ctx = self.asset_contexts[asset]
        now_ms = tick.timestamp_ms
        last_price = ctx["_last_price"]
        ret = 0.0
        if last_price is not None and last_price > 0.0:
            ret = (tick.price - last_price) / last_price
        ctx["_last_price"] = tick.price

        direction = 0.0
        if ret > 0.0:
            direction = 1.0
        elif ret < 0.0:
            direction = -1.0

        imbalance_signed = (
            (tick.top_bid_qty - tick.top_ask_qty)
            / max(tick.top_bid_qty + tick.top_ask_qty, 1e-9)
        )

        ctx["_returns"].append(ret)
        ctx["_volumes"].append(tick.volume)
        ctx["_signed_imbalances"].append(imbalance_signed)
        ctx["_directions"].append(direction)
        ctx["_state_history"].append(river_state_name)

        if river_state_name == "EMERGENCY":
            ctx["_last_emergency_ms"] = now_ms

        returns_arr = np.array(list(ctx["_returns"]) or [0.0], dtype=np.float64)
        volumes_arr = np.array(list(ctx["_volumes"]) or [tick.volume], dtype=np.float64)
        imbalances_arr = np.array(list(ctx["_signed_imbalances"]) or [imbalance_signed], dtype=np.float64)
        directions_arr = np.array(list(ctx["_directions"]) or [0.0], dtype=np.float64)

        volatility = float(np.std(returns_arr))
        mean_volume = float(np.mean(volumes_arr))
        persistence = abs(float(np.mean(directions_arr)))
        volume_asymmetry = abs(float(np.mean(imbalances_arr)))

        normalized_delta = abs(ret) / max(volatility, 1e-7)
        vol_weight = _clamp(volatility / 0.0008, 0.25, 1.50)
        velocity_score = _clamp(
            (normalized_delta / (1.0 + normalized_delta)) * vol_weight,
            0.0,
            1.0,
        )
        velocity_direction = _clamp(ret / max(volatility * 2.0, 1e-7), -1.0, 1.0)

        volume_expansion = _clamp((tick.volume / max(mean_volume, 1e-9) - 0.8) / 1.6, 0.0, 1.0)
        imbalance_score = _clamp(abs(imbalance_signed) * 2.5, 0.0, 1.0)
        compression_score = 1.0 - _clamp(volatility / 0.0015, 0.0, 1.0)
        exhaustion_score = _clamp(
            (abs(ret) / max(volatility, 1e-7) - 1.0) / 2.0,
            0.0,
            1.0,
        )
        abrupt_shift = 0.0
        if len(ctx["_directions"]) >= 2:
            prev_dir = list(ctx["_directions"])[-2]
            if direction != 0.0 and prev_dir != 0.0 and direction != prev_dir:
                abrupt_shift = 1.0

        structure_score = _clamp(
            (0.30 * volume_expansion)
            + (0.25 * imbalance_score)
            + (0.25 * max(compression_score, exhaustion_score))
            + (0.20 * abrupt_shift),
            0.0,
            1.0,
        )
        structure_direction = _clamp((0.65 * imbalance_signed) + (0.35 * velocity_direction), -1.0, 1.0)

        state_flip_rate = self._state_flip_rate(ctx["_state_history"])
        directional_instability = self._directional_instability(ctx["_directions"])
        coherence = abs(float(np.mean(np.sign(returns_arr) * np.sign(imbalances_arr))))
        coherence_collapse = 1.0 - _clamp(coherence, 0.0, 1.0)
        entropy_score = _clamp(
            (0.40 * state_flip_rate)
            + (0.35 * directional_instability)
            + (0.25 * coherence_collapse),
            0.0,
            1.0,
        )

        recent_emergency_count = 0
        for s in ctx["_state_history"]:
            if s == "EMERGENCY":
                recent_emergency_count += 1

        regime = self._classify_regime(
            volatility=volatility,
            persistence=persistence,
            volume_asymmetry=volume_asymmetry,
            entropy_score=entropy_score,
            recent_emergency_count=recent_emergency_count,
            last_emergency_ms=ctx["_last_emergency_ms"],
            now_ms=now_ms,
        )

        river_weight = {
            "LONG": 0.75,
            "SHORT": 0.75,
            "NEUTRAL": 0.45,
            "RECOVERY": 0.35,
            "EMERGENCY": 0.0,
        }.get(river_state_name, 0.45)

        confidence_raw = (0.35 * river_weight) + (0.30 * velocity_score) + (0.35 * structure_score)
        if regime == "TRENDING":
            confidence_raw += 0.10
        elif regime == "COMPRESSED":
            confidence_raw += 0.05
        elif regime == "CHAOTIC":
            confidence_raw -= 0.20
        elif regime == "RECOVERY":
            confidence_raw -= 0.10

        confidence_score = _clamp(confidence_raw * (1.0 - (0.75 * entropy_score)), 0.0, 1.0)
        if river_state_name == "EMERGENCY":
            confidence_score = 0.0

        if river_state_name != ctx["_last_state"]:
            ctx["last_transition_ms"] = now_ms
            ctx["_last_state"] = river_state_name

        ctx["velocity_score"] = velocity_score
        ctx["forensic_score"] = structure_score
        ctx["confidence_score"] = confidence_score
        ctx["regime_state"] = regime
        ctx["recent_emergency_count"] = recent_emergency_count
        ctx["entropy_score"] = entropy_score
        ctx["_velocity_direction"] = velocity_direction
        ctx["_structure_direction"] = structure_direction
        return ctx

    def _arbitrate_exposure(
        self,
        asset: str,
        river_state_name: str,
        ctx: Dict[str, Any],
        now_ms: int,
    ) -> Tuple[str, float, float, float, float]:
        if river_state_name == "EMERGENCY":
            ctx["_active_state"] = "EMERGENCY"
            ctx["_active_exposure"] = 0.0
            ctx["_active_since_ms"] = now_ms
            return "EMERGENCY", 0.0, 0.0, 0.0, 0.0

        river_direction = self.position_router.directional_signal_from_state(river_state_name)
        directional_signal = _clamp(
            (0.50 * river_direction)
            + (0.30 * ctx["_velocity_direction"])
            + (0.20 * ctx["_structure_direction"]),
            -1.0,
            1.0,
        )
        if abs(directional_signal) < 0.10:
            directional_signal = 0.0

        regime_multiplier = self._regime_multiplier(
            ctx["regime_state"], now_ms, ctx["_last_emergency_ms"]
        )

        emergency_suppression = 1.0
        if ctx["_last_emergency_ms"] > 0:
            since_emergency = now_ms - ctx["_last_emergency_ms"]
            if since_emergency < RECOVERY_WINDOW_MS:
                recovery_ratio = _clamp(since_emergency / float(RECOVERY_WINDOW_MS), 0.0, 1.0)
                emergency_suppression = 0.25 + (0.75 * recovery_ratio)

        weighted_target = self.position_router.weighted_target_exposure(
            directional_signal=directional_signal,
            confidence_score=ctx["confidence_score"],
            regime_multiplier=regime_multiplier,
            emergency_suppression=emergency_suppression,
        )

        confidence_floor = self._confidence_threshold_for_regime(ctx["regime_state"])
        entropy_ceiling = self._entropy_threshold_for_regime(ctx["regime_state"])
        no_recent_emergency_lock = True
        if ctx["_last_emergency_ms"] > 0 and now_ms - ctx["_last_emergency_ms"] < RECENT_EMERGENCY_LOCK_MS:
            no_recent_emergency_lock = False

        filters_pass = (
            ctx["confidence_score"] >= confidence_floor
            and ctx["entropy_score"] <= entropy_ceiling
            and no_recent_emergency_lock
        )

        candidate_state = "NEUTRAL"
        candidate_exposure = 0.0
        if filters_pass and abs(weighted_target) >= 0.02 and directional_signal != 0.0:
            candidate_state = "LONG" if weighted_target > 0.0 else "SHORT"
            candidate_exposure = weighted_target

        active_state = str(ctx.get("_active_state", "NEUTRAL"))
        active_exposure = float(ctx.get("_active_exposure", 0.0))
        active_since = int(ctx.get("_active_since_ms", 0))
        min_hold_ms = 1000

        if active_state in ("LONG", "SHORT"):
            held_for_ms = now_ms - active_since
            if held_for_ms < min_hold_ms:
                candidate_state = active_state
                candidate_exposure = active_exposure
            elif candidate_state == "NEUTRAL":
                if ctx["confidence_score"] > (confidence_floor - 0.05):
                    candidate_state = active_state
                    candidate_exposure = active_exposure * 0.90
            elif candidate_state != active_state and ctx["confidence_score"] < (confidence_floor + 0.08):
                candidate_state = active_state
                candidate_exposure = active_exposure

        if active_state == "NEUTRAL" and candidate_state in ("LONG", "SHORT"):
            if ctx["confidence_score"] < (confidence_floor + 0.03):
                candidate_state = "NEUTRAL"
                candidate_exposure = 0.0

        if candidate_state in ("LONG", "SHORT"):
            if active_state == candidate_state and abs(active_exposure) > 1e-9:
                candidate_exposure = (0.70 * active_exposure) + (0.30 * candidate_exposure)
            candidate_exposure = _clamp(candidate_exposure, -1.0, 1.0)

        if candidate_state != active_state:
            ctx["_active_state"] = candidate_state
            ctx["_active_since_ms"] = now_ms
        if candidate_state in ("LONG", "SHORT"):
            ctx["_active_exposure"] = candidate_exposure
            return candidate_state, candidate_exposure, directional_signal, regime_multiplier, emergency_suppression

        ctx["_active_state"] = "NEUTRAL"
        ctx["_active_exposure"] = 0.0
        return "NEUTRAL", 0.0, directional_signal, regime_multiplier, emergency_suppression

    def _should_route_command(
        self,
        asset: str,
        new_state: str,
        target_exposure: float,
        last_cmd: Optional[Dict[str, Any]],
        now_ms: int,
    ) -> bool:
        if last_cmd is None:
            return True

        last_state = str(last_cmd["state"])
        last_target = float(last_cmd["target_exposure"])
        state_changed = last_state != new_state
        target_changed = abs(last_target - target_exposure) >= ROUTE_DELTA_THRESHOLD
        interval_ok = (now_ms - self._last_route_ms.get(asset, 0)) >= ROUTE_MIN_INTERVAL_MS

        if state_changed:
            return True
        if new_state in ("LONG", "SHORT") and target_changed and interval_ok:
            return True
        return False

    def _maybe_log_fusion(self, asset: str, ctx: Dict[str, Any], target_exposure: float, now_ms: int) -> None:
        exposure_state = "NEUTRAL"
        if target_exposure > 0.0:
            exposure_state = "LONG"
        elif target_exposure < 0.0:
            exposure_state = "SHORT"

        should_log = False
        if now_ms - self._last_fusion_log_ms.get(asset, 0) >= FUSION_LOG_INTERVAL_MS:
            should_log = True
        if self._last_logged_regime.get(asset) != ctx["regime_state"]:
            should_log = True
        if self._last_logged_state.get(asset) != exposure_state:
            should_log = True

        if should_log:
            print(
                "[FUSION] asset="
                + asset
                + " regime="
                + ctx["regime_state"]
                + " confidence="
                + format(ctx["confidence_score"], ".2f")
                + " velocity="
                + format(ctx["velocity_score"], ".2f")
                + " structure="
                + format(ctx["forensic_score"], ".2f")
                + " entropy="
                + format(ctx["entropy_score"], ".2f")
                + " target_exposure="
                + format(target_exposure, ".2f")
            )
            self._last_fusion_log_ms[asset] = now_ms
            self._last_logged_regime[asset] = ctx["regime_state"]
            self._last_logged_state[asset] = exposure_state

    def calibrate_all(self, tape_dict: Dict[str, List[Tick]]) -> Dict[str, bool]:
        results = {}
        with self._lock:
            for asset, tape in tape_dict.items():
                if asset not in self.engines:
                    continue
                engine = self.engines[asset]
                for tick in tape:
                    engine.ingest(tick)

                calibrator = self.calibrators[asset]
                for tick in tape:
                    calibrator.ingest(tick)

                self._calibrated[asset] = calibrator.is_ready
                results[asset] = calibrator.is_ready

                if calibrator.is_ready:
                    print("[CALIBRATED] " + asset + " engine armed.")
                else:
                    print(
                        "[WARNING] " + asset + " failed to calibrate. "
                        + "Check warm-up tick count."
                    )
        return results

    def ingest(self, asset: str, tick: Tick) -> None:
        if asset not in self.engines:
            print("[ERROR] Dropping tick. Unknown asset: " + asset)
            return

        engine = self.engines[asset]
        river_state_name = "NEUTRAL"
        fusion_now_ms = tick.timestamp_ms

        if not self._calibrated.get(asset, False):
            warmup_state = engine.ingest(tick)
            if isinstance(warmup_state, EngineState):
                river_state_name = warmup_state.name
            self.calibrators[asset].ingest(tick)
            self._update_fusion_context(asset, tick, river_state_name)
            if self.calibrators[asset].is_ready:
                with self._lock:
                    self._calibrated[asset] = True
                print("[CALIBRATED] " + asset + " engine armed via live stream.")
            return

        start_time = time.time()
        new_state = engine.ingest(tick)
        river_state_name = new_state.name
        fusion_now_ms = tick.timestamp_ms
        ctx = self._update_fusion_context(asset, tick, river_state_name)

        routed_state, target_exposure, directional_signal, regime_multiplier, emergency_suppression = (
            self._arbitrate_exposure(asset, river_state_name, ctx, fusion_now_ms)
        )
        command = self.position_router.get_exposure_command(
            asset=asset,
            state_name=routed_state,
            target_exposure=target_exposure,
        )

        self._maybe_log_fusion(asset, ctx, target_exposure, fusion_now_ms)

        with self._lock:
            last_cmd = self.logger.get_latest_exposure(asset)
            should_route = self._should_route_command(
                asset=asset,
                new_state=routed_state,
                target_exposure=command["target_exposure"],
                last_cmd=last_cmd,
                now_ms=fusion_now_ms,
            )
            if should_route:
                self.logger.log_exposure_command(command)
                self._last_route_ms[asset] = fusion_now_ms
                print(
                    "[ROUTED] " + asset + " | State: " + routed_state
                    + " | Target Exposure: " + str(command["target_exposure"])
                )

        if hasattr(engine, "last_diagnostic") and engine.last_diagnostic:
            latency_ms = (time.time() - start_time) * 1000.0
            diagnostic = dict(engine.last_diagnostic)
            diagnostic["fusion"] = {
                "regime_state": self.asset_contexts[asset]["regime_state"],
                "confidence_score": round(self.asset_contexts[asset]["confidence_score"], 6),
                "velocity_score": round(self.asset_contexts[asset]["velocity_score"], 6),
                "forensic_score": round(self.asset_contexts[asset]["forensic_score"], 6),
                "entropy_score": round(self.asset_contexts[asset]["entropy_score"], 6),
                "directional_signal": round(directional_signal, 6),
                "regime_multiplier": round(regime_multiplier, 6),
                "emergency_suppression": round(emergency_suppression, 6),
                "target_exposure": round(target_exposure, 6),
                "routed_state": routed_state,
                "river_state": river_state_name,
            }
            self.logger.log_diagnostic(asset, diagnostic, latency_ms)

    def get_exposure(self, asset: str) -> float:
        last_cmd = self.logger.get_latest_exposure(asset)
        if last_cmd:
            return float(last_cmd["target_exposure"])
        return 0.0


# =============================================================================
# FEEDS
# =============================================================================

class Delta1DatabaseFeed:
    """
    Reads per-asset market ticks from Delta1.py and routes them into the fleet.
    Time-bucketed: polls at 245ms to match Delta1 bucket interval.
    """

    def __init__(
        self,
        fleet: FleetManager,
        db_path: str = PIPE_DB_PATH,
        poll_interval_ms: int = 245,
    ):
        self.fleet = fleet
        self.db_path = db_path
        self.poll_interval = poll_interval_ms / 1000.0
        self.is_running = False
        self._last_sequence_id = 0
        self._idle_loops = 0
        self._conn = _open_sqlite(self.db_path)
        self._last_tick_timestamp_ms: Optional[int] = None

    def _fetch_new_ticks(self) -> List[Any]:
        c = self._conn.cursor()
        c.execute(
            "SELECT sequence_id, timestamp_ms, price, volume, asset "
            + "FROM " + MARKET_TICKS_TABLE + " "
            + "WHERE sequence_id > ? ORDER BY sequence_id ASC LIMIT 1000",
            (self._last_sequence_id,),
        )
        rows = c.fetchall()
        if rows and self._idle_loops % 20 == 0:
            print(f"[FEED] Fetched {len(rows)} new rows from DB. Last seq: {self._last_sequence_id}")
        return rows

    def start_stream(self) -> None:
        self.is_running = True
        print("\n=== STARTING DELTA1 DATABASE FEED ===")
        print("DB Path: " + self.db_path)
        print("Table: " + MARKET_TICKS_TABLE)
        print("Poll Interval: " + str(self.poll_interval * 1000) + "ms (matches Delta1 bucket)")

        try:
            while self.is_running:
                rows = self._fetch_new_ticks()

                if not rows:
                    self._idle_loops += 1
                    if self._idle_loops % 100 == 0:
                        print("[WAIT] No new Delta1 ticks yet. Polling...")
                    time.sleep(self.poll_interval)
                    continue

                self._idle_loops = 0
                for row in rows:
                    sequence_id = int(row[0])
                    timestamp_ms = int(row[1])
                    price = float(row[2])
                    volume = float(row[3])
                    asset = str(row[4]) if len(row) > 4 else "BTCUSDT"
                    self._last_sequence_id = sequence_id

                    if self._last_tick_timestamp_ms is not None:
                        delta_ms = timestamp_ms - self._last_tick_timestamp_ms
                        if delta_ms > 0:
                            sleep_s = min(delta_ms / 1000.0, self.poll_interval)
                            if sleep_s > 0.0:
                                time.sleep(sleep_s)
                    self._last_tick_timestamp_ms = timestamp_ms

                    tick = Tick(
                        timestamp_ms=timestamp_ms,
                        price=price,
                        volume=volume,
                        top_bid_qty=volume * 0.4,
                        top_ask_qty=volume * 0.4,
                    )
                    self.fleet.ingest(asset, tick)
        except KeyboardInterrupt:
            print("\n=== STREAM TERMINATED BY USER ===")
            self.is_running = False
        finally:
            self._conn.close()


class BinanceWebSocketFeed:
    """Real Binance combined WebSocket stream for multiple assets."""

    def __init__(self, fleet: FleetManager, symbols: List[str]):
        self.fleet = fleet
        self.symbols = [s.lower() for s in symbols]
        self.is_running = False
        self._ws = None
        self._seq = 0
        streams = "/".join([f"{s}@trade" for s in self.symbols])
        self._uri = "wss://stream.binance.com:9443/stream?streams=" + streams

    async def connect(self):
        try:
            import websockets
            self._ws = await websockets.connect(self._uri)
            print("[WS] Connected to Binance combined stream: " + self._uri)
        except ImportError:
            print("[FATAL] websockets library not installed. Run: python3 -m pip install websockets")
            raise
        except Exception as e:
            print("[FATAL] WebSocket connection failed: " + str(e))
            raise

    async def start_stream(self) -> None:
        self.is_running = True
        print("\n=== STARTING LIVE BINANCE WEBSOCKET FEED ===")
        print("URI: " + self._uri)

        if self._ws is None:
            await self.connect()

        try:
            while self.is_running:
                try:
                    msg = await asyncio.wait_for(self._ws.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    print("[WS] No data for 5s, reconnecting...")
                    await self.connect()
                    continue

                payload = json.loads(msg)
                if "data" in payload:
                    data = payload["data"]
                else:
                    data = payload

                self._seq += 1
                symbol = data.get("s", "BTCUSDT").upper()
                price = float(data.get("p", 0.0))
                volume = float(data.get("q", 0.0))
                timestamp_ms = data.get("T", int(time.time() * 1000))

                tick = Tick(
                    timestamp_ms=timestamp_ms,
                    price=price,
                    volume=volume,
                    top_bid_qty=volume * 0.4,
                    top_ask_qty=volume * 0.4,
                )
                self.fleet.ingest(symbol, tick)
        except KeyboardInterrupt:
            print("\n=== STREAM TERMINATED BY USER ===")
            self.is_running = False
        except Exception as e:
            print("[WS ERROR] " + str(e))
            self.is_running = False
        finally:
            if self._ws:
                await self._ws.close()


class WebSocketFeed:
    """Mock feed for testing - generates realistic multi-asset data."""

    def __init__(self, fleet: FleetManager, tps: int = 100):
        self.fleet = fleet
        self.is_running = False
        self._seq = 0
        self._base_prices = {"BTCUSDT": 75000.0, "ETHUSDT": 3800.0, "SOLUSDT": 150.0}
        self._vols = {"BTCUSDT": 0.0003, "ETHUSDT": 0.0005, "SOLUSDT": 0.0008}
        self.tps = tps

    def start_stream(self) -> None:
        self.is_running = True
        print("\n=== STARTING HIGH-FREQUENCY MOCK FEED ===")
        print(f"Target TPS: {self.tps} per asset")

        try:
            while self.is_running:
                for asset in self.fleet.assets:
                    for _ in range(self.tps):
                        self._seq += 1
                        base = self._base_prices.get(asset, 75000.0)
                        vol = self._vols.get(asset, 0.0003)
                        price = base * (1.0 + random.gauss(0, vol))
                        self._base_prices[asset] = price
                        volume = random.random() * 0.5

                        tick = Tick(
                            timestamp_ms=int(time.time() * 1000),
                            price=price,
                            volume=volume,
                            top_bid_qty=volume * 0.4,
                            top_ask_qty=volume * 0.4,
                        )
                        self.fleet.ingest(asset, tick)
                time.sleep(1.0)
        except KeyboardInterrupt:
            print("\n=== STREAM TERMINATED BY USER ===")
            self.is_running = False


# =============================================================================
# SYSTEM INITIALIZATION  —  BTCUSDT WEBSOCKET ONLY
# =============================================================================

if __name__ == "__main__":
    # FORCE BTCUSDT WEBSOCKET ONLY — NO MOCK, NO DB BRIDGE, NO ETH/SOL
    universe = ["BTCUSDT"]

    print("Initializing Fleet Router...")
    fleet = FleetManager(assets=universe, warmup_ticks=50, max_leverage=1.0)
    print("Assets: " + str(universe))
    print("Feed Source: LIVE BINANCE WEBSOCKET (DIRECT — NO DB BRIDGE)")
    print("DB Path: " + PIPE_DB_PATH + " (used for command logging only)")

    feed = BinanceWebSocketFeed(fleet, universe)
    asyncio.run(feed.start_stream())
