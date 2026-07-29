# DREAMSWAP vNext — Architectural Map

> **Status:** OPERATIONAL — All 317 tests passing across 8 phases
> **Purpose:** Market research system. Not a trading bot.
> **Core Question:** *"Does a measurable market phenomenon exist that produces predictive lift?"*

---

## 1. Core Principles

| Principle | Meaning |
|-----------|---------|
| **Evidence > Prediction** | Raw data outlives conclusions. Every observation is preserved. |
| **Lift > Profit** | P(continuation \| H1) / P(continuation \| ¬H1) is the only metric that matters |
| **Baseline > Assumption** | Null observations (every 5 min) provide the denominator for lift |
| **Regime > Global Average** | All observations tagged with market regime at origin time |
| **Boolean > Fuzzy** | Every hypothesis condition is a boolean with an explicit threshold |
| **Immutable > Mutable** | All state snapshots are frozen dataclasses. Once recorded, never changed. |
| **Append-Only > Delete** | Journal never deletes. Compress old data, do not remove. |
| **Earned Complexity > Assumed Complexity** | H2 is only generated after H1 survives. No shortcuts. |

---

## 2. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DREAMSWAP vNext                             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  FEED LAYER (Phase 1)                        │   │
│  │  feed/client.py ──► feed/normalizer.py ──► feed/simulated.py│   │
│  │  Raw WebSocket / Simulated ingestion. Zero business logic.   │   │
│  │  Output: MarketEvent (BOOK_UPDATE | TRADE)                   │   │
│  └──────────────────────┬───────────────────────────────────────┘   │
│                         │                                           │
│                         ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 STATE LAYER (Phase 2)                        │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │   │
│  │  │ book.py  │ │ flow.py  │ │liquidity │ │ regime.py│       │   │
│  │  │ Top-5    │ │1m/15m    │ │.py       │ │ ADX/ATR  │       │   │
│  │  │ bid/ask  │ │counts    │ │Persistence│ │classify  │       │   │
│  │  └────┬─────┘ └────┬─────┘ └─────┬────┘ └────┬─────┘       │   │
│  │       └────────────┴─────────────┴───────────┘              │   │
│  │                          │                                   │   │
│  │                    ┌─────┴──────┐                            │   │
│  │                    │ baseline.py│←── Timer (5 min)           │   │
│  │                    └─────┬──────┘                            │   │
│  └──────────────────────────┼───────────────────────────────────┘   │
│                             │                                       │
│                             ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              HYPOTHESIS LAYER (Phase 3)                     │   │
│  │  hypothesis/h1.py                                           │   │
│  │    4 boolean conditions (persistence, acceleration,          │   │
│  │    cancellation, bias) → HypothesisSignal or None           │   │
│  └──────────────────────┬───────────────────────────────────────┘   │
│                         │                                           │
│                         ▼                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                EVIDENCE LAYER (Phase 4)                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐                │   │
│  │  │ observation.py   │───►│ tracker.py       │                │   │
│  │  │ EvidencePacket   │    │ 20-min outcome   │                │   │
│  │  │ creation         │    │ tracking         │                │   │
│  │  └──────────────────┘    └────────┬─────────┘                │   │
│  └───────────────────────────────────┼──────────────────────────┘   │
│                                      │                               │
│                                      ▼                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │               ANALYTICS LAYER (Phase 5)                      │   │
│  │  ┌────────────────┐    ┌──────────────────┐                  │   │
│  │  │ statistics.py  │───►│ research.py      │                  │   │
│  │  │ MathEngine:    │    │ HypothesisLife-  │                  │   │
│  │  │ lift, CI,      │    │ cycle: evaluate, │                  │   │
│  │  │ Bayes, sample  │    │ promote, retire, │                  │   │
│  │  │ size           │    │ weekly report    │                  │   │
│  │  └────────────────┘    └────────┬─────────┘                  │   │
│  └───────────────────────────────────┼──────────────────────────┘   │
│                                      │                               │
│                                      ▼                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                EDGE LAYER (Phase 6)                          │   │
│  │  ┌────────────────┐    ┌──────────────────┐                  │   │
│  │  │ scheduler.py   │    │ ledger.py        │                  │   │
│  │  │ H1 cooldown,   │    │ EdgeLedger:      │                  │   │
│  │  │ baseline timer │    │ weight, alloc,   │                  │   │
│  │  │                │    │ slippage regulate│                  │   │
│  │  └────────────────┘    └──────────────────┘                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                      │                               │
│                                      ▼                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │             PERSISTENCE LAYER (Phase 7)                      │   │
│  │  ┌────────────────┐    ┌──────────────────┐                  │   │
│  │  │ journal.py     │    │ db.py            │                  │   │
│  │  │ Append-only    │    │ SQLite WAL       │                  │   │
│  │  │ JSON Lines     │    │ 11 tables + CRUD │                  │   │
│  │  │ Auto-rotation  │    │ Thread-safe      │                  │   │
│  │  └────────────────┘    └──────────────────┘                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                      │                               │
│                                      ▼                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │               ORCHESTRATOR (Phase 8)                         │   │
│  │  main.py — DreamswapOrchestrator                             │   │
│  │  Wires all layers: Feed → State → H1 → Evidence → Analytics │   │
│  │  → Edge → Persistence. Error isolation per step.             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Directory Structure

```
Trading Bot/
│
├── ARCHITECTURAL_MAP.md              ← THIS FILE
│
├── core/                              ← Foundation data types & interfaces
│   ├── __init__.py
│   ├── types.py                       ← All frozen dataclasses, enums
│   ├── protocol.py                    ← StateModule, HypothesisEvaluator protocols
│   └── errors.py                      ← Exception hierarchy
│
├── feed/                              ← Phase 1: Raw data ingestion
│   ├── __init__.py
│   ├── client.py                      ← FeedClient abstract base
│   ├── simulated.py                   ← SimulatedFeedClient for testing
│   └── normalizer.py                  ← Binance message → MarketEvent
│
├── state/                             ← Phase 2: Market state modules
│   ├── __init__.py
│   ├── book.py                        ← Top-5 order book
│   ├── flow.py                        ← Participation dynamics
│   ├── liquidity.py                   ← Liquidity quality metrics
│   ├── regime.py                      ← Market regime classification
│   └── baseline.py                    ← Null observation sampler
│
├── hypothesis/                        ← Phase 3: Hypothesis evaluation
│   ├── __init__.py
│   └── h1.py                          ← H1 boolean condition evaluator
│
├── evidence/                          ← Phase 4: Observation & tracking
│   ├── __init__.py
│   ├── observation.py                 ← EvidencePacket factory
│   ├── tracker.py                     ← 20-min outcome tracker
│   ├── statistics.py                  ← MathEngine (lift, CI, Bayes)
│   └── research.py                    ← Hypothesis lifecycle
│
├── edge/                              ← Phase 6: Edge allocation
│   ├── __init__.py
│   ├── scheduler.py                   ← H1 cooldown, baseline timer
│   └── ledger.py                      ← Weight computation, allocation
│
├── persistence/                       ← Phase 7: Storage
│   ├── __init__.py
│   ├── journal.py                     ← Append-only JSON Lines journal
│   └── db.py                          ← SQLite WAL with 11 tables
│
├── main.py                            ← Phase 8: System orchestrator
│
└── tests/                             ← 317 tests across all phases
    ├── test_*.py                      ← 18 test files
    ├── test_integration_*.py          ← Integration tests
    └── __init__.py
```

---

## 4. Data Flow — End to End

### 4.1 H1 Observation Flow

```
Exchange / Simulated Feed
    │
    ▼ MarketEvent(event_type, timestamp, payload)
feed/client.py + feed/normalizer.py
    │
    ├──► BOOK_UPDATE ──► book.py (update top-5 levels)
    │                   └──► liquidity.py (record_book_snapshot)
    │                   └──► regime.py (update_from_book_state)
    │
    └──► TRADE ──► flow.py (update rolling counters)
    │
    ▼
StateBundle(book, flow, liquidity, regime)
    │
    ▼
h1.py — evaluate()                          ◄── Scheduler: should_evaluate_h1()
    │
    ├── persistence=False? ──► NO SIGNAL (continue)
    │
    └── PERSISTENCE=True
        + ACCELERATION=True
        + CANCELLATION=True
        + BIAS=LONG/SHORT
            │
            ▼ HypothesisSignal
        observation.py — create()
            │
            ▼ EvidencePacket (complete frozen snapshot)
        tracker.py — start_tracking()
            │
            ├──► journal.py — append(OBSERVATION)
            └──► db.py — save_observation()
            │
            ▼ (20 minutes of price updates)
        tracker.py — on_price_update() ──► OutcomeResult
            │
            ├──► lifecyle.py — record_observation()
            ├──► lifecyle.py — evaluate()        ◄── Called periodically
            ├──► lifecyle.py — check_survival()
            ├──► lifecyle.py — promote_to_edge()  ◄── If all 5 criteria met
            │       └──► ledger.py — register_edge()
            │       └──► journal.py — append(EDGE_PROMOTION)
            │
            ├──► journal.py — append(OUTCOME)
            └──► db.py — save_outcome()
```

### 4.2 Baseline Flow (Parallel)

```
Timer (every 5 minutes) → Scheduler: should_sample_baseline()
    │
    ▼
baseline.py — create_sample(StateBundle)
    │
    ▼ BaselineObservation(is_baseline=True)
observation.py — create_baseline()
    │
    ▼ EvidencePacket(is_baseline=True)
tracker.py — start_tracking()   ──── Identical tracking to H1
    │
    └──► 20 min later → OutcomeResult
         └──► lifecycle.py — record_observation()
              └──► statistics.py — lift(H1_rate / baseline_rate)
```

---

## 5. Core Data Types

### 5.1 Market Events (feed layer)

| Type | Fields | Validation |
|------|--------|-----------|
| `MarketEvent` | event_id, event_type (BOOK_UPDATE\|TRADE), timestamp, payload | timestamp > 0 |
| `BookUpdate` | side (BID\|ASK), price, volume, level (1-5) | price > 0, volume ≥ 0, level 1-5 |
| `TradeEvent` | price, volume, side (BUY\|SELL), aggressive | price > 0, volume > 0 |

### 5.2 State Snapshots (state layer)

| Snapshot | Key Fields | Purpose |
|----------|-----------|---------|
| `BookState` | bids: tuple[BookLevel], asks, spread, imbalance, mid | Top-5 order book |
| `FlowState` | trade_count_1m, acceleration_ratio, aggressive_volume_1m | Participation dynamics |
| `LiquidityState` | metrics: LiquidityMetrics(persistence_score, cancellation_ratio, depth_stability, trust_score) | Liquidity quality |
| `RegimeState` | primary_regime (TRENDING_UP/DOWN/RANGING/HIGH_VOL/LOW_VOL), volatility_regime, atr_14, atr_50_avg | Market classification |

### 5.3 Hypothesis & Evidence (hypothesis + evidence layers)

| Type | Key Fields | Mutability |
|------|-----------|------------|
| `ConditionsSnapshot` | persistence, acceleration, cancellation, bias | Frozen. Boolean only. |
| `HypothesisSignal` | hypothesis_id, direction, origin_price, conditions_met | Frozen. Output of H1. |
| `EvidencePacket` | observation_id, timestamp, origin_price, direction, all state snapshots, atr_14, spread, conditions_snapshot | **Frozen. The most valuable object in the system.** |
| `OutcomeResult` | observation_id, tier1/2/3_reached, invalidated, max_favorable_distance, time_to_result | Frozen. 20-min tracking result. |
| `HypothesisRecord` | hypothesis_id, version, status, observation_count, predictive_lift, confidence_interval, regime_performance | Frozen. Current lifecycle state. |

### 5.4 Analytics & Edge (analytics + edge layers)

| Type | Key Fields | Purpose |
|------|-----------|---------|
| `StatisticalReport` | lift, confidence_interval, bayesian_posterior, sample_size_adequate, regime_breakdown | MathEngine output |
| `SurvivalCriteria` | min_observations=500, min_lift=1.25, confidence=0.95, min_regimes=3, stability_tolerance=0.15 | Immutable thresholds |
| `EdgeRecord` | hypothesis_id, predictive_lift, confidence_lower/upper, regime_performance | Promoted hypothesis |
| `AllocationInstruction` | hypothesis_id, weight, allocated_size, expected_slippage, sufficient_liquidity | Edge ledger output |
| `SchedulerState` | last_h1_evaluation_ms, last_baseline_sample_ms, is_in_cooldown, ms_until_next_baseline | Scheduler snapshot |

### 5.5 Persistence (persistence layer)

| Type | Key Fields | Integrity |
|------|-----------|-----------|
| `JournalEntry` | entry_id (UUID), entry_type, timestamp, data (dict), created_at | Append-only. Once written, never changed. |
| `JournalEntryType` | OBSERVATION, OUTCOME, HYPOTHESIS_CHANGE, REGIME, FALSE_SIGNAL, MISSED_OPPORTUNITY, SYSTEM_EVENT, H1_EVALUATION, EDGE_PROMOTION, ALLOCATION | 10 entry types |

---

## 6. Module Responsibilities — Deep Dive

### 6.1 feed/client.py — Abstract Feed Client

```
Abstract base class. Contract:
  - connect(endpoint) → None
  - disconnect() → None
  - subscribe(channels) → None
  - on_message(callback) → None         # Register MarketEvent handler
  - is_healthy() → bool                 # ≤5s since last event
```

**Design Rule:** If feed.py contains a conditional, it is wrong. Its only job: receive → normalize → emit.

### 6.2 state/book.py — Top-5 Order Book

```
Internal: dict[int, BookLevel] keyed by level index (0-4)
  - update(event) → processes BOOK_UPDATE events
  - snapshot() → BookState with sorted top-5 bids/asks, spread, imbalance, mid
  - reset() → clears all levels
```

**Why top-5?** H1 only needs visible liquidity. Full book = noise. (ADR-005)

### 6.3 state/flow.py — Participation Dynamics

```
Internal: deque[(timestamp, volume, aggressive)] for 1m and 15m windows
  - update(event) → processes TRADE events
  - snapshot() → FlowState with counts, volume, acceleration_ratio
  - Baseline recalculated every 60 seconds
```

**Acceleration Ratio:** 1-min rate / 15-min per-minute rate. >1.8 triggers H1 condition.

### 6.4 state/liquidity.py — Liquidity Quality

```
Internal: depth_samples deque, cancelled/executed volume counters
  - record_book_snapshot(book_state) → depth sample at current time
  - snapshot() → LiquidityState with persistence, cancellation, stability, trust_score
  - trust_score = 1.0 if ALL thresholds met, else weighted average
```

**Trust Score Formula:**
```
IF persistence >= 0.85 AND cancellation < 0.7 AND stability < 0.3:
    trust_score = 1.0
ELSE:
    trust_score = p_norm * 0.4 + c_norm * 0.3 + s_norm * 0.3
```

### 6.5 state/regime.py — Market Regime Classification

```
Internal: price history deque, true ranges for ATR, exponential moving average
  - update_from_book_state(book_state) → record mid price
  - snapshot() → RegimeState with classification + ATR values
```

**Detection Logic:**
| Regime | Trigger |
|--------|---------|
| HIGH_VOL | ATR(14) ≥ 2x ATR(50 avg) |
| LOW_VOL | ATR(14) ≤ 0.5x ATR(50 avg) |
| TRENDING_UP | Trend strength ≥ 25, EMA slope > 0 |
| TRENDING_DOWN | Trend strength ≥ 25, EMA slope < 0 |
| RANGING | Default if no other regime matches |

### 6.6 state/baseline.py — Null Observation Sampler

```
Timer-driven (default: 5 min)
  - should_sample(now) → bool
  - create_sample(state_bundle) → BaselineObservation(is_baseline=True)
```

**Why baselines?** Lift requires P(continuation | ¬H1). Without baselines, we can't measure it. (ADR-008)

### 6.7 hypothesis/h1.py — H1 Boolean Evaluator

```
Thresholds (explicit, immutable):
  PERSISTENCE   ≥ 0.85  (liquidity_state.metrics.persistence_score)
  ACCELERATION  > 1.8   (flow_state.acceleration_ratio)
  CANCELLATION  < 0.7   (liquidity_state.metrics.cancellation_ratio)
  BIAS          > 0.3x  (mid price movement / spread over 60s)

Trigger: ALL FOUR conditions must be True → HypothesisSignal
```

**Design Rule:** Precise enough that two engineers implement identically. (ADR-007)

### 6.8 evidence/observation.py — EvidencePacket Factory

```
  - create(signal, states) → EvidencePacket (from H1 signal)
  - create_baseline(observation) → EvidencePacket (from baseline sampler)
```

**The most valuable object in the system.** A complete frozen snapshot of market state at observation time. Enables retrospective re-testing when new hypotheses emerge.

### 6.9 evidence/tracker.py — 20-Minute Outcome Tracker

```
Internal: dict[UUID → _TrackingEntry] with mutable tracking state
  - start_tracking(packet) → begin monitoring
  - on_price_update(price, timestamp) → list[OutcomeResult] (newly finalized)
  - finalize(obs_id) → force-finalize an observation
```

**Outcome Tiers:**
| Tier | Condition | Invalidation |
|------|-----------|-------------|
| Tier 1 (Truth) | Price moves in predicted direction | Price returns to origin first |
| Tier 2 (Utility) | Price reaches ≥ 1 ATR from origin | Same |
| Tier 3 (Anomaly) | Price reaches ≥ 2 ATR from origin | Same |

**Invalidation is permanent.** Even if price later reaches target, once origin is crossed, outcome = FAIL.

### 6.10 evidence/statistics.py — MathEngine

```
Pure static methods. No state. Knows nothing about trading.
  - calculate_lift(h1_s, h1_t, bl_s, bl_t) → float
  - wilson_score_interval(successes, trials, confidence) → (lower, upper)
  - bayesian_update(prior, likelihood, count) → posterior mean
  - sample_size_required(min_lift, baseline_rate, power, alpha) → int
  - regime_stratified_lift(observations, regime) → float
  - generate_report(...) → StatisticalReport
```

### 6.11 evidence/research.py — Hypothesis Lifecycle

```
HypothesisLifecycle manages H1 through its lifetime:
  evaluate()
    → Queries statistics.py, produces HypothesisRecord with lift, CI, regimes
  check_survival(record)
    → Tests all 5 criteria (min obs, min lift, CI > baseline, regimes, stability)
  promote_to_edge()
    → Creates EdgeRecord, marks SURVIVING status
  retire_to_graveyard(cause)
    → Creates GraveyardEntry, marks DEAD, preserves all evidence
  generate_weekly_report()
    → "What truth did we learn this week?" plain-text output
```

**Survival Criteria (All Five Required):**
| Criterion | Threshold |
|-----------|-----------|
| Minimum observations | 500 |
| Minimum lift | 1.25 |
| Confidence (CI lower > baseline rate) | 95% |
| Regime coverage | ≥ 3 regimes with positive lift |
| Stability | Lift range ≤ 0.30 over last 100 obs |

### 6.12 edge/scheduler.py — Observation Scheduler

```
Pure timer/cooldown logic. No market state awareness.
  - should_evaluate_h1(timestamp_ms) → bool (cooldown-aware)
  - record_h1_signal(timestamp_ms) → starts 1-min cooldown
  - should_sample_baseline(timestamp_ms) → bool (5-min interval)
  - get_state(timestamp_ms) → SchedulerState (immutable snapshot)
```

**Timing:**
- H1 cooldown: 60,000 ms (1 minute between H1 observations)
- Baseline interval: 300,000 ms (5 minutes)
- Cooldown prevents observation spam from the same persistent liquidity event

### 6.13 edge/ledger.py — EdgeLedger + SlippageRegulator

```
EdgeLedger manages surviving hypotheses:
  - register_edge(edge) / unregister_edge(id)
  - compute_weight(edge) → float (composite of lift, CI tightness, regime diversity)
  - get_weights() → dict[id → weight]
  - dynamic_allocation(liquidity_state) → list[AllocationInstruction]

SlippageRegulator:
  - estimate_slippage(liquidity, size, direction) → bps
  - adjust_size(desired_size, liquidity) → (adjusted, estimated_bps, sufficient)
```

**Weight Formula:**
```
weight = lift_norm * 0.5 + ci_tightness * 0.3 + regime_diversity * 0.2
  lift_norm = 1 - 1/lift           (higher lift → higher weight)
  ci_tightness = lower_ci/upper_ci  (narrower CI → higher weight)
  regime_diversity = min(1, n/5)   (more regimes → higher weight)
```

### 6.14 persistence/journal.py — Evidence Journal

```
Append-only JSON Lines format. Entry types:
  OBSERVATION, OUTCOME, HYPOTHESIS_CHANGE, REGIME,
  FALSE_SIGNAL, MISSED_OPPORTUNITY, SYSTEM_EVENT,
  H1_EVALUATION, EDGE_PROMOTION, ALLOCATION

Features:
  - Auto-rotation at max_entries (default: 100,000)
  - Gzip compression on rotation. Archived files never deleted.
  - Thread-safe via Lock on all public methods
  - Time-range, type, and limit filtering on reads
  - Context manager support
```

### 6.15 persistence/db.py — DreamswapDB (SQLite)

```
11 tables matching design doc schema:
  observations, evidence_packets, outcomes,
  hypotheses, hypothesis_versions, hypothesis_trials,
  regimes,
  false_signals, missed_opportunities,
  graveyard, edges

Features:
  - WAL journal mode for concurrent reads
  - Thread-safe via per-thread connections + write lock
  - CHECK constraints on all enum columns
  - NOT NULL on all design-specified columns
  - @property — Decimal precision for origin_price
  - Indexed on timestamp, is_baseline, invalidated, regime_type, hypothesis_id
```

### 6.16 main.py — DreamswapOrchestrator

```
Event loop (called on every MarketEvent):
  1. book.py / flow.py / liquidity.py / regime.py ← update state
  2. Build StateBundle from all module snapshots
  3. tracker.py ← process price update (finalize expired observations)
  4. scheduler.py ← check if H1 evaluation is due
     ├── h1.py ← evaluate conditions
     │   └── If signal: observation.py → create EvidencePacket
     │       ├── tracker.py ← start_tracking()
     │       ├── journal.py ← append(OBSERVATION)
     │       └── db.py ← save_observation()
     └── baseline.py ← sample if due (every 5 min)

Periodic (called externally or on schedule):
  5. lifecycle.py ← evaluate() → HypothesisRecord
  6. lifecycle.py ← check_survival() → promote_to_edge() if met
  7. ledger.py ← register_edge() → dynamic_allocation()

Failure Handling:
  - Every step wrapped in try/except — crash logs, loop continues
  - DB failure → log + retry on next cycle
  - Feed disconnect → reconnect loop
```

---

## 7. Key Design Decisions (ADRs)

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-001 | System as Evidence Engine (not trading bot) | Profit corrupts feedback loops. Optimize for truth. |
| ADR-002 | SQLite over TimescaleDB/PostgreSQL | Single-node. No external deps. ~1MB/year data volume. |
| ADR-003 | In-memory state over Redis | Single process. No network hop. ~10MB state. |
| ADR-004 | WebSocket over REST/FIX | Real-time push. Sub-10ms. Standard for crypto. |
| ADR-005 | Top-5 book depth over full book | H1 only needs visible liquidity. Full book = noise. |
| ADR-006 | EvidencePacket as frozen snapshot | Enables retrospective re-testing. Time capsule. |
| ADR-007 | Boolean conditions over fuzzy logic | Science cannot test ambiguity. Two engineers must agree. |
| ADR-008 | Active baseline sampling over historical negation | Active sampling ensures matched conditions. 288/day. |

---

## 8. Validation & Test Status

| Phase | Module | Tests | Status |
|-------|--------|-------|--------|
| Phase 1 | feed/*, core/* | feed/book integration | ✅ Pass |
| Phase 2 | state/* | All state modules + snapshot | ✅ Pass |
| Phase 3 | hypothesis/h1.py | Condition evaluation | ✅ Pass |
| Phase 4 | evidence/observation.py, tracker.py | End-to-end observation→outcome | ✅ Pass |
| Phase 5 | evidence/statistics.py, research.py | Math accuracy, lifecycle | ✅ Pass |
| Phase 6 | edge/ledger.py, scheduler.py | Weight, allocation, cooldown | ✅ Pass |
| Phase 7 | persistence/journal.py, db.py | Append-only, schema, CRUD | ✅ Pass |
| Phase 8 | main.py | Full system orchestration | ✅ Pass |

**Total: 317 tests. All passing.**

---

## 9. Anti-Patterns (Enforced)

| Anti-Pattern | How Prevented |
|-------------|---------------|
| Optimizing for profit | Primary metric = lift, not PnL |
| Changing survival criteria mid-test | SurvivalCriteria is immutable (frozen dataclass) |
| Deleting failed observations | Journal is append-only. Never delete. |
| Adding H2 before H1 survives | promote_to_edge() gate → RuntimeError |
| Using win rate instead of lift | calculate_lift() requires baseline rate |
| Ignoring regime context | Every EvidencePacket contains regime_state at origin |
| Module importing upward | Dependency graph enforced via protocol.py |

---

## 10. The Product

> **The product is the accumulated body of evidence.**

If all trading functionality were removed, DREAMSWAP should still answer:

> **"What new truth about DOGE market behavior did we learn this week?"**

The system converts:
- **Market activity** → Evidence
- **Evidence** → Hypotheses
- **Hypotheses** → Knowledge

That is the design.

---

*Last updated: 2026-06-19 — 317 tests passing across 8 phases*
