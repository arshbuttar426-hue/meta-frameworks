"""
FLEET MANAGER v5.0 — Tensor Gateway
Python 3.14 | O(1) Risk & Hysteresis | BTCUSDT Only
Reads from delt.py tensor_quantum.db → Writes to exposure_commands
"""

import sqlite3
import threading
import time
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

# ── CONFIG ──────────────────────────────────────────────────────
DB_PATH = os.environ.get("TRADING_DB_PATH", "tensor_quantum.db")
PIPE_DB_PATH = os.environ.get("TRADING_PIPE_DB_PATH", "pipeline_macro.db")
POLL_INTERVAL_MS = 245
EMERGENCY_LOCK_STRESS = 0.90
EMERGENCY_UNLOCK_STRESS = 0.50
TIME_LOCK_MS = 5000
DECAY_STEP = 0.25
ASSET = "BTCUSDT"

SQLITE_TIMEOUT_SEC = 30.0
SQLITE_BUSY_TIMEOUT_MS = 5000


# ── DATA STRUCTURES ─────────────────────────────────────────────
@dataclass
class TickPacket:
    sequence_id: int
    timestamp_ms: int
    price: float
    signal: str
    core_stress: float


# ── 1. TENSOR FEED ────────────────────────────────────────────
class TensorFeed:
    """
    Polls tensor_quantum.db every 245ms.
    O(1) extraction: one SELECT, one row, five columns.
    """

    def __init__(self, db_path: str = DB_PATH, poll_interval_ms: int = POLL_INTERVAL_MS):
        self.db_path = db_path
        self.poll_interval = poll_interval_ms / 1000.0
        self._last_sequence_id = 0
        self._conn = sqlite3.connect(
            db_path, check_same_thread=False, timeout=SQLITE_TIMEOUT_SEC
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")

    def poll(self) -> Optional[TickPacket]:
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT sequence_id, timestamp_ms, price, signal, core_stress "
            "FROM quantum_log WHERE sequence_id > ? "
            "ORDER BY sequence_id DESC LIMIT 1",
            (self._last_sequence_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        self._last_sequence_id = int(row[0])
        return TickPacket(
            sequence_id=int(row[0]),
            timestamp_ms=int(row[1]),
            price=float(row[2]),
            signal=str(row[3]),
            core_stress=float(row[4]),
        )

    def run(self, callback) -> None:
        print(f"[TensorFeed] Connected to {self.db_path}")
        print(f"[TensorFeed] Polling every {self.poll_interval * 1000:.0f}ms")
        try:
            while True:
                try:
                    packet = self.poll()
                except sqlite3.OperationalError:
                    packet = None
                if packet:
                    callback(packet)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[TensorFeed] Shutting down.")


# ── 2. RISK ARBITRATOR ──────────────────────────────────────────
class RiskArbitrator:
    """
    Absolute shield. One number in: core_stress.
    One of two states out: SAFE or EMERGENCY.
    """

    def __init__(
        self,
        lock_threshold: float = EMERGENCY_LOCK_STRESS,
        unlock_threshold: float = EMERGENCY_UNLOCK_STRESS,
    ):
        self.lock_threshold = lock_threshold
        self.unlock_threshold = unlock_threshold
        self._emergency = False

    def check(self, signal: str, core_stress: float) -> str:
        # If already in emergency, require core_stress to drop below unlock threshold
        if self._emergency:
            if core_stress < self.unlock_threshold:
                self._emergency = False
                print(f"[RISK] Emergency cleared. core_stress={core_stress:.4f}")
            else:
                # Stay in emergency regardless of incoming signal
                return "CRASH_HALT"

        # Enter emergency if stress spikes or if delt.py itself issued a halt
        if core_stress > self.lock_threshold or signal in (
            "DRAWDOWN_HALT",
            "LOCKOUT",
            "EMERGENCY",
        ):
            self._emergency = True
            print(
                f"[RISK] EMERGENCY LOCKOUT. core_stress={core_stress:.4f} signal={signal}"
            )
            return "CRASH_HALT"

        return signal


# ── 3. HYSTERESIS ENGINE ──────────────────────────────────────
class HysteresisEngine:
    """
    Emotion filter. Converts raw signal into smooth target_exposure.
    Time-lock: 5-second directional hold.
    Decay: steps down by 0.25 per tick on HOLD.
    """

    def __init__(self, time_lock_ms: int = TIME_LOCK_MS, decay_step: float = DECAY_STEP):
        self.time_lock_ms = time_lock_ms
        self.decay_step = decay_step
        self._current_exposure = 0.0
        self._lock_until_ms = 0

    def process(self, signal: str, now_ms: int) -> float:
        if signal == "CRASH_HALT":
            self._current_exposure = 0.0
            return 0.0
        if signal == "BUY":
            # If locked in opposite direction (short), refuse
            if self._current_exposure < 0 and now_ms < self._lock_until_ms:
                return self._current_exposure
            self._current_exposure = 1.0
            self._lock_until_ms = now_ms + self.time_lock_ms
            return 1.0

        if signal == "SELL":
            # If locked in opposite direction (long), refuse
            if self._current_exposure > 0 and now_ms < self._lock_until_ms:
                return self._current_exposure
            self._current_exposure = -1.0
            self._lock_until_ms = now_ms + self.time_lock_ms
            return -1.0

        # HOLD, NEUTRAL, or any halted signal: decay toward zero
        if self._current_exposure > 0:
            self._current_exposure = max(0.0, self._current_exposure - self.decay_step)
        elif self._current_exposure < 0:
            self._current_exposure = min(0.0, self._current_exposure + self.decay_step)

        return self._current_exposure


# ── 4. PIPELINE LOGGER ──────────────────────────────────────────
class PipelineLogger:
    """
    Hand-off to execution bridge. Writes exposure_commands to SQLite WAL.
    Thread-local connections for sacred invariant compliance.
    """

    def __init__(self, db_path: str = PIPE_DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=SQLITE_TIMEOUT_SEC,
            )
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        return self._local.conn

    def _init_db(self) -> None:
        c = self._conn().cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS exposure_commands ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "asset TEXT NOT NULL, "
            "state TEXT NOT NULL, "
            "target_exposure REAL NOT NULL, "
            "timestamp_ms INTEGER NOT NULL, "
            "UNIQUE(asset, timestamp_ms)"
            ")"
        )
        self._conn().commit()

    def log(self, asset: str, state: str, target_exposure: float, timestamp_ms: int) -> None:
        c = self._conn().cursor()
        ts = int(timestamp_ms)
        inserted = False
        for _ in range(5):
            try:
                c.execute(
                    "INSERT INTO exposure_commands (asset, state, target_exposure, timestamp_ms) "
                    "VALUES (?, ?, ?, ?)",
                    (asset, state, target_exposure, ts),
                )
                inserted = True
                break
            except sqlite3.IntegrityError:
                ts += 1
        if not inserted:
            c.execute(
                "INSERT OR REPLACE INTO exposure_commands (asset, state, target_exposure, timestamp_ms) "
                "VALUES (?, ?, ?, ?)",
                (asset, state, target_exposure, ts),
            )
        self._conn().commit()

    def get_latest(self, asset: str) -> Optional[Dict[str, Any]]:
        c = self._conn().cursor()
        c.execute(
            "SELECT state, target_exposure FROM exposure_commands "
            "WHERE asset = ? ORDER BY timestamp_ms DESC LIMIT 1",
            (asset,),
        )
        row = c.fetchone()
        if row:
            return {"state": row[0], "target_exposure": row[1]}
        return None


# ── MAIN ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("FLEET MANAGER v5.0 — Tensor Gateway")
    print("Asset: BTCUSDT | O(1) Risk + Hysteresis")
    print("=" * 60)

    risk = RiskArbitrator()
    hysteresis = HysteresisEngine()
    logger = PipelineLogger()
    feed = TensorFeed()

    def on_packet(packet: TickPacket) -> None:
        # 1. Risk gate
        safe_signal = risk.check(packet.signal, packet.core_stress)

        # 2. Hysteresis smoothing
        exposure = hysteresis.process(safe_signal, packet.timestamp_ms)

        # 3. Log only if exposure or state changed
        last = logger.get_latest(ASSET)
        if (
            last is None
            or last["target_exposure"] != exposure
            or last["state"] != safe_signal
        ):
            logger.log(ASSET, safe_signal, exposure, packet.timestamp_ms)
            print(
                f"[FLEET] seq={packet.sequence_id} price={packet.price:.2f} "
                f"raw={packet.signal} safe={safe_signal} exposure={exposure:+.2f} "
                f"stress={packet.core_stress:.4f}"
            )

    print(f"[MAIN] DB read:  {DB_PATH}")
    print(f"[MAIN] DB write: {PIPE_DB_PATH}")
    print("[MAIN] Entering poll loop. Press Ctrl+C to exit.")
    feed.run(on_packet)
