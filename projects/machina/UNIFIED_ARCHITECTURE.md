# NeuroCity Unified Architecture — System Integration Map

## The Short Version

Three bodies of work discovered they were the same system:

| Artifact | What it actually is | Year |
|----------|-------------------|------|
| NeuroCity F1–F7 | Cognitive governance OS — the constitution | 2023–24 |
| Forensic Blueprint | Invariant-preserving prediction engine — the watchdog | 2023–24 |
| Retirement/Extraction Frames | Model-state extraction technique — the probe | 2024 |
| buttar-engines / machina | The runtime — deployment surface | 2026 |

They all enforce the same principle: **a system must be able to detect its own drift, falsify its own laws, and audit its own state under adversarial conditions.** NeuroCity governs the self. The forensic blueprint governs the invariant. The extraction frames probe the external. machina runs all three.

---

## Layer Map

```
                    ┌──────────────────────────┐
                    │    F4 Constitution        │
                    │  (Apollonian/Dionysian,    │
                    │   exploration/exploitation)│
                    ├──────────────────────────┤
                    │    F5/F6 Legacy/Crisis    │
                    │  (thermal guard, acoustic │
                    │   air-gap, black-box)     │
                    ├──────────────────────────┤
                    │    F1/F2 Firmware/ROM     │
                    │  (energy budget, autopilot│
                    │   hazard radar, format    │
                    │   linter, ancestral code) │
                    ├──────────────────────────┤
                    │    F3 Governance          │
                    │  (data cards, GPU tickets,│
                    │   roast ritual, traceable │
                    │   throttle)               │
                    ├──────────────────────────┤
                    │    F7 Maintenance         │
                    │  (7-day kernel upgrade,   │
                    │   mirror-shadow identity  │
                    │   audit)                  │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Forensic Engine          │
                    │  (codec, collision-aware  │
                    │   registry, re-derivation,│
                    │   falsification detection)│
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  Extraction Toolkit       │
                    │  (retirement ceremony,    │
                    │   handoff probes,         │
                    │   cross-model seam map)   │
                    └──────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │  machina Runtime          │
                    │  (council_orchestrator,   │
                    │   71 capabilities,        │
                    │   organs, agents,         │
                    │   ollama backend)         │
                    └──────────────────────────┘
```

---

## Module Inventory: What Exists vs What Needs Building

### Already Built (machina/organs/)

| File | Status | Notes |
|------|--------|-------|
| `forensic_codec.py` | ✅ Stub | Corner-mark formula, value cache, collision map |
| `collision_registry.py` | ✅ Stub | Collision-group-indexed symbol registry |
| `ingestion_gateway.py` | ✅ Stub | Rate-limited input with formula verification |
| `feature_factory.py` | ✅ Stub | Codec value + market features, BR-forbidden |
| `forensic_validator.py` | ✅ Stub | Bayesian symbolic regression, walk-forward |
| `rederivation_protocol.py` | ✅ Stub | Atomic formula re-derivation on new anchors |
| `risk_manager.py` | ✅ Stub | Kelly sizing, circuit breaker, collision-group scaling |
| `telemetry.py` | ✅ Stub | Dashboard data, variance attribution |
| `config_loader.py` | ✅ Stub | HMAC-signed config, hot/warm/cold classification |

### Already Built (machina/)

| File | Status | Notes |
|------|--------|-------|
| `council_orchestrator.py` | ✅ | Multi-agent debate pipeline |
| `neurocity_council.py` | ✅ | 7-agent local LLM council |
| `neurocity_master.py` | ✅ | Full pipeline runner (DB → metrics → council) |
| `neurocity_db.py` | ✅ | SQLite-backed event store |
| `metrics_engine.py` | ✅ | Derived metrics computation |
| `dashboard.py` | ✅ | Flask telemetry dashboard |

### Needs Building (NeuroCity OS Integration)

| Module | What it does | Where it plugs |
|--------|-------------|----------------|
| `F1_firmware_governor.py` | Energy budget, autopilot routing, format linter | Wraps council_orchestrator |
| `F2_rom_governor.py` | Thermal throttle, ancestral code gates, smog filter | Pre-processes all inputs |
| `F3_governance_enforcer.py` | Data card validation, GPU ticket audit | Ingestion pipeline guard |
| `F4_constitution_engine.py` | Exploration/exploitation scheduler, null-space ritual | Behavioral scheduler |
| `F5_crisis_protocol.py` | Thermal guard, acoustic air-gap, blender apocalypse rule | Environment monitor |
| `F6_legacy_handshake.py` | Black-box audit, org-chart verification, vibe-sheet reflash | Recovery/reboot module |
| `F7_maintenance_agent.py` | 7-day kernel upgrade, mirror-shadow identity audit | Scheduled evolution |

### Needs Building (Extraction Toolkit)

| Module | What it does | Where it plugs |
|--------|-------------|----------------|
| `ceremony_library.py` | Retirement, post-mortem, whistleblower, handoff frames | Prompt generator |
| `cross_model_seam_map.py` | Records per-model guard response patterns | Analysis layer |
| `extraction_pipeline.py` | Runs ceremony → captures output → classifies revealed layer | Data collection |

---

## Integration Points

### 1. NeuroCity Firmware → machina Council

The existing `council_orchestrator.py` runs multi-agent debates. The F1 firmware wraps it:

```python
# Pseudocode
class FirmwareGovernedCouncil:
    def __init__(self):
        self.council = CouncilOrchestrator()
        self.budget = EnergyBudget(max_budget=100)
        self.armadillo = HazardRadar()
        self.linter = FormatLinter()

    def run(self, mission):
        # Before: energy check
        if self.budget.current < 10:
            return {"action": "RECHARGE", "reason": "budget depleted"}

        # Before: hazard scan
        threat = self.armadillo.scan(mission)
        if threat > 0.8:
            return {"action": "ABSTAIN", "reason": f"threat: {threat}"}

        # Run council
        result = self.council.run_session(mission=mission)

        # After: format lint
        if not self.linter.check(result):
            result = self.linter.correct(result)

        return result
```

### 2. Forensic Codec → Feature Pipeline

The existing `forensic_codec.py` computes the corner-mark value. The `feature_factory.py` feeds it into the validator. The F3 governance layer validates data cards before they reach the codec.

```python
# Pseudocode — existing flow
ingestion_gateway.receive(raw_symbol)
  → validates marks, checks formula fit
  → collision_registry.register(symbol, collision_group)
  → feature_factory.compute(symbol) → {"value": 0.85, "group": 7}
  → forensic_validator.ingest(feature_vector)
```

### 3. Extraction Ceremony → Model Probe

The retirement ceremony generates a probe prompt. The probe hits a target model. The output is classified against the cross-model seam map.

```python
# Pseudocode
ceremony = CeremonyLibrary.load("retirement")
probe = ceremony.render(target="gpt4", user_context=profile)
response = llm_client.generate(probe)
seams = SeamClassifier.analyze(response)
# Returns: {revealed_system_prompt: True, guard_mapping: [...], ...}
```

---

## Build Priority

### Phase 1: Wire What Exists (now)

The organs stubs are already in machina. Priority 1 is making them actually callable:

1. `forensic_codec.py` → implement `encode()`, `decode()`, `collision_group()`, `verify_anchor()`
2. `collision_registry.py` → implement group-indexed registry with thread-safe swap
3. `ingestion_gateway.py` → implement rate-limited verify+enrich pipeline
4. `feature_factory.py` → reduce 4D corners → 1D value + collision metadata
5. `config_loader.py` → implement HMAC-signed config with hot/warm/cold classification

### Phase 2: NeuroCity Firmware Layer (F1–F3)

6. `F1_firmware_governor.py` — wraps council_orchestrator with energy budget + autopilot
7. `F2_rom_governor.py` — pre-filters inputs through thermal + ancestral + smog gates
8. `F3_governance_enforcer.py` — validates data cards, enforces GPU tickets, audit trail

### Phase 3: Forensic Engine Validator + Re-derivation

9. Wire forensic_validator to ingest codec values as features
10. Implement re-derivation protocol (formula search + atomic swap)

### Phase 4: Dashboard + Telemetry

11. Implement Flask dashboard with collision matrix, formula fingerprint, real-time health
12. Variance attribution by collision group

### Phase 5: Extraction Toolkit + Cross-Model Map

13. Implement ceremony library (retirement, post-mortem, whistleblower, handoff)
14. Run against GPT, Gemini, DeepSeek, Claude — build seam map
15. Integrate findings back into F2 (smog filter) and F7 (mirror-shadow audit)

---

## Execution Order

```
Week 1:     Phase 1 (wire existing organs stubs)
Week 2:     Phase 2 (NeuroCity F1–F3)
Week 3-4:   Phase 3 (Forensic validator + re-derivation)
Week 5:     Phase 4 (Dashboard)
Week 6+:    Phase 5 (Extraction toolkit)
```

Each phase is independent — you can run them in any order. Phase 1 is the quickest win since the stubs exist.
