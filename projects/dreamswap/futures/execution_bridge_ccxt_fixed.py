# =============================================================================
# EXECUTION BRIDGE — CCXT BINANCE FUTURES v4.1
# Standalone. No Fleet Manager imports. Reads pipeline_macro.db only.
# Python 3.14 Compatible | Per-Asset Position Tracking | Time-Bucketed Sync
# BTCUSDT ONLY
# =============================================================================

import sqlite3
import time
import os
import sys
import signal
from typing import Dict, Optional, Tuple, Any

try:
    import ccxt
except ImportError:
    ccxt = None


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPE_DB_PATH = os.environ.get("TRADING_PIPE_DB_PATH") or os.path.join(_SCRIPT_DIR, "pipeline_macro.db")
SQLITE_TIMEOUT_SEC = 30.0
SQLITE_BUSY_TIMEOUT_MS = 5000


def _open_sqlite(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=SQLITE_TIMEOUT_SEC)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=" + str(SQLITE_BUSY_TIMEOUT_MS))
    return conn


class ExecutionBridge:
    """
    Polls pipeline_macro.db for exposure commands and reconciles
    Binance USD-M Futures positions via CCXT.

    SAFETY:
      - testnet=True by default
      - dry_run=True by default
      - Halts if STOP_TRADING file exists in working directory
      - Minimum delta threshold prevents noise trading
      - Signal handlers for graceful shutdown
      - Per-asset position tracking (not global)
    """

    def __init__(
        self,
        db_path: str = PIPE_DB_PATH,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
        dry_run: bool = True,
        min_delta_pct: float = 0.02,
        poll_interval_ms: int = 245,
    ):
        self.db_path = db_path
        self.testnet = testnet
        self.dry_run = dry_run
        self.min_delta_pct = min_delta_pct
        self.poll_interval = poll_interval_ms / 1000.0

        self.last_timestamps: Dict[str, int] = {}
        self.last_targets: Dict[str, float] = {}
        self.running = False
        self.exchange = None

        # Per-asset position tracking
        self._current_positions: Dict[str, Tuple[float, str]] = {}

        if not self.dry_run:
            if ccxt is None:
                print("[FATAL] CCXT not installed. Run: python3 -m pip install ccxt")
                sys.exit(1)
            self.exchange = ccxt.binance(
                {
                    "apiKey": api_key,
                    "secret": api_secret,
                    "enableRateLimit": True,
                    "options": {
                        "defaultType": "future",
                        "adjustForTimeDifference": True,
                    },
                }
            )
            if testnet:
                self.exchange.set_sandbox_mode(True)

        self._init_db()
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        print("\n[SHUTDOWN] Signal " + str(signum) + " received. Stopping bridge...")
        self.running = False

    def _init_db(self) -> None:
        conn = _open_sqlite(self.db_path)
        c = conn.cursor()
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
            "CREATE TABLE IF NOT EXISTS executions ("
            + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            + "asset TEXT NOT NULL, "
            + "target_exposure REAL NOT NULL, "
            + "current_exposure REAL NOT NULL, "
            + "delta_contracts REAL NOT NULL, "
            + "order_id TEXT, "
            + "status TEXT, "
            + "timestamp_ms INTEGER NOT NULL"
            + ")"
        )
        conn.commit()
        conn.close()

    def _conn(self):
        return _open_sqlite(self.db_path)

    def _check_stop_file(self) -> bool:
        return os.path.exists("STOP_TRADING")

    def _ccxt_symbol(self, asset: str) -> str:
        # Normalize: strip double USDT if present
        asset = asset.upper().replace("USDTUSDT", "USDT")
        if asset.endswith("USDT"):
            base = asset[:-4]
            return base + "/USDT:USDT"
        return asset

    def _get_latest_command(self, asset: str) -> Optional[Dict[str, Any]]:
        conn = self._conn()
        c = conn.cursor()
        last_ms = self.last_timestamps.get(asset, 0)
        c.execute(
            "SELECT target_exposure, timestamp_ms FROM exposure_commands "
            + "WHERE asset = ? AND timestamp_ms > ? "
            + "ORDER BY timestamp_ms DESC LIMIT 1",
            (asset, last_ms),
        )
        row = c.fetchone()
        conn.close()
        if row:
            self.last_timestamps[asset] = row[1]
            return {"target_exposure": float(row[0]), "timestamp_ms": row[1]}
        return None

    def _get_wallet_balance_usdt(self) -> float:
        if self.dry_run or self.exchange is None:
            return 100000.0
        balance = self.exchange.fetch_balance()
        return float(balance.get("USDT", {}).get("free", 0.0))

    def _get_position(self, symbol: str, asset: str) -> Tuple[float, str]:
        if self.dry_run or self.exchange is None:
            cached = self._current_positions.get(asset, (0.0, "none"))
            return cached
        try:
            positions = self.exchange.fetch_positions([symbol])
            for pos in positions:
                sym = pos.get("symbol", pos.get("future", ""))
                if sym == symbol:
                    contracts = float(pos.get("contracts", 0.0))
                    side = pos.get("side", "none")
                    if contracts == 0 or side is None:
                        return 0.0, "none"
                    return contracts, side
            return 0.0, "none"
        except Exception as e:
            print("[ERROR] Failed to fetch position for " + symbol + ": " + str(e))
            return 0.0, "none"

    def _get_mark_price(self, symbol: str) -> float:
        if self.dry_run or self.exchange is None:
            return 0.0
        ticker = self.exchange.fetch_ticker(symbol)
        return float(ticker.get("last", 0.0))

    def _calculate_target_contracts(
        self, symbol: str, target_exposure: float, balance_usdt: float
    ) -> float:
        if self.dry_run or self.exchange is None:
            mark_price = 77000.0
            if "ETH" in symbol:
                mark_price = 3800.0
            elif "SOL" in symbol:
                mark_price = 150.0
            if mark_price == 0:
                return 0.0
            target_notional = balance_usdt * target_exposure
            return target_notional / mark_price
        market = self.exchange.market(symbol)
        contract_size = float(market.get("contractSize", 1.0))
        mark_price = self._get_mark_price(symbol)
        if mark_price == 0:
            return 0.0
        target_notional = balance_usdt * target_exposure
        target_contracts = target_notional / (mark_price * contract_size)
        return target_contracts

    def _place_order(self, symbol: str, delta: float) -> Optional[str]:
        if abs(delta) < 1e-9:
            return None

        side = "buy" if delta > 0 else "sell"
        amount = abs(delta)

        if self.dry_run or self.exchange is None:
            print(
                "[DRY_RUN] Would place "
                + side.upper()
                + " order: "
                + str(round(amount, 4))
                + " contracts on "
                + symbol
            )
            return "DRY_RUN"

        market = self.exchange.market(symbol)
        amount = float(self.exchange.amount_to_precision(symbol, amount))

        min_amount = float(market["limits"]["amount"]["min"])
        if amount < min_amount:
            print(
                "[SKIP] Order amount " + str(amount) + " below minimum " + str(min_amount)
            )
            return None

        try:
            order = self.exchange.create_order(
                symbol=symbol, type="market", side=side, amount=amount
            )
            order_id = order.get("id", "unknown")
            print(
                "[EXECUTED] "
                + side.upper()
                + " "
                + str(amount)
                + " contracts on "
                + symbol
                + " | Order ID: "
                + order_id
            )
            return order_id
        except Exception as e:
            print("[FATAL] Order failed on " + symbol + ": " + str(e))
            return None

    def _log_execution(
        self,
        asset: str,
        target: float,
        current: float,
        delta: float,
        order_id: Optional[str],
        status: str,
    ) -> None:
        conn = self._conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO executions "
            + "(asset, target_exposure, current_exposure, delta_contracts, order_id, status, timestamp_ms) "
            + "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                asset,
                target,
                current,
                delta,
                order_id,
                status,
                int(time.time() * 1000),
            ),
        )
        conn.commit()
        conn.close()

    def reconcile(self, asset: str) -> None:
        if self._check_stop_file():
            print("[STOP] Stop file detected. Halting execution for " + asset)
            return

        command = self._get_latest_command(asset)
        if not command:
            return

        target_exposure = command["target_exposure"]

        last_target = self.last_targets.get(asset)
        if last_target is not None and abs(target_exposure - last_target) < 1e-9:
            return
        self.last_targets[asset] = target_exposure

        symbol = self._ccxt_symbol(asset)

        balance = self._get_wallet_balance_usdt()
        if balance <= 0:
            print("[WARNING] Zero USDT balance. Skipping " + asset)
            return

        current_contracts, current_side = self._get_position(symbol, asset)
        mark_price = self._get_mark_price(symbol)

        if self.dry_run or self.exchange is None:
            current_exposure = 0.0
            target_contracts = self._calculate_target_contracts(symbol, target_exposure, balance)
            delta = target_contracts - current_contracts

            exposure_diff = abs(target_exposure - current_exposure)
            contract_delta_pct = abs(delta) / max(abs(target_contracts), 1e-9)
            if exposure_diff < self.min_delta_pct and contract_delta_pct < self.min_delta_pct:
                return

            print(
                "[RECONCILE] "
                + asset
                + " | Target: "
                + str(round(target_exposure, 4))
                + " | Current: "
                + str(round(current_exposure, 4))
                + " | Delta: "
                + str(round(delta, 4))
                + " contracts"
            )

            order_id = self._place_order(symbol, delta)
            status = "EXECUTED" if order_id else "FAILED"
            if self.dry_run and order_id == "DRY_RUN":
                status = "DRY_RUN"

            # Update cached position for dry_run
            new_contracts = current_contracts + delta
            new_side = "long" if new_contracts > 0 else ("short" if new_contracts < 0 else "none")
            self._current_positions[asset] = (new_contracts, new_side)

            self._log_execution(asset, target_exposure, current_exposure, delta, order_id, status)
            return

        # Live trading path (only reached when not dry_run)
        market = self.exchange.market(symbol)
        contract_size = float(market.get("contractSize", 1.0))

        current_notional = current_contracts * mark_price * contract_size
        current_exposure = 0.0
        if balance > 0:
            current_exposure = current_notional / balance
        if current_side == "short":
            current_exposure = -abs(current_exposure)

        target_contracts = self._calculate_target_contracts(
            symbol, target_exposure, balance
        )
        delta = target_contracts - current_contracts

        exposure_diff = abs(target_exposure - current_exposure)
        contract_delta_pct = abs(delta) / max(abs(target_contracts), 1e-9)
        if exposure_diff < self.min_delta_pct and contract_delta_pct < self.min_delta_pct:
            return

        print(
            "[RECONCILE] "
            + asset
            + " | Target: "
            + str(round(target_exposure, 4))
            + " | Current: "
            + str(round(current_exposure, 4))
            + " | Delta: "
            + str(round(delta, 4))
            + " contracts"
        )

        order_id = self._place_order(symbol, delta)
        status = "EXECUTED" if order_id else "FAILED"
        if self.dry_run and order_id == "DRY_RUN":
            status = "DRY_RUN"

        self._log_execution(asset, target_exposure, current_exposure, delta, order_id, status)

    def run(self, assets: list) -> None:
        self.running = True
        print("=== EXECUTION BRIDGE STARTED ===")
        print("Mode: " + ("TESTNET" if self.testnet else "LIVE"))
        print("Dry Run: " + str(self.dry_run))
        print("DB Path: " + self.db_path)
        print("Assets: " + str(assets))
        print("Poll Interval: " + str(self.poll_interval * 1000) + "ms")
        print("Safety: Create STOP_TRADING file to halt immediately")

        while self.running:
            if self._check_stop_file():
                print("[STOP] STOP_TRADING file detected. Shutting down.")
                self.running = False
                break

            for asset in assets:
                try:
                    self.reconcile(asset)
                except Exception as e:
                    print("[ERROR] Reconcile failed for " + asset + ": " + str(e))

            time.sleep(self.poll_interval)

        print("=== EXECUTION BRIDGE STOPPED ===")


if __name__ == "__main__":
    # BTCUSDT ONLY
    assets = ["BTCUSDT"]

    bridge = ExecutionBridge(
        db_path=PIPE_DB_PATH,
        api_key="YOUR_API_KEY_HERE",
        api_secret="YOUR_API_SECRET_HERE",
        testnet=True,
        dry_run=True,
        poll_interval_ms=245,
    )
    bridge.run(assets=assets)
