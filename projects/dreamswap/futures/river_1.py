#!/usr/bin/env python3
# =============================================================================
# RIVER DOCTRINE ORCHESTRATOR v2.1 (CONCURRENT EDITION)
# True real-time parallel execution via subprocess.Popen
# BTCUSDT ONLY | WebSocket Direct
# =============================================================================

import subprocess
import sys
import os
import time
import signal
import sqlite3
import argparse
from pathlib import Path
from typing import List

# ── CONFIGURATION ────────────────────────────────────────────────────────────
DEFAULT_DB_PATH = os.environ.get("TRADING_PIPE_DB_PATH", "pipeline_macro.db")
DEFAULT_SEQ_DB = os.environ.get("TRADING_SEQ_DB_PATH", "sequencer_quantum.db")
DEFAULT_ASSETS = "BTCUSDT"
DEFAULT_DURATION_SEC = 30

# Script paths — auto-detect from orchestrator location
SCRIPT_DIR = Path(__file__).parent.resolve()
DELTA1_SCRIPT = os.environ.get("DELTA1_PATH", str(SCRIPT_DIR / "Delta1.py"))
FLEET_SCRIPT = os.environ.get("FLEET_PATH", str(SCRIPT_DIR / "fleet_manager_dopamine_v3.py"))
BRIDGE_SCRIPT = os.environ.get("BRIDGE_PATH", str(SCRIPT_DIR / "execution_bridge_ccxt_fixed.py"))

PYTHON_EXE = sys.executable

class RiverOrchestrator:
    def __init__(self, db_path=DEFAULT_DB_PATH, seq_db=DEFAULT_SEQ_DB, assets=DEFAULT_ASSETS, 
                 duration_sec=DEFAULT_DURATION_SEC, feed_mode="live_ws", cleanup=True):
        self.db_path = str(Path(db_path).resolve())
        self.seq_db = str(Path(seq_db).resolve())
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.seq_db).parent.mkdir(parents=True, exist_ok=True)
        self.assets = assets
        self.duration_sec = duration_sec
        self.feed_mode = feed_mode
        self.cleanup = cleanup
        self.processes: List[subprocess.Popen] = []
        self.running = False

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print(f"\n[ORCHESTRATOR] Signal {signum} received. Initiating graceful shutdown...")
        self.running = False

    def _clean_databases(self):
        print("[ORCHESTRATOR] Purging old state...")
        for db in [self.db_path, self.seq_db]:
            for suffix in ["", "-wal", "-shm", "-journal"]:
                path = db + suffix
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

    def _wait_for_db_init(self, timeout_sec: int = 10) -> bool:
        """Waits for Delta1 to create the sequencer DB before starting Fleet.

        Delta1 writes to seq_db immediately. The pipeline DB (db_path) only
        exists after the first bucket flush (~245ms), so we check seq_db.
        """
        start = time.time()
        while time.time() - start < timeout_sec:
            try:
                # Check sequencer DB (created by Delta1.py immediately)
                conn = sqlite3.connect(self.seq_db)
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM quantum_log")
                count = c.fetchone()[0]
                conn.close()
                if count >= 1:
                    return True
            except (sqlite3.OperationalError, sqlite3.DatabaseError):
                pass
            time.sleep(0.25)
        return False

    def run(self):
        print("=" * 70)
        print("RIVER DOCTRINE ORCHESTRATOR v2.1 (CONCURRENT | BTCUSDT ONLY)")
        print("=" * 70)

        if self.cleanup:
            self._clean_databases()
            time.sleep(0.5)  # Allow filesystem to settle after deletion

        env = os.environ.copy()
        env["TRADING_PIPE_DB_PATH"] = self.db_path
        env["TRADING_SEQ_DB_PATH"] = self.seq_db
        env["FLEET_ASSETS"] = self.assets
        env["BRIDGE_ASSETS"] = self.assets

        self.running = True

        try:
            # 1. BOOT DELTA 1
            print("\n[BOOT] Starting Delta1 Sequencer...")
            cmd_delta = [PYTHON_EXE, DELTA1_SCRIPT]
            # Delta1 is hardcoded to BTCUSDT WebSocket in v4.1

            proc_delta = subprocess.Popen(cmd_delta, env=env, cwd=str(SCRIPT_DIR))
            self.processes.append(proc_delta)

            # Wait for data pipe to get hot
            if not self._wait_for_db_init():
                print("[FATAL] Delta1 failed to initialize the database. Aborting.")
                return 1
            print("[BOOT] SQLite WAL is hot. Market data flowing.")

            # 2. BOOT FLEET MANAGER
            print("[BOOT] Starting Fleet Manager (Fusion Layer)...")
            cmd_fleet = [PYTHON_EXE, FLEET_SCRIPT]
            if self.feed_mode == "live_ws":
                cmd_fleet.append("--live-ws")
            elif self.feed_mode == "mock":
                cmd_fleet.append("--mock")

            proc_fleet = subprocess.Popen(cmd_fleet, env=env, cwd=str(SCRIPT_DIR))
            self.processes.append(proc_fleet)
            time.sleep(1) # Brief pause so Fleet can calibrate before Bridge wakes up

            # 3. BOOT EXECUTION BRIDGE
            print("[BOOT] Starting Execution Bridge (CCXT)...")
            proc_bridge = subprocess.Popen([PYTHON_EXE, BRIDGE_SCRIPT], env=env, cwd=str(SCRIPT_DIR))
            self.processes.append(proc_bridge)

            # 4. MONITOR RUNTIME
            print(f"\n[ORCHESTRATOR] All systems go. Running live concurrency for {self.duration_sec} seconds...\n")
            start_time = time.time()
            while self.running and (time.time() - start_time) < self.duration_sec:
                time.sleep(1)

                # Health check - if any process died early, kill all
                if any(p.poll() is not None for p in self.processes):
                    print("\n[WARN] A subsystem terminated unexpectedly. Shutting down...")
                    break

        except KeyboardInterrupt:
            print("\n[ORCHESTRATOR] Manual interrupt caught.")
        finally:
            self._shutdown_and_report()

        return 0

    def _shutdown_and_report(self):
        print("\n[SHUTDOWN] Sending SIGTERM to all subsystems...")
        for proc in self.processes:
            if proc.poll() is None:
                proc.terminate()

        # Give them 3 seconds to close SQLite connections gracefully without corrupting WAL
        time.sleep(3)
        for proc in self.processes:
            if proc.poll() is None:
                proc.kill()

        self._print_final_report()

    def _print_final_report(self):
        print("\n" + "=" * 70)
        print("FINAL REPORT (CONCURRENT RUN)")
        print("=" * 70)

        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            for table in ["market_ticks", "pipeline_telemetry", "exposure_commands", "executions", "position_ledger"]:
                try:
                    c.execute(f"SELECT COUNT(*) FROM {table}")
                    print(f"  {table:<25} {c.fetchone()[0]:>6} rows")
                except:
                    pass

            try:
                c.execute("SELECT SUM(realized_pnl_usdt), SUM(entry_notional_usdt), COUNT(*) FROM position_ledger WHERE status = 'closed'")
                pnl, notional, closed = c.fetchone()
                print("\n  PnL SUMMARY")
                print(f"  Closed trades:      {closed or 0:>12}")
                print(f"  Total realized PnL: ${(pnl or 0):>+12,.2f} USDT")
            except:
                pass
            conn.close()
        except Exception as e:
            print(f"[WARN] Could not generate final report: {e}")
        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", default=False, help="Use high-frequency mock feed")
    parser.add_argument("--live-db", action="store_true", default=False, help="Use live Binance feed via Delta1->DB->Fleet")
    parser.add_argument("--live-ws", action="store_true", default=False, help="Use live Binance WebSocket directly in Fleet Manager (bypasses DB)")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION_SEC, help="Run duration in seconds")
    parser.add_argument("--assets", type=str, default=DEFAULT_ASSETS, help="Comma-separated assets")
    parser.add_argument("--db", type=str, default=DEFAULT_DB_PATH, help="Pipeline DB path")
    parser.add_argument("--no-cleanup", action="store_true", help="Do not purge databases on start")

    args = parser.parse_args()

    # Determine feed mode
    if args.mock:
        feed_mode = "mock"
    elif args.live_db:
        feed_mode = "live_db"
    else:
        feed_mode = "live_ws"  # Default to direct WebSocket

    orch = RiverOrchestrator(
        db_path=args.db,
        assets=args.assets,
        duration_sec=args.duration,
        feed_mode=feed_mode,
        cleanup=not args.no_cleanup,
    )
    sys.exit(orch.run())
