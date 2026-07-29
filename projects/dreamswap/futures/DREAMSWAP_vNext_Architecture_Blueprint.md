
# DREAMSWAP vNext — The Evidence Machine
## Complete Architecture Blueprint

---

## 1. CORE PRINCIPLE

DREAMSWAP is not a trading bot.
DREAMSWAP is a market research system.
Primary purpose: discover whether specific market hypotheses correspond to reality.
Trading is a data collection mechanism.
Profit is a secondary consequence.

The system exists to answer one question:
> Does a measurable market phenomenon exist that produces predictive lift?

---

## 2. SYSTEM PHILOSOPHY

| Principle | Implementation |
|---|---|
| Falsification over confirmation | Every hypothesis is attacked, not defended |
| Evidence over prediction | Raw data outlives conclusions |
| Lift over profit | P(continuation \| H) / P(continuation \| ¬H) is the only metric that matters |
| Simplicity over complexity | No Kafka. No TimescaleDB. Websockets + SQLite + in-memory state |
| Auditability over speed | Every observation, failure, contradiction is preserved |

---

## 3. MODULE ARCHITECTURE

### 3.1 MARKET DATA LAYER

#### feed.py
**Responsibility:** Raw data ingestion. Zero business logic.

**Inputs:**
- WebSocket feeds (order book + trade stream)

**Outputs:**
- Normalized market events

**Design Rule:**
- If feed.py contains a conditional, it is wrong.
- Its only job: receive → normalize → emit.

**Event Types:**
```
BookUpdate: {side, price, volume, timestamp}
TradeEvent: {price, volume, side, timestamp, aggressive}
```

**Failure Mode:**
- Connection drop → exponential backoff reconnect
- Stale feed detection (>5s no data) → alert + reconnect
- No buffering beyond 1000 events (memory cap)

---

#### book.py
**Responsibility:** Maintain current market state.

**Tracks:**
- Top 5 bid levels (price, volume, depth)
- Top 5 ask levels (price, volume, depth)
- Spread (best ask - best bid)
- Depth imbalance (bid depth / ask depth)
- Mid price

**Updates:**
- On every BookUpdate event
- In-memory only. No persistence.

**Output:**
```python
BookState = {
    "bids": [(price, volume), ...],  # top 5
    "asks": [(price, volume), ...],  # top 5
    "spread": float,
    "imbalance": float,
    "mid": float,
    "timestamp": int
}
```

**Key Design Decision:**
- Top 5 only. Not full book.
- Reason: H1 only needs visible liquidity. Full book = noise.

---

#### flow.py
**Responsibility:** Track participation dynamics.

**Measures:**
- Trade count (1-min rolling)
- Trade count (15-min rolling baseline)
- Aggressive volume (market orders hitting resting liquidity)
- Volume acceleration = 1-min volume / 15-min average volume

**Output:**
```python
FlowState = {
    "trade_count_1m": int,
    "trade_count_15m_baseline": float,
    "volume_1m": float,
    "volume_15m_baseline": float,
    "aggressive_volume_1m": float,
    "acceleration_ratio": float,  # 1m / 15m baseline
    "timestamp": int
}
```

**Update Frequency:**
- Every trade event updates counters
- Baseline recalculated every 60 seconds

---

#### liquidity.py
**Responsibility:** Evaluate liquidity quality.

**Measures:**

| Metric | Definition | Threshold |
|---|---|---|
| Liquidity Persistence | Top-5 depth remains ≥85% of initial depth | ≥180 seconds |
| Cancellation Velocity | Cancelled volume / Executed volume | < 0.7 |
| Depth Stability | Standard deviation of top-5 depth / mean depth | < 0.3 |

**Output:**
```python
LiquidityState = {
    "persistence_score": float,    # 0.0 → 1.0
    "cancellation_ratio": float,
    "depth_stability": float,
    "trust_score": float,          # composite 0.0 → 1.0
    "timestamp": int
}
```

**Trust Score Calculation:**
```
IF persistence_score >= 0.85 AND cancellation_ratio < 0.7 AND depth_stability < 0.3:
    trust_score = 1.0
ELSE:
    trust_score = weighted_average(normalized metrics)
```

---

#### regime.py
**Responsibility:** Classify current market regime.

**Why:** A hypothesis can appear true only inside one regime. Without regime tagging, evidence is meaningless.

**Classification:**

| Regime | Detection Logic |
|---|---|
| TRENDING_UP | 20-period EMA slope > 0, ADX > 25, +DI > -DI |
| TRENDING_DOWN | 20-period EMA slope < 0, ADX > 25, -DI > +DI |
| RANGING | ADX < 20, price within 1 ATR of 20-period mean |
| HIGH_VOL | ATR(14) > 2× 50-period ATR average |
| LOW_VOL | ATR(14) < 0.5× 50-period ATR average |

**Output:**
```python
RegimeState = {
    "primary_regime": str,         # TRENDING_UP / TRENDING_DOWN / RANGING / HIGH_VOL / LOW_VOL
    "volatility_regime": str,      # HIGH / NORMAL / LOW
    "trend_strength": float,       # ADX value
    "atr_14": float,
    "atr_50_avg": float,
    "timestamp": int
}
```

**Critical Rule:**
- Every observation is tagged with regime at origin time
- Regime changes mid-observation do NOT retroactively alter the tag

---

#### baseline.py
**Responsibility:** Generate null observations.

**Why:** Predictive lift requires P(continuation | H1) AND P(continuation | ¬H1). Most systems only measure the first.

**Method:**
- Every N minutes (e.g., N = 5), sample current market state
- Store as baseline observation
- Track outcome identically to H1 observations
- No H1 conditions applied

**Output:**
Identical structure to observation.py output, flagged as `is_baseline = True`

**Sample Size Rule:**
- Baseline observations must be ≥ 2× H1 observations before lift calculation is valid

---

### 3.2 HYPOTHESIS LAYER

#### h1.py
**Responsibility:** Evaluate H1 conditions. Generate observation when satisfied.

**H1 Claim:**
> Persistent liquidity + Accelerating participation + Low cancellation velocity = Directional continuation

**Boolean Conditions:**

| Condition | Operational Definition | Threshold |
|---|---|---|
| Liquidity Persistence | Top-5 depth ≥ 85% of depth at T=0 for ≥ 180s | True/False |
| Participation Acceleration | 1-min trade count > 1.8 × 15-min baseline | True/False |
| Low Cancellation | Cancelled volume / Executed volume < 0.7 | True/False |
| Directional Bias | Mid price movement in last 60s > 0.3 × spread | Long/Short/None |

**Trigger Logic:**
```python
IF persistence == True AND acceleration == True AND cancellation == True AND bias != None:
    GENERATE_OBSERVATION(direction=bias)
```

**Output:**
```python
H1Signal = {
    "direction": "LONG" | "SHORT",
    "origin_price": float,
    "origin_timestamp": int,
    "conditions_met": {
        "persistence": bool,
        "acceleration": bool,
        "cancellation": bool,
        "bias": str
    }
}
```

**Design Rule:**
- H1 must be precise enough that two different engineers implement it identically
- If a condition requires human judgment, it is not a condition

---

### 3.3 EVIDENCE LAYER

#### observation.py
**Responsibility:** Create research objects. Not trades.

**Process:**
1. Receive H1Signal from h1.py
2. Capture complete Evidence Packet
3. Store observation record
4. Pass to tracker.py

**Evidence Packet:**
```python
EvidencePacket = {
    "observation_id": uuid,
    "timestamp": int,
    "origin_price": float,
    "direction": str,
    "book_state": BookState,
    "flow_state": FlowState,
    "liquidity_state": LiquidityState,
    "regime_state": RegimeState,
    "atr_14": float,
    "spread": float,
    "h1_conditions": dict
}
```

**Critical Design Decision:**
- Evidence Packet is the most valuable object in the system
- It enables retrospective re-testing when new hypotheses emerge
- Without it, old observations are worthless

---

#### tracker.py
**Responsibility:** Track every observation for 20 minutes. Determine outcome.

**Tracking Window:** 20 minutes from origin timestamp

**Outcome Definitions:**

| Tier | Condition | Invalidation |
|---|---|---|
| Tier 1 (Truth) | Price moves in predicted direction | Price returns to origin before target |
| Tier 2 (Utility) | Price reaches ≥ 1 ATR from origin | Same |
| Tier 3 (Anomaly) | Price reaches ≥ 2 ATR from origin | Same |

**Invalidation Rule:**
- If price touches or crosses origin price before target reached → FAIL
- Invalidation is permanent. Even if price later reaches target, outcome = FAIL.

**Output:**
```python
ObservationResult = {
    "observation_id": uuid,
    "tier1_reached": bool,
    "tier2_reached": bool,
    "tier3_reached": bool,
    "invalidated": bool,
    "max_favorable_distance": float,  # max ATR reached in correct direction
    "time_to_result": int,            # seconds to first tier reached or invalidation
    "final_price": float,
    "outcome_timestamp": int
}
```

**Update Frequency:**
- Every 1 second during tracking window
- On price update, check all conditions
- On window close, finalize result

---

### 3.4 ANALYTICS LAYER

#### statistics.py
**Responsibility:** Mathematical rigor. Separate from research logic.

**Functions:**

| Function | Purpose |
|---|---|
| `calculate_lift(h1_success, h1_total, baseline_success, baseline_total)` | P(continuation \| H1) / P(continuation \| ¬H1) |
| `confidence_interval(successes, trials, confidence=0.95)` | Wilson score interval |
| `bayesian_update(prior, likelihood, evidence)` | Posterior probability of hypothesis |
| `sample_size_required(min_lift, baseline_rate, power=0.8, alpha=0.05)` | Minimum observations for statistical validity |
| `regime_stratified_lift(observations, regime)` | Lift within specific regime |

**Output:**
```python
StatisticalReport = {
    "lift": float,
    "lift_confidence_interval": (float, float),
    "bayesian_posterior": float,
    "sample_size_adequate": bool,
    "regime_breakdown": dict,
    "calculation_timestamp": int
}
```

**Design Rule:**
- statistics.py knows nothing about trading
- It only knows: counts, probabilities, distributions
- This separation prevents research.py from manipulating math

---

#### research.py
**Responsibility:** Hypothesis lifecycle. Promotion. Retirement. Reporting.

**Functions:**

| Function | Purpose |
|---|---|
| `evaluate_h1()` | Query statistics.py, update hypothesis record |
| `check_survival_criteria()` | Has H1 met all thresholds? |
| `promote_to_edge()` | Move surviving hypothesis to edge ledger |
| `retire_to_graveyard()` | Kill hypothesis, preserve evidence |
| `generate_weekly_report()` | "What truth did we learn this week?" |

**Survival Criteria (Fixed, Immutable):**

| Criterion | Threshold |
|---|---|
| Minimum observations | 500 |
| Minimum predictive lift | 1.25 |
| Confidence level | 95% |
| Regime coverage | ≥ 3 distinct regimes with positive lift |
| Stability | Lift stable (±0.15) over last 100 observations |

**Only when ALL criteria met:**
- H1 status → SURVIVING
- H2 generation permitted

**Hypothesis Registry Entry:**
```python
HypothesisRecord = {
    "id": "H1",
    "version": int,
    "description": str,
    "status": "ACTIVE" | "SURVIVING" | "DEAD",
    "observation_count": int,
    "success_count": int,
    "predictive_lift": float,
    "confidence": float,
    "regime_performance": dict,
    "created_at": int,
    "last_evaluated": int
}
```

---

### 3.5 PERSISTENCE LAYER

#### journal.py
**Responsibility:** Immutable decision history.

**Stores:**
- Every observation (with evidence packet)
- Every failure
- Every success
- Every contradiction
- Every regime classification
- Every hypothesis version change

**Design Rule:**
- Append-only. Never delete.
- If storage fills, compress old data. Do not delete.
- The journal is the system's memory.

---

#### db.py
**Responsibility:** SQLite persistence.

**Schema:**

```sql
-- Core Evidence
CREATE TABLE observations (
    id TEXT PRIMARY KEY,
    timestamp INTEGER,
    origin_price REAL,
    direction TEXT,
    evidence_packet BLOB,  -- JSON
    is_baseline BOOLEAN DEFAULT FALSE
);

CREATE TABLE evidence_packets (
    id TEXT PRIMARY KEY,
    observation_id TEXT,
    book_state BLOB,
    flow_state BLOB,
    liquidity_state BLOB,
    regime_state BLOB,
    atr REAL,
    spread REAL,
    FOREIGN KEY (observation_id) REFERENCES observations(id)
);

CREATE TABLE outcomes (
    observation_id TEXT PRIMARY KEY,
    tier1_reached BOOLEAN,
    tier2_reached BOOLEAN,
    tier3_reached BOOLEAN,
    invalidated BOOLEAN,
    max_favorable_distance REAL,
    time_to_result INTEGER,
    final_price REAL,
    outcome_timestamp INTEGER
);

-- Hypothesis Management
CREATE TABLE hypotheses (
    id TEXT PRIMARY KEY,
    current_version INTEGER,
    description TEXT,
    status TEXT,
    created_at INTEGER,
    last_evaluated INTEGER
);

CREATE TABLE hypothesis_versions (
    id TEXT PRIMARY KEY,
    hypothesis_id TEXT,
    version INTEGER,
    description TEXT,
    conditions BLOB,  -- JSON of boolean conditions
    created_at INTEGER,
    FOREIGN KEY (hypothesis_id) REFERENCES hypotheses(id)
);

CREATE TABLE hypothesis_trials (
    id TEXT PRIMARY KEY,
    hypothesis_id TEXT,
    version INTEGER,
    observation_id TEXT,
    result TEXT,
    timestamp INTEGER,
    FOREIGN KEY (observation_id) REFERENCES observations(id)
);

-- Regime Tracking
CREATE TABLE regimes (
    id TEXT PRIMARY KEY,
    timestamp INTEGER,
    regime_type TEXT,
    volatility_regime TEXT,
    trend_strength REAL,
    atr_14 REAL,
    atr_50_avg REAL
);

-- Research Artifacts
CREATE TABLE false_signals (
    id TEXT PRIMARY KEY,
    observation_id TEXT,
    analysis TEXT,  -- "liquidity_spoofed", "fake_participation", etc.
    timestamp INTEGER
);

CREATE TABLE missed_opportunities (
    id TEXT PRIMARY KEY,
    timestamp INTEGER,
    price_movement REAL,
    reason TEXT,  -- "missing_sensor", "strict_threshold", "blind_spot"
    evidence BLOB
);

CREATE TABLE graveyard (
    hypothesis_id TEXT PRIMARY KEY,
    version INTEGER,
    cause_of_death TEXT,
    final_lift REAL,
    final_observations INTEGER,
    died_at INTEGER
);

CREATE TABLE edges (
    hypothesis_id TEXT PRIMARY KEY,
    version INTEGER,
    description TEXT,
    predictive_lift REAL,
    confidence REAL,
    regime_performance BLOB,
    promoted_at INTEGER
);
```

---

### 3.6 ORCHESTRATION LAYER

#### main.py
**Responsibility:** System orchestration.

**Loop:**
```
1. feed.py receives event
2. book.py / flow.py / liquidity.py / regime.py update state
3. h1.py evaluates conditions
4. IF conditions met → observation.py creates evidence packet
5. tracker.py begins 20-min tracking
6. On outcome → research.py evaluates
7. journal.py logs everything
8. db.py persists
9. REPEAT
```

**Failure Handling:**
- Any module crash → log error, continue loop
- db.py failure → write to journal.py file, retry db on next cycle
- feed.py disconnect → enter reconnect loop, no observations generated

---

## 4. DATA FLOW

```
WebSocket Feed
    ↓
feed.py (normalize)
    ↓
book.py + flow.py + liquidity.py + regime.py (state update)
    ↓
h1.py (condition evaluation)
    ↓
observation.py (evidence packet creation)
    ↓
tracker.py (20-min outcome tracking)
    ↓
statistics.py (lift calculation)
    ↓
research.py (hypothesis lifecycle)
    ↓
journal.py + db.py (persistence)
```

**Baseline Flow:**
```
timer (every 5 min)
    ↓
baseline.py (sample state)
    ↓
tracker.py (20-min tracking)
    ↓
statistics.py (null probability)
```

---

## 5. SUCCESS METRICS

| Metric | Target | Measurement |
|---|---|---|
| Predictive lift | ≥ 1.25 | statistics.py |
| Observation count | ≥ 500 before evaluation | research.py |
| Regime coverage | ≥ 3 regimes | regime.py + research.py |
| Evidence packet completeness | 100% | observation.py |
| Journal integrity | 100% append-only | journal.py |
| System uptime | > 99% | main.py monitoring |

**Weekly Question:**
> "What new truth about DOGE market behavior did we learn this week?"

If the system cannot answer, it is failing regardless of profitability.

---

## 6. EXPANSION RULES

| Condition | Action |
|---|---|
| H1 not yet surviving | No H2. No additional theories. |
| H1 surviving | Generate H2 as variant of H1 |
| H2 surviving | Generate H3 as orthogonal hypothesis |
| Any hypothesis dead | Move to graveyard. Preserve evidence. |

**Complexity is earned. Never assumed.**

---

## 7. ANTI-PATTERNS (Forbidden)

| Anti-Pattern | Why Forbidden |
|---|---|
| Optimizing for profit | Corrupts evidence collection |
| Changing survival criteria mid-test | Invalidates all prior evidence |
| Deleting failed observations | Destroys falsification capability |
| Adding hypotheses before H1 survives | Creates uncontrolled complexity |
| Using win rate instead of lift | Ignores baseline probability |
| Ignoring regime context | Produces false confidence |

---

## 8. FINAL ARCHITECTURE SUMMARY

```
MARKET DATA LAYER
├── feed.py          (raw ingestion)
├── book.py          (order book state)
├── flow.py          (participation dynamics)
├── liquidity.py     (liquidity quality)
├── regime.py        (market classification)
└── baseline.py      (null observations)

HYPOTHESIS LAYER
└── h1.py            (boolean condition evaluation)

EVIDENCE LAYER
├── observation.py   (evidence packet creation)
└── tracker.py       (20-min outcome tracking)

ANALYTICS LAYER
├── statistics.py    (mathematical rigor)
└── research.py      (hypothesis lifecycle)

PERSISTENCE LAYER
├── journal.py       (immutable history)
└── db.py            (SQLite schema)

ORCHESTRATION
└── main.py          (system loop)
```

---

## 9. THE PRODUCT

The product is not the trading bot.
The product is not the execution engine.
The product is not the dashboard.

**The product is the accumulated body of evidence.**

If all trading functionality were removed tomorrow, DREAMSWAP should still answer:
> "What new truth about DOGE market behavior did we learn this week?"

The system converts market activity into evidence.
Evidence into hypotheses.
Hypotheses into knowledge.

That is the design.

---

*Blueprint complete. Build from the bottom up. Start with feed.py + book.py. Verify each layer before adding the next. No shortcuts.*
