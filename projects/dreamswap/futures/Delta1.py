"""
RIVER DOCTRINE Delta1.py v4.1
Time-Bucketed BTCUSDT-Only | Real Binance WebSocket | 245ms Heartbeat
Python 3.14 | Fixed Class Structure | BTCUSDT ONLY
"""

import asyncio
import time
import json
import sqlite3
import threading
import sys
import os
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from collections import deque
from typing import Optional, Dict, Any, List

# ── OPTIONAL WEBSOCKETS ─────────────────────────────────────────
try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

# ── CONFIG ──────────────────────────────────────────────────────
SEQ_QUEUE_MAXSIZE = 100000
PIPE_QUEUE_MAXSIZE = 5000
BUCKET_INTERVAL_MS = 245.0
BURST_DURATION_SEC = 30
BURST_RATE_TPS = 5000
NORMAL_RATE_TPS = 100
PIPELINE_NORMAL_LATENCY_MS = 50
PIPELINE_DEGRADED_LATENCY_MS = 10
PIPELINE_SURVIVAL_LATENCY_MS = 2

P99_THRESHOLD_MS = 5.0
P99_9_THRESHOLD_MS = 20.0
DRAIN_TARGET_SIZE = 100
Z_COOLDOWN_TICKS = 50
Z_VIOLATION_DELTA = 10000.0
DRAWDOWN_PCT = 0.95

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEQ_DB_PATH = os.environ.get("TRADING_SEQ_DB_PATH") or os.path.join(_SCRIPT_DIR, "sequencer_quantum.db")
PIPE_DB_PATH = os.environ.get("TRADING_PIPE_DB_PATH") or os.path.join(_SCRIPT_DIR, "pipeline_macro.db")
SQLITE_TIMEOUT_SEC = 30.0
SQLITE_BUSY_TIMEOUT_MS = 5000
MARKET_TICKS_TABLE = "market_ticks"


def _open_sqlite(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=SQLITE_TIMEOUT_SEC)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=" + str(SQLITE_BUSY_TIMEOUT_MS))
    return conn

# ── DATA OBJECTS ─────────────────────────────────────────────────
@dataclass
class Tick:
    sequence_id: int
    timestamp_ms: int
    price: float
    volume: float
    asset: str = "BTCUSDT"

@dataclass
class EnrichedTick:
    tick: Tick
    jump: int = 0
    jump_ema: float = 0.0
    path_streak: float = 0.0
    z_score: float = 0.0
    is_in_violation: bool = False
    bucket_count: int = 1

@dataclass
class TimeBucket:
    asset: str = ""
    start_ts: int = 0
    end_ts: int = 0
    tick_count: int = 0
    open_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    close_price: float = 0.0
    total_volume: float = 0.0
    buy_volume_est: float = 0.0
    sell_volume_est: float = 0.0
    vwap_num: float = 0.0
    last_price: float = 0.0

    @property
    def vwap(self) -> float:
        return self.vwap_num / self.total_volume if self.total_volume > 0 else self.close_price

    @property
    def range(self) -> float:
        return self.high_price - self.low_price


# ── LIVE BINANCE FEED (BTCUSDT ONLY) ────────────────────────────
class BinanceFeed:
    """Real Binance WebSocket @trade stream. BTCUSDT only. No mock."""

    def __init__(self, symbol: str = "btcusdt"):
        self.symbol = symbol.lower()
        self._seq = 0
        self._ws = None

    async def connect(self):
        if not HAS_WEBSOCKETS:
            raise RuntimeError("websockets library not installed. Run: python3 -m pip install websockets")
        uri = "wss://stream.binance.com:9443/ws/" + self.symbol + "@trade"
        print("[WS] Connecting to " + uri)
        self._ws = await websockets.connect(uri)
        print("[WS] Connected.")

    async def recv(self) -> Tick:
        if self._ws is None:
            await self.connect()
        msg = await self._ws.recv()
        data = json.loads(msg)
        self._seq += 1
        return Tick(
            sequence_id=self._seq,
            timestamp_ms=data.get("T", int(time.time() * 1000)),
            price=float(data.get("p", 0.0)),
            volume=float(data.get("q", 0.0)),
            asset="BTCUSDT"
        )

    async def close(self):
        if self._ws:
            await self._ws.close()


# ── SEQUENCER NODE (Time-Bucketed Aggregation) ────────────────────
class SequencerNode:
    """
    Time-bucketed state aggregation. O(1) per tick. Clock-driven flush.
    Per-asset EMA, Z-score, and topology. Preserved class structure.
    """

    def __init__(self, executor: ThreadPoolExecutor, db_path: str, z_event: threading.Event):
        self.executor = executor
        self.z_event = z_event
        self._db_path = db_path

        self._processed = 0
        self._z_violations = 0
        self._z_cooldown = 0

        self._latency_history = deque(maxlen=10000)
        self._max_latency_ms = 0.0
        self._last_latency_ms = 0.0

        # PER-ASSET STATE
        self._buckets: Dict[str, TimeBucket] = {}
        self._bucket_lock = asyncio.Lock()
        self._last_ts: Dict[str, int] = {}
        self.dynamic_ref: Dict[str, float] = {}
        self.dynamic_var: Dict[str, float] = {}
        self.tau_ms: float = 5000.0
        self.MAX_DT_MS = 1000
        self.VOL_FLOOR_BPS = 0.00005

        # PER-ASSET HYSTERESIS
        self.TRIGGER_Z = 5.0
        self.CLEAR_Z = 2.0
        self.is_in_violation: Dict[str, bool] = {}
        self.stress_field: Dict[str, float] = {}
        self.density_tps: Dict[str, float] = {}

        # PER-ASSET TOPOLOGY
        self._prev_bracket: Dict[str, int] = {}
        self._prev_jump: Dict[str, int] = {}
        self.jump_ema: Dict[str, float] = {}
        self.path_streak: Dict[str, float] = {}

        # WARMUP: suppress Z-evaluation until variance stabilizes
        self._bucket_counts: Dict[str, int] = {}
        self.WARMUP_BUCKETS = 10

        # SQLITE
        self._batch = []
        self.BATCH_SIZE = 100
        self._last_flush = time.monotonic()
        self.tls = threading.local()

    def _new_bucket(self, asset: str, ts: int) -> TimeBucket:
        return TimeBucket(asset=asset, start_ts=ts)

    async def consume(self, tick: Tick) -> EnrichedTick:
        """O(1) accumulation. Returns lightweight interim object."""
        start = time.monotonic()
        asset = tick.asset

        async with self._bucket_lock:
            if asset not in self._buckets:
                self._buckets[asset] = self._new_bucket(asset, tick.timestamp_ms)
                self._last_ts[asset] = tick.timestamp_ms
                self.dynamic_ref[asset] = tick.price
                self.dynamic_var[asset] = (tick.price * 0.001) ** 2
                self.is_in_violation[asset] = False
                self.stress_field[asset] = 0.0
                self.density_tps[asset] = 0.0
                self.jump_ema[asset] = 0.0
                self.path_streak[asset] = 0.0

            b = self._buckets[asset]
            if b.tick_count == 0:
                b.start_ts = tick.timestamp_ms
                b.open_price = tick.price
            b.end_ts = tick.timestamp_ms
            b.tick_count += 1
            b.close_price = tick.price
            b.high_price = max(b.high_price, tick.price)
            b.low_price = min(b.low_price, tick.price)
            b.total_volume += tick.volume
            b.vwap_num += tick.price * tick.volume

            if b.last_price > 0:
                if tick.price > b.last_price:
                    b.buy_volume_est += tick.volume
                elif tick.price < b.last_price:
                    b.sell_volume_est += tick.volume
                else:
                    b.buy_volume_est += tick.volume * 0.5
                    b.sell_volume_est += tick.volume * 0.5
            b.last_price = tick.price

        self._processed += 1
        latency = (time.monotonic() - start) * 1000.0
        self._last_latency_ms = latency
        self._latency_history.append(latency)
        if latency > self._max_latency_ms:
            self._max_latency_ms = latency

        return EnrichedTick(tick=tick)

    async def flush_all(self) -> List[EnrichedTick]:
        """Atomic swap all buckets. Clock-driven 245ms."""
        async with self._bucket_lock:
            if not self._buckets:
                return []

            snapshots = []
            any_violation = False
            assets = list(self._buckets.keys())

            for asset in assets:
                b = self._buckets[asset]
                if b.tick_count == 0:
                    continue

                enriched = self._compute_bucket_physics(b)
                if enriched.is_in_violation:
                    any_violation = True
                snapshots.append(enriched)
                self._buckets[asset] = self._new_bucket(asset, b.end_ts)

            # Global Z-event logic (OR across assets)
            if any_violation:
                self._z_violations += 1
                self._z_cooldown = 0
                if not self.z_event.is_set():
                    self.z_event.set()
            else:
                self._z_cooldown += 1
                if self._z_cooldown >= Z_COOLDOWN_TICKS and self.z_event.is_set():
                    self.z_event.clear()
                    self._z_cooldown = 0

            return snapshots

    def _compute_bucket_physics(self, b: TimeBucket) -> EnrichedTick:
        asset = b.asset
        tick = Tick(
            sequence_id=0,
            timestamp_ms=b.end_ts,
            price=b.vwap,
            volume=b.total_volume,
            asset=asset
        )

        # 1. CLOCK-TIME EMA
        last_ts = self._last_ts.get(asset, b.end_ts)
        dt = b.end_ts - last_ts
        if dt < 0:
            dt = 0
        dt = min(dt, self.MAX_DT_MS)
        self._last_ts[asset] = b.end_ts

        alpha_eff = 1.0 - math.exp(-dt / self.tau_ms)

        # Tick density per bucket
        bucket_dur_ms = max(b.end_ts - b.start_ts, 1)
        inst_tps = b.tick_count / (bucket_dur_ms / 1000.0)
        self.density_tps[asset] = self.density_tps.get(asset, 0.0) * (1.0 - alpha_eff) + inst_tps * alpha_eff

        # 2. TRANSITION TOPOLOGY (cent-phase tracking)
        disp_mils = int(round((b.vwap % 100.0) * 1000))
        bracket = ((disp_mils % 1000) + 1000) % 1000 or 1000

        jump = 0
        prev_bracket = self._prev_bracket.get(asset)
        if prev_bracket is not None:
            raw_diff = bracket - prev_bracket
            jump = ((raw_diff + 500) % 1000) - 500
            self._prev_jump[asset] = jump

            abs_jump = abs(jump)
            self.jump_ema[asset] = (self.jump_ema.get(asset, 0.0) * (1.0 - alpha_eff)) + (abs_jump * alpha_eff)

            if jump > 0:
                self.path_streak[asset] = max(1.0, self.path_streak.get(asset, 0.0) + 1.0)
            elif jump < 0:
                self.path_streak[asset] = min(-1.0, self.path_streak.get(asset, 0.0) - 1.0)
            else:
                self.path_streak[asset] = self.path_streak.get(asset, 0.0) * 0.95

        self._prev_bracket[asset] = bracket

        # Track bucket count for warmup
        self._bucket_counts[asset] = self._bucket_counts.get(asset, 0) + 1
        is_warmed_up = self._bucket_counts[asset] >= self.WARMUP_BUCKETS

        # 3. VOLATILITY-NORMALIZED Z-SCORE
        vol_floor = b.vwap * self.VOL_FLOOR_BPS
        std_dev = max(math.sqrt(self.dynamic_var.get(asset, vol_floor)), vol_floor)
        diff = b.vwap - self.dynamic_ref.get(asset, b.vwap)
        z_score = abs(diff) / std_dev if std_dev > 0 else 0.0

        # 4. ASYMMETRIC STRESS PERSISTENCE
        stress_alpha = min(alpha_eff * 3.0, 1.0) if z_score > self.stress_field.get(asset, 0.0) else alpha_eff
        self.stress_field[asset] = self.stress_field.get(asset, 0.0) * (1.0 - stress_alpha) + z_score * stress_alpha

        # 5. DUAL-THRESHOLD HYSTERESIS
        if is_warmed_up:
            if z_score > self.TRIGGER_Z:
                self.is_in_violation[asset] = True
            elif z_score < self.CLEAR_Z:
                self.is_in_violation[asset] = False
        else:
            # During warmup: only clear, never trigger
            if z_score < self.CLEAR_Z:
                self.is_in_violation[asset] = False

        # 6. EMA UPDATE (dampened if stressed)
        if self.is_in_violation.get(asset, False):
            dampened_alpha = alpha_eff * 0.01
            ref = self.dynamic_ref.get(asset, b.vwap)
            self.dynamic_ref[asset] = ref + dampened_alpha * diff
            var = self.dynamic_var.get(asset, (b.vwap * 0.001) ** 2)
            self.dynamic_var[asset] = (1.0 - dampened_alpha) * (var + dampened_alpha * (diff ** 2))
        else:
            ref = self.dynamic_ref.get(asset, b.vwap)
            self.dynamic_ref[asset] = ref + alpha_eff * diff
            var = self.dynamic_var.get(asset, (b.vwap * 0.001) ** 2)
            self.dynamic_var[asset] = (1.0 - alpha_eff) * (var + alpha_eff * (diff ** 2))

        # 7. BATCH PERSISTENCE
        self._batch.append((tick, bracket, jump, self.jump_ema.get(asset, 0.0),
                           self.path_streak.get(asset, 0.0),
                           self.is_in_violation.get(asset, False), 0.0, asset))

        now_mono = time.monotonic()
        if len(self._batch) >= self.BATCH_SIZE or (self._batch and now_mono - self._last_flush >= 0.05):
            batch_copy = self._batch.copy()
            self._batch.clear()
            self._last_flush = now_mono
            asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._persist_batch_thread_safe,
                batch_copy
            )

        return EnrichedTick(
            tick=tick,
            jump=jump,
            jump_ema=self.jump_ema.get(asset, 0.0),
            path_streak=self.path_streak.get(asset, 0.0),
            z_score=z_score,
            is_in_violation=self.is_in_violation.get(asset, False),
            bucket_count=b.tick_count
        )

    def _persist_batch_thread_safe(self, batch_data) -> None:
        if not hasattr(self.tls, 'conn'):
            self.tls.conn = sqlite3.connect(self._db_path, timeout=30.0)
            self.tls.conn.execute("PRAGMA journal_mode=WAL")
            self.tls.conn.execute("PRAGMA busy_timeout=5000")
            self.tls.conn.execute("""
                CREATE TABLE IF NOT EXISTS quantum_log (
                    sequence_id INTEGER PRIMARY KEY,
                    timestamp_ms INTEGER,
                    price REAL,
                    volume REAL,
                    asset TEXT,
                    bracket INTEGER,
                    jump INTEGER,
                    jump_ema REAL,
                    path_streak REAL,
                    z_violation INTEGER,
                    latency_ms REAL
                )
            """)

        rows = [
            (b[0].sequence_id, b[0].timestamp_ms, b[0].price, b[0].volume, b[7], b[1], b[2], b[3], b[4], int(b[5]), b[6])
            for b in batch_data
        ]
        self.tls.conn.executemany(
            "INSERT OR REPLACE INTO quantum_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows
        )
        self.tls.conn.commit()

    def p99_latency(self) -> float:
        if not self._latency_history:
            return 0.0
        sorted_lat = sorted(self._latency_history)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def p99_9_latency(self) -> float:
        if not self._latency_history:
            return 0.0
        sorted_lat = sorted(self._latency_history)
        idx = int(len(sorted_lat) * 0.999)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    def stats(self) -> Dict[str, Any]:
        return {
            "processed": self._processed,
            "z_violations": self._z_violations,
            "last_latency_ms": round(self._last_latency_ms, 3),
            "max_latency_ms": round(self._max_latency_ms, 3),
            "p99_latency_ms": round(self.p99_latency(), 3),
            "p99_9_latency_ms": round(self.p99_9_latency(), 3),
            "latency_samples": len(self._latency_history)
        }


# ── PIPELINE NODE (Macro Time — 7 Layers) ───────────────────────
class PipelineNode:
    """
    Macro time. Processes bucket-level EnrichedTick objects.
    7-layer topology. Preserved class structure.
    """

    MODE_NORMAL = "NORMAL"
    MODE_DEGRADED = "DEGRADED"
    MODE_SURVIVAL = "SURVIVAL"

    def __init__(self, executor: ThreadPoolExecutor, db_path: str, z_event: threading.Event):
        self.executor = executor
        self.z_event = z_event
        self._db_path = db_path
        self._processed = 0
        self._dropped = 0
        self._mode = self.MODE_NORMAL
        self._last_latency_ms = 0.0
        self._conn: Optional[sqlite3.Connection] = None

        self._price_window: deque = deque(maxlen=100)
        self._ema_fast: Optional[float] = None
        self._session_high = 0.0
        self._session_pnl = 0.0
        self._prev_price = 75000.0

    def _init_db(self) -> sqlite3.Connection:
        try:
            conn = _open_sqlite(self._db_path)
        except sqlite3.Error as e:
            print("[FATAL] Cannot open pipeline DB at " + str(self._db_path) + ": " + str(e))
            raise
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_ticks (
                sequence_id INTEGER PRIMARY KEY,
                timestamp_ms INTEGER NOT NULL,
                price REAL NOT NULL,
                volume REAL NOT NULL,
                asset TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_telemetry (
                sequence_id INTEGER PRIMARY KEY,
                timestamp_ms INTEGER,
                asset TEXT,
                regime TEXT,
                signal TEXT,
                mode TEXT,
                executed INTEGER,
                total_latency_ms REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_ms INTEGER,
                asset TEXT,
                event_type TEXT,
                details TEXT
            )
        """)
        conn.commit()
        return conn

    async def consume(self, enriched: EnrichedTick, queue_size: int) -> None:
        start = time.monotonic()
        tick = enriched.tick
        asset = tick.asset
        if self._processed % 50 == 0:
            print(f"[PIPELINE] Processing {asset} | price={tick.price:.2f} | z={enriched.z_score:.2f} | violation={enriched.is_in_violation}")

        # ── Mode Selection ─────────────────────────────────────────
        if queue_size > 3000:
            self._mode = self.MODE_SURVIVAL
        elif queue_size > 1000:
            self._mode = self.MODE_DEGRADED
        else:
            self._mode = self.MODE_NORMAL

        # ── Layer 2: Microstructure ───────────────────────────────
        if self._mode != self.MODE_SURVIVAL:
            direction = "BUY" if tick.price > self._prev_price else "SELL"
            micro_score = tick.volume * (1.0 if direction == "BUY" else -1.0)
        else:
            direction = "UNKNOWN"
            micro_score = 0.0
        self._prev_price = tick.price

        # ── Layer 3: Regime Detection ─────────────────────────────
        self._price_window.append(tick.price)
        if len(self._price_window) >= 10:
            vol = self._realized_vol()
            if vol > 5000.0:
                regime = "CRASH"
            elif vol > 2000.0:
                regime = "VOLATILE"
            else:
                regime = "CALM"
        else:
            regime = "WARMUP"

        # ── Layer 4: Feature Factory ────────────────────────────────
        if self._mode == self.MODE_NORMAL:
            self._ema_fast = self._update_ema(tick.price, 10)
            if len(self._price_window) >= 2:
                momentum = tick.price - self._price_window[0]
            else:
                momentum = 0.0
        else:
            self._ema_fast = tick.price
            momentum = 0.0

        # ── Layer 5: Signal Generator ───────────────────────────────
        if regime == "CRASH" or enriched.is_in_violation:
            signal = "HOLD"
        elif enriched.jump_ema > 5.0:
            signal = "HOLD"
        elif enriched.path_streak > 4.0 and regime == "CALM":
            signal = "BUY"
        elif enriched.path_streak < -4.0 and regime == "CALM":
            signal = "SELL"
        elif momentum > 100.0 and regime == "CALM":
            signal = "BUY"
        elif momentum < -100.0 and regime == "CALM":
            signal = "SELL"
        else:
            signal = "HOLD"

        # ── Layer 6: Risk Gateway ─────────────────────────────────
        executed = False
        if self.z_event.is_set():
            signal = "LOCKOUT"
            self._log_risk("Z_VIOLATION_LOCKOUT",
                           f"Sequencer detected flash crash on {asset} — halting execution")
        elif self._session_high > 0.0 and tick.price < self._session_high * DRAWDOWN_PCT:
            signal = "DRAWDOWN_HALT"
            self._log_risk("DRAWDOWN_LOCKOUT",
                           f"Price {round(tick.price, 2)} below 95% of session high {round(self._session_high, 2)}")
        else:
            if signal in ("BUY", "SELL"):
                executed = True
                self._session_pnl += tick.price * 0.001

        if tick.price > self._session_high:
            self._session_high = tick.price

        # ── Layer 7: Execution ────────────────────────────────────
        total_latency = (time.monotonic() - start) * 1000.0
        await asyncio.get_event_loop().run_in_executor(
            self.executor,
            self._persist_telemetry,
            tick, regime, signal, self._mode, executed, total_latency
        )

        self._processed += 1
        self._last_latency_ms = total_latency

    def _realized_vol(self) -> float:
        if len(self._price_window) < 2:
            return 0.0
        prices = list(self._price_window)
        returns = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
        return (sum(returns) / len(returns)) * 100.0

    def _update_ema(self, price: float, period: int) -> float:
        if self._ema_fast is None:
            return price
        alpha = 2.0 / (period + 1.0)
        return price * alpha + self._ema_fast * (1.0 - alpha)

    def _log_risk(self, event_type: str, details: str) -> None:
        if self._conn is None:
            self._conn = self._init_db()
        ts = int(time.time() * 1000)
        asset = ""
        if " on " in details:
            parts = details.split(" on ")
            if len(parts) > 1:
                asset = parts[1].split(" ")[0]
        self._conn.execute(
            "INSERT INTO risk_events (timestamp_ms, asset, event_type, details) VALUES (?, ?, ?, ?)",
            (ts, asset, event_type, details)
        )
        self._conn.commit()

    def _persist_telemetry(self, tick: Tick, regime: str, signal: str,
                           mode: str, executed: bool, latency: float) -> None:
        try:
            conn = _open_sqlite(self._db_path)
            asset = getattr(tick, 'asset', 'BTCUSDT')
            conn.execute(
                "INSERT OR REPLACE INTO " + MARKET_TICKS_TABLE + " VALUES (?, ?, ?, ?, ?)",
                (tick.sequence_id, tick.timestamp_ms, tick.price, tick.volume, asset)
            )
            conn.execute(
                "INSERT OR REPLACE INTO pipeline_telemetry VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (tick.sequence_id, tick.timestamp_ms, asset, regime, signal, mode,
                 int(executed), latency)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print("[PIPELINE DB ERROR] " + str(e))

    def stats(self) -> Dict[str, Any]:
        return {
            "processed": self._processed,
            "dropped": self._dropped,
            "mode": self._mode,
            "last_latency_ms": round(self._last_latency_ms, 3),
            "session_high": round(self._session_high, 2),
            "session_pnl": round(self._session_pnl, 4)
        }


# ── BROADCASTER ──────────────────────────────────────────────────
class Broadcaster:
    """
    Sequential dual-queue pub/sub with clock-driven bucket flusher.
    Preserved class structure. Added bucket_flusher method.
    """

    def __init__(self, sequencer: SequencerNode, pipeline: PipelineNode):
        self.sequencer = sequencer
        self.pipeline = pipeline
        self.seq_queue: asyncio.Queue = asyncio.Queue(maxsize=SEQ_QUEUE_MAXSIZE)
        self.pipe_queue: asyncio.Queue = asyncio.Queue(maxsize=PIPE_QUEUE_MAXSIZE)
        self._running = False
        self._ticks_received = 0
        self._pipe_drops = 0

    async def produce(self, feed, duration_sec: int) -> None:
        self._running = True
        end_time = time.monotonic() + duration_sec

        while self._running and time.monotonic() < end_time:
            try:
                tick = await feed.recv()
            except Exception as e:
                print("Feed error: " + str(e))
                await asyncio.sleep(0.1)
                continue

            self._ticks_received += 1
            try:
                self.seq_queue.put_nowait(tick)
            except asyncio.QueueFull:
                pass

    async def consume_sequencer(self) -> None:
        while self._running:
            try:
                tick = await asyncio.wait_for(self.seq_queue.get(), timeout=0.1)
                await self.sequencer.consume(tick)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print("Sequencer error: " + str(e))

    async def bucket_flusher(self) -> None:
        """Clock-driven: 245ms heartbeat. Flushes buckets to pipeline."""
        flush_count = 0
        while self._running:
            await asyncio.sleep(BUCKET_INTERVAL_MS / 1000.0)
            try:
                enriched_list = await self.sequencer.flush_all()
                if enriched_list:
                    flush_count += 1
                    if flush_count % 10 == 0:  # Log every ~2.5s
                        assets_flushed = [e.tick.asset for e in enriched_list]
                        print(f"[FLUSH] {len(enriched_list)} buckets flushed: {assets_flushed}")
                for enriched in enriched_list:
                    try:
                        self.pipe_queue.put_nowait(enriched)
                    except asyncio.QueueFull:
                        try:
                            self.pipe_queue.get_nowait()
                            self._pipe_drops += 1
                            self.pipe_queue.put_nowait(enriched)
                        except asyncio.QueueEmpty:
                            pass
            except Exception as e:
                print("Flusher error: " + str(e))

    async def consume_pipeline(self) -> None:
        while self._running:
            try:
                enriched = await asyncio.wait_for(self.pipe_queue.get(), timeout=0.1)
                queue_size = self.pipe_queue.qsize()
                await self.pipeline.consume(enriched, queue_size)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print("Pipeline error: " + str(e))

    async def drain_pipeline(self) -> float:
        drain_start = time.monotonic()
        while self.pipe_queue.qsize() > DRAIN_TARGET_SIZE:
            try:
                enriched = await asyncio.wait_for(self.pipe_queue.get(), timeout=0.1)
                queue_size = self.pipe_queue.qsize()
                await self.pipeline.consume(enriched, queue_size)
            except asyncio.TimeoutError:
                continue
        return time.monotonic() - drain_start

    def stats(self) -> Dict[str, Any]:
        return {
            "ticks_received": self._ticks_received,
            "pipe_drops": self._pipe_drops,
            "seq_queue_size": self.seq_queue.qsize(),
            "pipe_queue_size": self.pipe_queue.qsize(),
            "pipe_drop_rate": round(self._pipe_drops / max(self._ticks_received, 1), 4)
        }


# ── MAIN ─────────────────────────────────────────────────────────
async def main():
    reset_db = "--reset-db" in sys.argv

    print("=" * 75)
    print("RIVER DOCTRINE Delta1.py v4.1")
    print("Time-Bucketed Architecture | BTCUSDT ONLY | Real Feed | 245ms Heartbeat")
    print("=" * 75)
    print("")

    assets = ["btcusdt"]
    asset_labels = ["BTCUSDT"]
    print("MODE: LIVE BINANCE FEED (BTCUSDT Only)")
    print("Assets: " + str(asset_labels))

    if not HAS_WEBSOCKETS:
        print("ERROR: websockets library not installed. Run: python3 -m pip install websockets")
        return

    # Ensure DB directory exists
    for db_path in (SEQ_DB_PATH, PIPE_DB_PATH):
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                print("[DB] Created directory: " + db_dir)
            except OSError as e:
                print("[WARNING] Could not create DB directory " + db_dir + ": " + str(e))

    feed = BinanceFeed("btcusdt")
    try:
        await feed.connect()
    except Exception as e:
        print("Failed to connect to Binance: " + str(e))
        return

    production_duration = 300  # 5 minutes live run

    print("Seq queue maxsize:  " + str(SEQ_QUEUE_MAXSIZE))
    print("Pipe queue maxsize: " + str(PIPE_QUEUE_MAXSIZE))
    print("Bucket interval:    " + str(BUCKET_INTERVAL_MS) + "ms")
    print("Drain target:       " + str(DRAIN_TARGET_SIZE) + " ticks")
    print("Z-violation delta:  $" + str(Z_VIOLATION_DELTA))
    print("Z-cooldown ticks:   " + str(Z_COOLDOWN_TICKS))
    print("Drawdown limit:     " + str(int(DRAWDOWN_PCT * 100)) + "% of session high")
    print("")

    z_violation_event = threading.Event()

    seq_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="seq_")
    pipe_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pipe_")

    if reset_db:
        for p in (SEQ_DB_PATH, PIPE_DB_PATH):
            if os.path.exists(p):
                try:
                    os.remove(p)
                    print("[DB] Removed: " + p)
                except OSError as e:
                    print("[WARNING] Could not remove " + p + ": " + str(e))
        print("DB reset: enabled (--reset-db)")
    else:
        print("DB reset: disabled (preserving existing SQLite state)")
        # Verify DB files are accessible
        for p in (SEQ_DB_PATH, PIPE_DB_PATH):
            try:
                test_conn = sqlite3.connect(p, timeout=1.0)
                test_conn.execute("SELECT 1")
                test_conn.close()
            except sqlite3.Error as e:
                print("[DB WARNING] " + p + " not accessible: " + str(e))

    sequencer = SequencerNode(seq_executor, SEQ_DB_PATH, z_violation_event)
    pipeline = PipelineNode(pipe_executor, PIPE_DB_PATH, z_violation_event)
    broadcaster = Broadcaster(sequencer, pipeline)

    producer = asyncio.create_task(broadcaster.produce(feed, production_duration))
    seq_consumer = asyncio.create_task(broadcaster.consume_sequencer())
    flusher = asyncio.create_task(broadcaster.bucket_flusher())
    pipe_consumer = asyncio.create_task(broadcaster.consume_pipeline())

    start = time.monotonic()
    while time.monotonic() - start < production_duration:
        await asyncio.sleep(1.0)
        elapsed = int(time.monotonic() - start)
        bstats = broadcaster.stats()
        sstats = sequencer.stats()
        pstats = pipeline.stats()

        line = (
            "[T+" + str(elapsed).rjust(3) + "s] "
            "SeqQ: " + str(bstats["seq_queue_size"]).rjust(6) + " | "
            "PipeQ: " + str(bstats["pipe_queue_size"]).rjust(4) + " | "
            "Drop%: " + str(round(bstats["pipe_drop_rate"] * 100.0, 1)).rjust(5) + " | "
            "Seq: " + str(sstats["processed"]).rjust(6) +
            " (p99=" + str(sstats["p99_latency_ms"]).rjust(5) + "ms,p99.9=" +
            str(sstats["p99_9_latency_ms"]).rjust(5) + "ms) | "
            "Pipe: " + str(pstats["mode"]).ljust(10) +
            " (" + str(pstats["last_latency_ms"]).rjust(5) + "ms)"
        )
        print(line)

    print("")
    print("--- DRAIN PHASE: Measuring Time to Recovery ---")
    drain_start_size = broadcaster.pipe_queue.qsize()
    ttr_seconds = await broadcaster.drain_pipeline()

    print("Drain start size: " + str(drain_start_size) + " ticks")
    print("Time to Recovery: " + str(round(ttr_seconds, 2)) + " seconds")
    print("Drain end size:   " + str(broadcaster.pipe_queue.qsize()) + " ticks")
    print("Pipeline mode:    " + pipeline.stats()["mode"])
    print("Z-lockout active: " + str(z_violation_event.is_set()))

    broadcaster._running = False
    await asyncio.gather(producer, seq_consumer, flusher, pipe_consumer, return_exceptions=True)
    seq_executor.shutdown(wait=True)
    pipe_executor.shutdown(wait=True)
    await feed.close()

    print("")
    print("=" * 75)
    print("FINAL REPORT")
    print("=" * 75)
    bstats = broadcaster.stats()
    sstats = sequencer.stats()
    pstats = pipeline.stats()

    print("Ticks received:       " + str(bstats["ticks_received"]))
    print("Pipe drops:           " + str(bstats["pipe_drops"]))
    print("Pipe drop rate:       " + str(round(bstats["pipe_drop_rate"] * 100.0, 2)) + "%")
    print("")
    print("Sequencer processed:   " + str(sstats["processed"]))
    print("Sequencer Z-viols:    " + str(sstats["z_violations"]))
    print("Sequencer p99 latency:   " + str(sstats["p99_latency_ms"]) + "ms")
    print("Sequencer p99.9 latency:  " + str(sstats["p99_9_latency_ms"]) + "ms")
    print("Sequencer max latency:    " + str(sstats["max_latency_ms"]) + "ms")
    print("Latency samples:      " + str(sstats["latency_samples"]))
    print("")
    print("Pipeline processed:    " + str(pstats["processed"]))
    print("Pipeline final mode:   " + pstats["mode"])
    print("Pipeline last latency:  " + str(pstats["last_latency_ms"]) + "ms")
    print("Session high:         " + str(pstats["session_high"]))
    print("Session P&L (mock):   " + str(pstats["session_pnl"]))
    print("Time to Recovery:     " + str(round(ttr_seconds, 2)) + "s")
    print("")

    seq_p99_pass = sstats["p99_latency_ms"] < P99_THRESHOLD_MS
    seq_p99_9_pass = sstats["p99_9_latency_ms"] < P99_9_THRESHOLD_MS
    pipe_degraded = pstats["processed"] < bstats["ticks_received"]
    pipe_recovered = pstats["mode"] == "NORMAL"

    print("Go/No-Go Criteria:")
    print("  Sequencer p99 < " + str(P99_THRESHOLD_MS) + "ms:      " +
          ("PASS (" + str(sstats["p99_latency_ms"]) + "ms)" if seq_p99_pass else "FAIL (" + str(sstats["p99_latency_ms"]) + "ms)"))
    print("  Sequencer p99.9 < " + str(P99_9_THRESHOLD_MS) + "ms:    " +
          ("PASS (" + str(sstats["p99_9_latency_ms"]) + "ms)" if seq_p99_9_pass else "FAIL (" + str(sstats["p99_9_latency_ms"]) + "ms)"))
    print("  Pipeline degraded:               " + ("PASS" if pipe_degraded else "FAIL"))
    print("  Pipeline recovered to NORMAL:    " + ("PASS" if pipe_recovered else "FAIL"))
    print("")

    if seq_p99_pass and seq_p99_9_pass and pipe_degraded and pipe_recovered:
        print("RESULT: PASS — River Doctrine v4 validated. Production ready.")
    elif seq_p99_pass and pipe_degraded:
        print("RESULT: CONDITIONAL PASS — p99 holds, p99.9 or recovery incomplete.")
    else:
        print("RESULT: FAIL — Causality violation detected.")


if __name__ == "__main__":
    asyncio.run(main())
