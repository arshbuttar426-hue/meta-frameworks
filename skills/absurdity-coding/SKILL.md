---
name: absurdity-coding
description: "12-domain equilibrium framework (v4): Domain 0 Nature + 10 sabotage domains + Domain -1 Parsimony. Every artifact must satisfy ALL forces simultaneously before it enters the codebase. Resolves cross-version domain mismatch (v2 vs v1.9 SKILL.md): the 10 sabotage domains are Metallurgy, Biology, Physics, Chemistry, Biomechanics, Philosophy, Psychology, Medicine, Economics, Cryptography. Neuroscience/Thermodynamics/Immunology/Tea Ceremony from v1.9 are subsumed."
metadata:
  category: coding-methodology
  version: 4.0
  architecture: hybrid
  based_on: "absurdity-protocol.md"
  domains: 12
  domain_0: "Nature — The Simultaneous Constraint"
  domain_-1: "Parsimony — Occam's Razor"
  reconciliation: >
    v4 absorbs all 10 sabotage domains from absurdity-protocol.md v2
    plus Domain 0 (Nature) and Domain -1 (Parsimony). The Force-Down
    Protocol self-applies at SKILL.md:3-16 (this front matter). A pruning
    schedule is established: domains with zero empirical contribution in
    the last 90 generations are deprecated.
---
# Absurdity Protocol — Full Creative Control Through Multidisciplinary Sabotage (v4)

> *A solution-forced framework that weaponizes deep principles from absurd domains (mycology, immunology, thermodynamics, economics, cryptography) to solve concrete engineering problems in AI creative pipelines. Every insight terminates in code.*

---

## Table of Contents

1. [The Continuation Problem](#1-the-continuation-problem)
2. [The Specificity Engine](#2-the-specificity-engine)
3. [The Force-Down Protocol (6 Steps)](#3-the-force-down-protocol-6-steps)
4. [The Eleven Domains of Sabotage](#4-the-eleven-domains-of-sabotage)
5. [Domain Interaction Matrix (Expanded)](#5-domain-interaction-matrix-expanded)
6. [Domain -1: The Negative Domain — Parsimony](#5b-domain--1-the-negative-domain--parsimony-occams-razor)
7. [Falsification Conditions](#5c-falsification-conditions)
8. [Confidence and Calibration](#5d-confidence-and-calibration)
9. [Domain Interconnection Web (Original)](#5-domain-interconnection-web-original)
10. [Validation Criteria & Self-Check](#6-validation-criteria--self-check)
11. [Implementation Roadmap & Priority Matrix](#7-implementation-roadmap--priority-matrix)
12. [Failure Mode Taxonomy](#7b-failure-mode-taxonomy)

---

## 1. The Continuation Problem

Every AI pipeline that:
1. Produces structured intermediate representations
2. Then compresses them through an LLM
3. Before passing to a downstream model

...is susceptible to **catastrophic information loss**. The bottleneck is not the model — it's the compiler. The Information Retention Ratio (IRR) of a typical prompt pipeline is ~34% — 66% of structured input data is lost before reaching the generative model.

### Information Retention Ratio (IRR)

```
IRR = |structured_output| / |structured_input|
     = 1.0 for lossless stages
     = 0.34 for lossy stages (Compiler at T=1.5)
```

### The Two Types of Pipeline Stages

| Stage Type | Behavior | Examples |
|:---|:---|:---|
| **Lossless** | Structured → Structured (data preserved) | CineSpec, LightSpec, CharacterDNA |
| **Lossy** | Structured → Summarized Text (data lost) | Compiler prompt assembly, LLM inference |

The critical insight: **the compiler's summarization is the single point of failure.** Every lossy stage compounds the problem — the Compiler receives degraded input from upstream lossy stages, then degrades it further through its own lossy summarization.

### The "34% Correction"

When the Compiler receives raw structured specs (cinema language) instead of summarized prose, the IRR can be driven from 0.34 back toward 1.0. The **34% correction** refers to the improvement achieved by eliminating one level of lossy summarization.

### Empirical Phase Landscape (MODELTUNE)

152 benchmark points across 6 models reveal temperature-dependent behavioral phases that directly affect IRR:

| Model | Phase 1 (T≤0.3) | Phase 2 (0.3<T<0.7) | Phase 3 (T≥0.7) | IRR Impact |
|-------|-----------------|----------------------|------------------|------------|
| **Gemma-12B** | Lossless, structured output | Lossless, structured output | Lossless, structured output | IRR≈1.0 at all temps |
| **Phi-4-mini** | Lossless, structured output | Lossless, structured output | Lossless, structured output | IRR≈1.0 at all temps |
| **Ornith-9B** | Verbose thinking wrapper, structured inside | Crisp structured output (IRR≈0.95) | Repetition loops (IRR≈0.2) | IRR≈0.95 at T=0.5, catastrophic at T≥0.7 |
| **VibeThinker-3B** | Never closes `<think>` — zero output | Partial delivery | Functional at T≥0.9 | IRR=0 at T<0.7, IRR≈0.6 at T≥0.9 |
| **Qwen3.5-4B** | Never closes `<think>` — zero output | Occasionally delivers at T=0.7 (20%) | Same | IRR=0.8 at T≈0.7 (only), 0 otherwise |
| **SmolLM3-3B** | Fast, shallow, structured | Fast, shallow, structured | Fast, shallow, structured | IRR≈0.7 at all temps (limited by capacity, not temp) |

**Key insight**: Compiler temperature reduction from 1.5 → 0.3 improves IRR from 0.34 to 0.89 (measured at `PHASE_TRANSITION_EXPLOIT.md`). The modeltune data at `/Users/arshbuttar/modeltune/tune_*.json` provides the empirical phase boundaries.

---

## 2. The Specificity Engine

A filter that rejects vague, philosophical, or non-specific statements. It mandates that any proposed solution must specify:

1. **File/class/function** — exact module path (e.g., `src/cinema/engines/continuation.py:ContinuityHomeostat`)
2. **Interface** — inputs/outputs with concrete types (e.g., `measure(frame_spec: FrameSpec) -> IRR: float`)
3. **Behavioral change** — not "improves quality" but "replaces X with Y" (e.g., "replaces monolithic Compiler.summarize() with RibosomeCompiler.translate()")
4. **Call site** — where it's invoked in the pipeline (e.g., `Pipeline.run()` before Generator)
5. **Test plan** — ≥3 test cases: normal, edge, failure

### Vague → Specific Translations

| Vague | Specific |
|:---|:---|
| "Improve continuity" | "Create `CharacterDNA.encode()` that extracts 13 traits from `CharacterProfile` and appends them verbatim to every `CompileIn` at `pipeline.py:147`" |
| "Optimize model selection" | "Create `TaskAuction.bid()` that scores each available model on `(speed × reliability / cost)` and selects winner at `task_auction.py:88`, replacing hard-coded `ChainConfig` at `engine.py:52`" |
| "Prevent drift" | "Create `ContinuityHomeostat.correct()` that checks `mass >= 2.0` and `segment > 2` before injecting a `[CORRECTION]` clause at `continuation.py:204`, called before each generator inference at `compiler.py:310`" |
| "Make pipeline faster" | "Replace `Gemma-12B` on `film_dna` stage with `Phi-4-mini` at `T=0.3`, reducing latency from 17s to 0.7s (+16.3s savings), validated by MODELTUNE `tune_phi_results.json` demonstrating 100% code correctness" |

---

## 3. The Force-Down Protocol (6 Steps)

A recursive process to move from abstract "principle" to tested "artifact":

| Step | What you do | Example (Domain 8: Medicine) |
|:---|:---|:---|
| 1. Reveal principle | State the domain principle | "Homeostatic systems maintain stable internal conditions through corrective feedback loops" |
| 2. Envision artifact | Name the concrete implementation | "ContinuityHomeostat class" |
| 3. Define interface | Specify exact input/output types | `ContinuityHomeostat.measure_and_correct(frame_spec: FrameSpec) -> FrameSpec` |
| 4. Pinpoint file location | Exact module path | `src/cinema/engines/continuation.py:120` |
| 5. Identify call site | Where it's invoked | `CompilerEngine.compile()` at `compiler.py:310` — called once per segment before LLM inference |
| 6. Plan tests | ≥3 test cases | 1. Zero drift → no correction. 2. Identity drift → correction injected. 3. Multiple set points → all corrected in priority order |

**Fractal invariant**: The Force-Down protocol applies to itself. Each step in the protocol is its own 6-step mini-workflow.

---

## 4. The Eleven Domains of Sabotage

Each domain is forced down to: **file path, class/function, typed interface, behavioral change, call site, test plan.**

---

### Domain 0: Nature — The Simultaneous Constraint

**Principle:** Before any domain — before metallurgy, before biology — the axiom: ALL forces apply ALL the time. A falling leaf obeys gravity, thermodynamics, fluid dynamics, material science, and chemistry simultaneously and never crashes. It does not have a physics phase followed by a chemistry phase. It is ALL constraints at once in a single unified equilibrium.

Current code breaks because it satisfies exactly one constraint: what the programmer intended. A bridge satisfies gravity, thermal expansion, wind load, material stress, and seismology simultaneously from the first sketch, or it collapses. Code should be the same.

**Force-Down:**

| Step | Artifact |
|:---|:---|
| **File** | `src/core/simultaneous.py` |
| **Class** | `SimultaneousConstraint`, `EquilibriumChecker` |
| **Interface** | `SimultaneousConstraint.check_all(artifact: Artifact) -> list[Force]` |
| | `EquilibriumChecker.equilibrium(forcers: list[Force]) -> bool` |
| **Behavioral change** | Replaces "optimize for one dimension (speed, readability, memory)" with "satisfy ALL dimensions simultaneously." A change is not accepted unless it passes EquilibriumChecker — all forces in balance. |
| **Call site** | Every commit, every merge, every refactor. Before code enters the artifact pool, it must satisfy every domain simultaneously. |

**Key insights this domain provides:**

1. **Current practice is single-force** — most code satisfies exactly one constraint (the feature works). It ignores substrate cost, information retention, distribution topology, and verification architecture.
2. **Nature never crashes** — because it never drops a constraint. The artifact either satisfies all forces or it does not exist.
3. **The 10 domains are not alternatives** — they are simultaneous obligations. You do not choose which domain to apply. You check whether your artifact satisfies *all of them at once.*

**Implementation:**
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Force:
    name: str
    satisfied: bool
    deviation: float  # 0.0 = perfect, higher = further from equilibrium


@dataclass
class Artifact:
    code: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SimultaneousConstraint:
    def __init__(self):
        self.checks: dict[str, Callable[[Artifact], Force]] = {}

    def register(self, name: str, check: Callable[[Artifact], Force]) -> None:
        self.checks[name] = check

    def check_all(self, artifact: Artifact) -> list[Force]:
        results = []
        for name, check in self.checks.items():
            results.append(check(artifact))
        return results


class EquilibriumChecker:
    MAX_DEVIATION = 0.1

    def equilibrium(self, forces: list[Force]) -> bool:
        if not forces:
            return True
        return all(f.satisfied and f.deviation <= self.MAX_DEVIATION for f in forces)

    def report(self, forces: list[Force]) -> str:
        lines = ["EQUILIBRIUM REPORT", "=" * 50]
        for f in forces:
            status = "✓" if f.satisfied and f.deviation <= self.MAX_DEVIATION else "✗"
            lines.append(f"  [{status}] {f.name}: deviation={f.deviation:.3f}")
        lines.append(f"\nOverall equilibrium: {'PASS' if self.equilibrium(forces) else 'FAIL'}")
        return "\n".join(lines)
```

**Tests** (`tests/test_simultaneous.py`):
1. `SimultaneousConstraint.check_all(artifact)` with 3 registered checks all passing → returns 3 Forces, all satisfied
2. `EquilibriumChecker.equilibrium([Force("test", True, 0.05)])` → returns True (within max deviation)
3. `EquilibriumChecker.equilibrium([Force("test", False, 0.5)])` → returns False (unsatisfied)
4. `EquilibriumChecker.equilibrium([Force("test", True, 0.2)])` → returns False (exceeds max deviation)

---

### Domain 1: Metallurgy — The Substrate Constraint

**Principle:** Every line of code is a tax on the physical properties of specific elements arranged in specific crystal lattices. Gold's electron configuration determines conductivity, which determines transistor gate speed, which determines clock cycles, which determines instruction throughput, which determines your program's real runtime. The substrate is not infinite, uniform, or free — it is a finite physical layer with temperature dependence, wire delay, and manufacturing variance. The element *is* the compiler.

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/core/substrate.py` |
| **Class** | `SubstrateConstraint`, `ConductivityModel` |
| **Interface** | `SubstrateConstraint.cycle_budget(algorithm: str) -> float` |
| | `SubstrateConstraint.material_cost(instruction: str) -> Joules` |
| | `ConductivityModel.latency(distance_nm: float) -> float` |
| **Behavioral change** | Replaces the assumption of infinite uniform compute with a substrate-aware model that budgets cycle count against physical wire delay, thermal state, and material conductivity. Every abstraction layer is annotated with its substrate cost. |
| **Call site** | Every branch prediction, cache miss, and pipeline stall — the substrate is the first thing evaluated before any domain-specific logic runs |

**Key insights this domain provides:**

1. **Purity matters** — doped silicon is faster but leakier. Abstractions are the same. Pure functional purity costs transistor budget.
2. **Impurities create properties** — without dopants, no transistor. Without clever hacks, no performance.
3. **Conductivity is temperature-dependent** — code runs faster or slower based on thermal state. The substrate *feels*.
4. **Wire delay dominates** — electrons move at finite speed. A 4GHz CPU spends most of its cycle waiting for signals to cross the die. Architecture is bottlenecked by *how far gold has to travel.*

**Implementation:**
```python
from __future__ import annotations
from dataclasses import dataclass

# Gold conductivity at 20°C: 4.1×10^7 S/m
# Speed of signal in copper: ~2/3 c ≈ 2×10^8 m/s
# Wire delay at 5nm process: ~100ps per mm

@dataclass
class SubstrateConstraint:
    material: str              # "gold", "copper", "silicon"
    conductivity_sm: float     # Siemens per meter
    thermal_coefficient: float # How conductivity changes with temp
    wire_delay_ps_per_mm: float

    def cycle_budget(self, algorithm: str, gate_count: int) -> float:
        base = self._base_cycles(algorithm, gate_count)
        thermal_penalty = self._thermal_derating()
        wire_penalty = self._wire_delay_penalty(gate_count)
        return base * thermal_penalty * wire_penalty

    def material_cost(self, instruction: str) -> float:
        base_cost = {"ADD": 0.1, "MUL": 0.3, "LOAD": 0.5, "STORE": 0.5, "BRANCH": 0.2}
        return base_cost.get(instruction, 0.15) * self.conductivity_sm / 4.1e7

    def _base_cycles(self, algorithm: str, gate_count: int) -> float:
        return {"O(n)": 1.0, "O(n^2)": 2.0, "O(log n)": 0.5}.get(algorithm, 1.0) * gate_count

    def _thermal_derating(self) -> float:
        # At 85°C, gold's conductivity drops by ~5%
        return 1.0 + (self.thermal_coefficient * 65)  # 20°C to 85°C rise

    def _wire_delay_penalty(self, gate_count: int) -> float:
        # More gates → longer wires → more delay
        return 1.0 + (gate_count / 1000) * (self.wire_delay_ps_per_mm / 100)


DEFAULT_SUBSTRATE = SubstrateConstraint(
    material="gold",
    conductivity_sm=4.1e7,
    thermal_coefficient=-0.0008,  # -0.08% per °C for gold
    wire_delay_ps_per_mm=100,
)
```

**Tests** (`tests/test_substrate.py`):
1. `SubstrateConstraint.cycle_budget("O(n)", 100)` with gold at 20°C → returns base × 1.0 (no thermal penalty)
2. `SubstrateConstraint.cycle_budget("O(n)", 1000)` → wire delay penalty increases (more gates → longer paths)
3. `SubstrateConstraint.material_cost("ADD")` → returns energy per transition for that instruction
4. `DEFAULT_SUBSTRATE.thermal_coefficient` = -0.0008 → confirms gold's temperature sensitivity

---

### Domain 2: Biology — Mycelial Distribution

**Principle:** Nodes should be semi-autonomous; creativity emerges from local resonance, not central command. Fungi solve problems through distributed computation across a network of hyphae. Local nodes make local decisions; the network learns through connection strength modulation.

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/engines/mycelial.py` |
| **Class** | `CreativeNode`, `MycelialNetwork`, `ZoneManager` |
| **Interface** | `CreativeNode.sense(signal: str) -> float` |
| | `CreativeNode.respond(signal: str, energy: float) -> str | None` |
| | `MycelialNetwork.route(field: str, task_type: str) -> list[CreativeNode]` |
| **Behavioral change** | Replaces monolithic `Compiler.compile()` at `compiler.py:180` with distributed `MycelialNetwork.route()` at `mycelial.py:60`. Each node processes its specialty field in parallel instead of the single LLM processing everything sequentially. |
| **Call site** | `Pipeline.run()` at `pipeline.py:200` — before generator inference, after all specs collected |

**Implementation:**
```python
from __future__ import annotations
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

SIMILARITY_THRESHOLD = 0.6


@dataclass
class CreativeNode:
    """Each node is a semi-autonomous creative agent forming a mycelial network."""
    node_id: str
    specialty: str                        # "camera", "character", "lighting", etc.
    model_key: str                        # Ollama model key
    temperature: float = 0.3
    local_state: dict = field(default_factory=dict)
    connections: list[str] = field(default_factory=list)   # node_ids
    connection_strengths: dict[str, float] = field(default_factory=dict)
    creativity_reserves: float = 1.0

    def sense(self, signal: str) -> float:
        """Compute resonance between signal and local_state. Returns 0.0-1.0."""
        signal_tokens = set(signal.lower().split())
        state_tokens = set(str(self.local_state.values()).lower().split())
        overlap = signal_tokens & state_tokens
        return len(overlap) / max(len(signal_tokens), 1)

    def respond(self, signal: str, energy: float) -> Optional[str]:
        """If signal resonates AND we have energy, respond. Silence is valid — let another node speak."""
        if self.sense(signal) >= SIMILARITY_THRESHOLD and self.creativity_reserves >= energy:
            self.creativity_reserves -= energy
            return f"[{self.specialty.upper()} NODE {self.node_id}]: {signal}"
        return None

    def reinforce(self, other_node_id: str, weight: float) -> None:
        """Strengthen connection to nodes that produced good outputs."""
        current = self.connection_strengths.get(other_node_id, 0.0)
        self.connection_strengths[other_node_id] = current + weight
        if other_node_id not in self.connections:
            self.connections.append(other_node_id)


@dataclass
class Zone:
    """Supply chain logistics: a zone is a pipeline stage cluster with a permanently loaded model."""
    stages: list[str]
    model_key: str
    temperature: float
    keep_loaded: bool = True
    loading_cost_s: float = 0.0


class ZoneManager:
    """Models are pickers assigned to zones (pipeline stages). A model NEVER leaves its zone during a run."""

    ZONES: dict[str, Zone] = {
        "creative": Zone(
            stages=["writer", "director"],
            model_key="hf.co/yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF:Q4_K_M",
            temperature=0.7, keep_loaded=True,
        ),
        "reasoning": Zone(
            stages=["dramaturg", "symbolism"],
            model_key="hf.co/zaakirio/Ornith-1.0-9B-uncensored-GGUF:Q4_K_M",
            temperature=0.5, keep_loaded=False, loading_cost_s=5.0,
        ),
        "fast_analysis": Zone(
            stages=["film_dna", "character"],
            model_key="hf.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF:Q4_K_M",
            temperature=0.3, keep_loaded=False, loading_cost_s=1.5,
        ),
        "precision": Zone(
            stages=["compiler"],
            model_key="hf.co/yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF:Q4_K_M",
            temperature=0.3, keep_loaded=True,
        ),
    }

    def get_zone(self, stage: str) -> Optional[Zone]:
        for zone_name, zone in self.ZONES.items():
            if stage in zone.stages:
                return zone
        return None

    def assign(self, stage: str) -> tuple[str, float, bool]:
        """Returns (model_key, temperature, is_already_loaded)."""
        zone = self.get_zone(stage)
        if not zone:
            raise ValueError(f"No zone found for stage '{stage}'")
        return zone.model_key, zone.temperature, zone.keep_loaded

    def stage_to_zone_map(self) -> dict[str, str]:
        return {stage: zname for zname, z in self.ZONES.items() for stage in z.stages}


class MycelialNetwork:
    """Distributes structured fields to specialist sub-generators in parallel."""

    def __init__(self, nodes: list[CreativeNode]):
        self.nodes = {n.node_id: n for n in nodes}
        self.executor = ThreadPoolExecutor(max_workers=len(nodes))
        self.zone_manager = ZoneManager()

    def route(self, field: str, task_type: str) -> list[CreativeNode]:
        """Find which nodes should handle this field based on specialty and resonance."""
        candidates = []
        for node in self.nodes.values():
            if node.specialty == task_type or node.sense(field) >= SIMILARITY_THRESHOLD:
                candidates.append(node)
        return candidates or list(self.nodes.values())

    def distribute(self, field: str, task_type: str) -> list[str]:
        """Fan out to matched nodes in parallel. Returns list of responses."""
        matched = self.route(field, task_type)
        if not matched:
            return []
        futures = {self.executor.submit(n.respond, field, 0.2): n.node_id for n in matched}
        results = []
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
        return results

    def reinforce_path(self, from_id: str, to_id: str, weight: float) -> None:
        if from_id in self.nodes and to_id in self.nodes:
            self.nodes[from_id].reinforce(to_id, weight)
```

**Tests** (`tests/test_mycelial.py`):
1. `CreativeNode.sense("camera: ARRI Alexa 75mm")` with `local_state={"camera": "ARRI"}` → returns ≥0.5
2. `CreativeNode.respond("foo", 0.5)` when `creativity_reserves=0.3` → returns `None` (insufficient energy)
3. `MycelialNetwork.route("lighting", "lighting")` with a node specializing in "lighting" → returns that node
4. `ZoneManager.assign("writer")` → returns Gemma-12B key, T=0.7, keep_loaded=True
5. `ZoneManager.assign("unknown_stage")` → raises `ValueError`

---

### Domain 3: Physics — Thermodynamics of Creativity (Maxwell's Demon)

**Principle:** Information can be sorted without energy cost if you know the labels. Entropy increases unless work is done to maintain order. Each LLM call is a heat bath — it injects thermal noise. The compiler is a heat sink that draws structured information into thermal equilibrium (generic prose).

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/engines/entropy.py` |
| **Class** | `EntropyAuditor`, `MaxwellCompiler` |
| **Interface** | `EntropyAuditor.measure(input_fields: dict, output_prompt: str) -> float` |
| | `EntropyAuditor.flag_lossy_stages(pipeline_log: list[StageRecord]) -> list[Flag]` |
| | `MaxwellCompiler.sort(specs: list[BaseModel]) -> SortedPrompt` |
| **Behavioral change** | Replaces `Compiler.compile()` that fuses specs into prose with `MaxwellCompiler.sort()` that sorts specs into labeled `[CAMERA]`, `[CHARACTER]`, `[LIGHTING]`, `[ENVIRONMENT]`, `[ACTION]` dimensions — the model sees organized structure, not summarized paragraphs. |
| **Call site** | `Pipeline.run()` at `pipeline.py:210` — after ContinuationEngine produces verdict, before CompilerEngine injects into prompt |

**Implementation:**
```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class StageRecord:
    stage_name: str
    input_fields: dict[str, Any]
    output_text: str
    latency_ms: float


@dataclass
class Flag:
    stage: str
    irr: float
    message: str
    severity: str  # "WARN" | "FAIL"


@dataclass
class SortedPrompt:
    camera: list[str] = field(default_factory=list)
    character: list[str] = field(default_factory=list)
    lighting: list[str] = field(default_factory=list)
    environment: list[str] = field(default_factory=list)
    action: list[str] = field(default_factory=list)
    continuity: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = []
        if self.camera:
            lines.append("[CAMERA]")
            lines.extend(f"  {c}" for c in self.camera)
        if self.character:
            lines.append("[CHARACTER]")
            lines.extend(f"  {c}" for c in self.character)
        if self.lighting:
            lines.append("[LIGHTING]")
            lines.extend(f"  {l}" for l in self.lighting)
        if self.environment:
            lines.append("[ENVIRONMENT]")
            lines.extend(f"  {e}" for e in self.environment)
        if self.action:
            lines.append("[ACTION]")
            lines.extend(f"  {a}" for a in self.action)
        if self.continuity:
            lines.append("[CONTINUITY]")
            lines.extend(f"  {c}" for c in self.continuity)
        return "\n".join(lines)


class MaxwellCompiler:
    """Acts as a sorter rather than a fuser. Sorts structured fields into labeled dimensions."""

    DIMENSION_MAP = {
        "camera_body": "camera", "lens": "camera", "focal_length": "camera", "aperture": "camera",
        "character_id": "character", "costume": "character", "expression": "character",
        "key_light": "lighting", "fill_light": "lighting", "color_temp": "lighting",
        "location": "environment", "time": "environment", "weather": "environment",
        "movement": "action", "gesture": "action", "interaction": "action",
    }

    def sort(self, specs: dict[str, Any]) -> SortedPrompt:
        prompt = SortedPrompt()
        for field_name, field_value in specs.items():
            dimension = self.DIMENSION_MAP.get(field_name, "environment")  # default to environment
            target = getattr(prompt, dimension)
            target.append(f"{field_name}: {field_value}")
        return prompt


class EntropyAuditor:
    """Measures information loss between input and output at each pipeline stage.
    IRR = preserved_fields / total_fields."""

    IRR_THRESHOLD = 0.5  # Stages below 50% retention are flagged

    def measure(self, input_fields: dict[str, Any], output_text: str) -> float:
        if not input_fields:
            return 1.0
        preserved = 0
        for key, value in input_fields.items():
            value_str = str(value)
            if value_str and value_str in output_text:
                preserved += 1
        return preserved / len(input_fields)

    def flag_lossy_stages(self, pipeline_log: list[StageRecord]) -> list[Flag]:
        flags = []
        for record in pipeline_log:
            irr = self.measure(record.input_fields, record.output_text)
            if irr < self.IRR_THRESHOLD:
                flags.append(Flag(
                    stage=record.stage_name,
                    irr=irr,
                    message=f"Lossy stage: IRR={irr:.2f} — {int((1-irr)*100)}% of structured data lost. "
                            f"Consider lowering temperature or using dimension-sorted prompts.",
                    severity="FAIL" if irr < 0.3 else "WARN",
                ))
        return flags

    def audit_report(self, pipeline_log: list[StageRecord]) -> str:
        flags = self.flag_lossy_stages(pipeline_log)
        if not flags:
            return "All stages pass entropy audit (IRR ≥ 0.5)."
        lines = ["ENTROPY AUDIT REPORT", "=" * 50]
        for f in flags:
            lines.append(f"  [{f.severity}] Stage '{f.stage}': IRR={f.irr:.0%}")
            lines.append(f"    {f.message}")
        return "\n".join(lines)
```

**Tests** (`tests/test_entropy.py`):
1. `measure({"camera": "ARRI Alexa 35"}, "The camera is an ARRI Alexa 35")` → returns 1.0
2. `measure({"camera": "ARRI Alexa 35"}, "A cinematic scene")` → returns 0.0 (field completely lost)
3. `flag_lossy_stages([StageRecord("compiler", {"lens": "75mm"}, "generic prose", 100)])` → 1 flag with IRR=0.0
4. `MaxwellCompiler.sort({"camera_body": "Alexa", "lens": "75mm", "key_light": "HMI"})` → SortedPrompt with camera=[...], lighting=[...]

---

### Domain 4: Chemistry — Catalytic Templates

**Principle:** A catalyst lowers activation energy without being consumed. The compiler is unchanged by translation — it should be a ribosome that faithfully translates structured fields into output slots.

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/engines/catalyst.py` |
| **Class** | `RibosomeCompiler`, `SemanticIsotope`, `CatalyticTemplate` |
| **Interface** | `RibosomeCompiler.translate(spec: BaseModel) -> str` |
| | `SemanticIsotope.embed(element: str, prompt: str) -> str` |
| | `CatalyticTemplate.fill(name: str, **kwargs) -> str` |
| **Behavioral change** | Replaces `Compiler._assemble_prompt()` that writes creative prose from specs with `RibosomeCompiler.translate()` that performs one-to-one field→slot mapping with zero information loss. Catalytic templates are registered once and never mutated. |
| **Call site** | `Pipeline.compile()` at `pipeline.py:230` — final assembly before sending to Generator |

**Implementation:**
```python
from __future__ import annotations
import hashlib
import random
from dataclasses import dataclass
from typing import Any


TRANSLATION_TABLE = {
    "camera_body": "camera: {value}",
    "lens": "lens: {value}",
    "focal_length_mm": "focal length: {value}mm",
    "aperture": "aperture: T/{value}",
    "shot_size": "shot: {value}",
    "angle": "angle: {value}",
    "movement": "movement: {value}",
    "key_light": "key light: {value}",
    "fill_light": "fill light: {value}",
    "color_temp_k": "color temperature: {value}K",
    "character_name": "character: {value}",
    "costume": "costume: {value}",
    "expression": "expression: {value}",
    "setting": "setting: {value}",
    "weather": "weather: {value}",
    "time_of_day": "time: {value}",
}


class RibosomeCompiler:
    """Faithfully translates each structured field into its output slot. No information is consumed."""

    def translate(self, spec: dict[str, Any]) -> str:
        output = []
        for field_name, field_value in spec.items():
            template = TRANSLATION_TABLE.get(field_name)
            if template:
                output.append(template.format(value=field_value))
            elif isinstance(field_value, str):
                # Unknown fields pass through verbatim (lossless by default)
                output.append(field_value)
        return "\n".join(output)

    def verify_irr(self, spec: dict[str, Any], output: str) -> float:
        preserved = sum(1 for v in spec.values() if str(v) in output)
        return preserved / len(spec) if spec else 1.0


@dataclass
class Isotope:
    element: str
    half_life: float
    detectable: list[str]


class SemanticIsotope:
    """Invisible 'tag' embedded in every prompt that the model preserves but we can detect.
    Analogous to radioactive tracers in chemical reactions — they reveal flow without altering behavior."""

    def __init__(self):
        self.periodic_table = {
            "CHARACTER": Isotope(
                element="Elias_Voss_001",
                half_life=float('inf'),
                detectable=["weathered brown leather coat", "gaunt face", "wooden staff"],
            ),
            "CAMERA": Isotope(
                element="ARRI_Alexa_35",
                half_life=float('inf'),
                detectable=["ARRI Prime DNA 75mm", "T/2.0", "Zeiss Suprema Prime"],
            ),
            "ENVIRONMENT": Isotope(
                element="Nalanda_ruins",
                half_life=3,
                detectable=["crumbling red sandstone", "broken stupa", "overgrown ivy"],
            ),
        }

    def embed(self, element_name: str, prompt: str) -> str:
        isotope = self.periodic_table.get(element_name)
        if not isotope or isotope.half_life <= 0:
            return prompt
        phrase = random.choice(isotope.detectable)
        return f"{prompt}\n[ISOTOPE:{element_name}:{phrase}]"

    def detect(self, output_prompt: str) -> list[str]:
        detected = []
        for element_name, isotope in self.periodic_table.items():
            for phrase in isotope.detectable:
                if phrase in output_prompt:
                    detected.append(element_name)
                    break
        return detected

    def retention_rate(self, output_prompt: str) -> float:
        detected = self.detect(output_prompt)
        return len(detected) / len(self.periodic_table) if self.periodic_table else 1.0


@dataclass(frozen=True)
class CatalyticTemplate:
    """A template that is registered once and never mutated — always the same, always reliable."""
    name: str
    version: str
    system_prompt: str
    body: str


class TemplateRegistry:
    _templates: dict[str, CatalyticTemplate] = {}

    @classmethod
    def register(cls, template: CatalyticTemplate) -> None:
        if template.name in cls._templates:
            raise ValueError(f"Template '{template.name}' already registered — templates are immutable")
        cls._templates[template.name] = template

    @classmethod
    def fill(cls, name: str, **kwargs) -> str:
        template = cls._templates.get(name)
        if not template:
            raise KeyError(f"Template '{name}' not found")
        try:
            return template.body.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Template '{name}' missing required field: {e}")

    @classmethod
    def system(cls, name: str) -> str:
        template = cls._templates.get(name)
        if not template:
            raise KeyError(f"Template '{name}' not found")
        return template.system_prompt


# Registration (happens once at import time)
TemplateRegistry.register(CatalyticTemplate(
    name="compiler",
    version="1.0.0",
    system_prompt="You faithfully translate structured field specifications into natural language. "
                  "Do not add, omit, or modify any specified value. Preserve every detail exactly.",
    body="[CAMERA]\n{camera_spec}\n\n[CHARACTER]\n{character_spec}\n\n[LIGHTING]\n{lighting_spec}\n\n"
         "[ENVIRONMENT]\n{environment_spec}\n\n[ACTION]\n{action_spec}\n\n[CONTINUITY]\n{continuity_verdict}",
))
```

**Tests** (`tests/test_catalyst.py`):
1. `RibosomeCompiler.translate({"camera_body": "Alexa 35", "focal_length_mm": 75})` → contains "camera: Alexa 35" and "focal length: 75mm", IRR=1.0
2. `SemanticIsotope.embed("CHARACTER", "a man walks in")` → appends isotope tag, output contains a detectable phrase
3. `SemanticIsotope.detect("weathered brown leather coat")` → returns `["CHARACTER"]`
4. `TemplateRegistry.fill("compiler", camera_spec="Alexa", character_spec="Elias")` → correctly filled, no KeyError
5. `TemplateRegistry.register(CatalyticTemplate("compiler", ...))` on existing name → raises `ValueError`

---

### Domain 5: Biomechanics — Joints Over Levers

**Principle:** Pipeline stages should be joints with degrees of freedom, not rigid levers. Joints flex under load rather than breaking. They have proprioception — awareness of their own position, tension, and velocity.

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/engines/biomechanics.py` |
| **Class** | `CreativeJoint`, `CreativeCerebellum` |
| **Interface** | `CreativeJoint.transmit(signal: dict, context: PipelineContext) -> dict` |
| | `CreativeCerebellum.sense(element: str) -> Proprioception` |
| | `CreativeCerebellum.correct(frame_spec: FrameSpec) -> FrameSpec` |
| **Behavioral change** | Replaces rigid sequential pipeline stages (`writer→dramaturg→director→...)` with flex joints that allow downstream stages to interpret within bounded drift when tension is high. Adds proprioception — each stage feels its own state without explicit lookups. |
| **Call site** | Every pipeline stage transition at `pipeline.py:50-190` — each `upstream→downstream` connection becomes a `CreativeJoint` |

**Implementation:**
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Proprioception:
    position: Optional[Any] = None
    velocity: float = 0.0          # Rate of change (positive = drifting away, negative = returning)
    tension: float = 0.5           # 0.0 = slack, 1.0 = max tension
    confidence: float = 0.9        # How sure we are about our position

    def decay(self, factor: float = 0.98) -> None:
        self.confidence *= factor
        self.velocity *= 0.95      # Velocity decays naturally


class CreativeJoint:
    """Connects two pipeline stages with degrees of freedom.
    Flexes under high tension instead of breaking."""

    def __init__(self, upstream: str, downstream: str):
        self.upstream = upstream
        self.downstream = downstream
        self.dof = ["flex", "extend", "rotate"]  # Degrees of freedom
        self.tension = 0.5
        self.proprioception = Proprioception()

    def transmit(self, signal: dict, context: dict) -> dict:
        current_tension = self.proprioception.tension
        if current_tension > 0.8:
            # High tension: flex — allow downstream to interpret creatively within bounds
            return self._flex(signal, drift_amount=current_tension)
        # Low tension: direct pass-through
        return self._direct(signal)

    def _direct(self, signal: dict) -> dict:
        return signal

    def _flex(self, signal: dict, drift_amount: float) -> dict:
        """Allow downstream to reinterpret signal within drift_amount tolerance.
        Signal values are preserved; downstream applies ±drift_amount interpretation."""
        flexed = dict(signal)
        flexed["_joint_flex"] = round(drift_amount, 2)
        flexed["_joint_origin"] = self.upstream
        return flexed


class CreativeCerebellum:
    """Handles automatic, unconscious coordination — creative proprioception.
    Like the cerebellum in motor control, it manages timing and coordination without conscious effort."""

    def __init__(self):
        self.body_map: dict[str, Proprioception] = {
            "camera": Proprioception(
                position={"x": 1.7, "y": 0.0, "z": 5.0, "angle": "eye level"},
                confidence=0.9,
            ),
            "character_001": Proprioception(
                position={"x": 0.3, "y": 0.0, "z": 0.0, "pose": "standing, facing right"},
                confidence=0.95,
            ),
        }

    def update(self, frame_spec: dict) -> None:
        for element, sense in self.body_map.items():
            sense.decay(0.98)

    def sense(self, element: str) -> Proprioception:
        """Feel where the element should be without looking it up."""
        return self.body_map.get(element, Proprioception(confidence=0.0))

    def correct(self, frame_spec: dict) -> dict:
        """Before generating, correct any proprioceptive drift."""
        for element, sense in self.body_map.items():
            if sense.confidence > 0.8 and not self._is_explicit_change(frame_spec, element):
                frame_spec = self._restore_proprioception(frame_spec, element)
        return frame_spec

    def _is_explicit_change(self, frame_spec: dict, element: str) -> bool:
        return f"change_{element}" in frame_spec.get("director_notes", [])

    def _restore_proprioception(self, frame_spec: dict, element: str) -> dict:
        sense = self.body_map[element]
        if sense.position:
            frame_spec[f"_{element}_proprioception"] = sense.position
        return frame_spec
```

**Tests** (`tests/test_biomechanics.py`):
1. `CreativeJoint("writer", "director").transmit({"scene": "sunset"}, {"tension": 0.3})` → returns signal unmodified (direct pass)
2. `CreativeJoint("writer", "director").transmit({"scene": "sunset"}, {"tension": 0.9})` → returns signal with `_joint_flex=0.9` and `_joint_origin="writer"`
3. `CreativeCerebellum.sense("camera")` → returns Proprioception with position and confidence=0.9
4. `CreativeCerebellum.sense("nonexistent")` → returns Proprioception with confidence=0.0
5. `Proprioception.decay(0.5)` 2x → confidence goes from 0.9 to 0.9*0.98*0.98 = ~0.86

---

### Domain 6: Philosophy — Death of the Director

**Principle:** Meaning is created at the point of reception, not transmission (Barthes, Derrida). The Director doesn't decide — they generate multiple interpretations. The model (audience) determines which meaning emerges from the interpretation space.

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/engines/philosophy.py` |
| **Class** | `DeathOfTheDirector`, `RiverContinuity`, `InterpretationSpace` |
| **Interface** | `DeathOfTheDirector.run(script: str, intent: str, dna: CharacterDNA) -> InterpretationSpace` |
| | `RiverContinuity.register_frame(frame_spec: FrameSpec) -> None` |
| | `RiverContinuity.what_should_be_identical(frame_number: int) -> str` |
| **Behavioral change** | Replaces single Director interpretation with `NUM_INTERPRETATIONS` alternative readings. The model chooses which to realize. Identity is maintained through difference — RiverContinuity explicitly states what changed and commands "EVERYTHING ELSE MUST BE IDENTICAL." |
| **Call site** | `Pipeline.run()` at `pipeline.py:120` — after Screenwriter produces script, before Cinematographer produces CameraSpec |

**Implementation:**
```python
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any, Optional

NUM_INTERPRETATIONS = 3


@dataclass
class Interpretation:
    reading: str
    emotional_tone: str
    visual_approach: str
    conflicts: list[str] = field(default_factory=list)


@dataclass
class InterpretationSpace:
    readings: list[Interpretation]
    conflicts: list[str] = field(default_factory=list)
    audience_vector: Optional[str] = None


class DeathOfTheDirector:
    """The Director doesn't decide — they generate multiple interpretations.
    The model (audience) determines which meaning emerges."""

    def run(self, script: str, intent: str, dna: str, characters: list[str]) -> InterpretationSpace:
        interpretations = []
        for i in range(NUM_INTERPRETATIONS):
            reading = self._alternative_reading(script, intent, seed=i)
            interpretations.append(reading)

        conflicts = self._find_conflicts(interpretations)
        return InterpretationSpace(readings=interpretations, conflicts=conflicts)

    def _alternative_reading(self, script: str, intent: str, seed: int) -> Interpretation:
        rng = random.Random(hash(script + intent + str(seed)))
        tones = ["melancholic", "triumphant", "ambiguous", "intimate", "epic"]
        approaches = ["close character study", "wide environmental", "dynamic action", "static observation"]
        return Interpretation(
            reading=f"Interpretation {seed + 1}: {script[:60]}...",
            emotional_tone=rng.choice(tones),
            visual_approach=rng.choice(approaches),
        )

    def _find_conflicts(self, interpretations: list[Interpretation]) -> list[str]:
        conflicts = []
        tones = [i.emotional_tone for i in interpretations]
        if len(set(tones)) < len(tones):
            conflicts.append("Duplicate emotional tones across interpretations")
        return conflicts


@dataclass
class FrameChange:
    field: str
    from_value: Any
    to_value: Any


class RiverContinuity:
    """Each frame is a different step into the same river.
    Identity is maintained through DIFFERENCE — each frame differs from the
    previous in exactly one way, and is identical in all others."""

    def __init__(self):
        self.ancestors: list[dict] = []
        self.genealogy: list[list[FrameChange]] = []

    def register_frame(self, frame_spec: dict) -> None:
        if self.ancestors:
            previous = self.ancestors[-1]
            changes = self._diff(previous, frame_spec)
            self.genealogy.append(changes)
        self.ancestors.append(frame_spec)

    def what_should_be_identical(self, frame_number: int) -> str:
        if not self.genealogy or frame_number < 2:
            return "This is the establishing frame. No prior continuity."
        changes = self.genealogy[frame_number - 2]
        change_list = ", ".join(f"{c.field}: {c.from_value} → {c.to_value}" for c in changes) if changes else "nothing"
        return (
            f"CONTINUITY: Frame {frame_number} continues from Frame "
            f"{frame_number - 1}. Only the following changed: {change_list}. "
            f"EVERYTHING ELSE MUST BE IDENTICAL TO FRAME {frame_number - 1}."
        )

    def _diff(self, a: dict, b: dict) -> list[FrameChange]:
        changes = []
        all_keys = set(a.keys()) | set(b.keys())
        for key in all_keys:
            if a.get(key) != b.get(key):
                changes.append(FrameChange(key, a.get(key), b.get(key)))
        return changes
```

**Tests** (`tests/test_philosophy.py`):
1. `DeathOfTheDirector.run("A man walks into a bar", "comedy", "DNA", ["Man"])` → returns InterpretationSpace with exactly 3 interpretations
2. `RiverContinuity.register_frame({"action": "walk"})` + second frame `{"action": "run"}` → genealogy contains 1 FrameChange with field="action"
3. `RiverContinuity.what_should_be_identical(1)` → "This is the establishing frame..."
4. `RiverContinuity.what_should_be_identical(2)` → contains "Only the following changed: action: walk → run"

---

### Domain 7: Psychology — Object Permanence & World Schema

**Principle:** Piaget's object permanence — the engine doesn't know objects continue to exist when out of sight. The WorldSchema is a mental model of the world that persists across frames. Every element has a "continues to exist" flag embedded in every prompt.

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/engines/world.py` |
| **Class** | `WorldSchema`, `CharacterShema`, `PropSchema`, `EnvironmentSchema` |
| **Interface** | `WorldSchema.persist(frame_spec: FrameSpec, frame_number: int) -> str` |
| | `WorldSchema.get_element(element_id: str) -> Optional[BaseSchema]` |
| | `WorldSchema.update(frame_spec: FrameSpec) -> None` |
| **Behavioral change** | Adds `[PERSISTS: ...]` clauses to every prompt — objects continue to exist off-screen. The model never needs to infer whether a prop vanished — it's explicitly told it persists. |
| **Call site** | `Pipeline.compile()` at `pipeline.py:235` — injected into prompt before sending to Generator, after ContinuityVerdict |

**Implementation:**
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CharacterSchema:
    character_id: str
    name: str
    identity: str
    continues_to_exist: bool = True
    last_seen_frame: int = 0
    last_position: str = ""
    last_action: str = ""


@dataclass
class PropSchema:
    prop_id: str
    description: str
    continues_to_exist: bool = True
    carried_by: Optional[str] = None
    last_seen_frame: int = 0


@dataclass
class EnvironmentSchema:
    setting: str
    invariants: dict[str, str] = field(default_factory=dict)


class WorldSchema:
    """A mental model of the world that persists across frames."""

    def __init__(self):
        self.schema: dict[str, dict] = {
            "characters": {
                "001": CharacterSchema(
                    character_id="001",
                    name="Elias Voss",
                    identity="weathered brown leather coat, gaunt face, wooden staff",
                    last_seen_frame=1, last_position="center frame", last_action="walking",
                ),
            },
            "props": {
                "wooden_staff": PropSchema(
                    prop_id="wooden_staff",
                    description="weathered wooden staff, taller than the man",
                    carried_by="001", last_seen_frame=1,
                ),
            },
            "environment": EnvironmentSchema(
                setting="Nalanda monastery ruins",
                invariants={"architecture": "crumbling red sandstone",
                           "time_period": "medieval India",
                           "weather": "dry", "light": "harsh noon sun"},
            ),
        }

    def persist(self, frame_spec: dict, frame_number: int) -> str:
        """Generate persistence clauses — what continues to exist off-screen."""
        notes = []
        for char_id, schema in self.schema["characters"].items():
            if not schema.continues_to_exist:
                continue
            char_present = schema.name in str(frame_spec.get("characters_in_frame", []))
            if not char_present:
                notes.append(
                    f"[PERSISTS: {schema.name} (wearing {schema.identity}) is nearby, "
                    f"last seen {schema.last_position} {schema.last_action}]"
                )
        for prop_id, schema in self.schema["props"].items():
            if not schema.continues_to_exist:
                continue
            prop_present = schema.description in str(frame_spec)
            if not prop_present:
                notes.append(
                    f"[PERSISTS: {schema.description} (carried by {schema.carried_by}) "
                    f"last seen frame {schema.last_seen_frame}]"
                )
        return "\n".join(notes)

    def get_element(self, element_id: str) -> Optional[object]:
        for category in self.schema.values():
            if isinstance(category, dict) and element_id in category:
                return category[element_id]
        return None

    def update(self, frame_spec: dict) -> None:
        for char_id, schema in self.schema["characters"].items():
            if char_id in str(frame_spec):
                schema.last_seen_frame += 1
```

**Tests** (`tests/test_world.py`):
1. `WorldSchema.persist({"characters_in_frame": []}, 2)` → contains `[PERSISTS: Elias Voss...]`
2. `WorldSchema.get_element("001")` → returns CharacterSchema with name="Elias Voss"
3. `WorldSchema.get_element("nonexistent")` → returns None
4. `WorldSchema.update({"001": "visible"})` → CharacterSchema.last_seen_frame increments

---

### Domain 8: Medicine — Homeostatic Continuity Regulation

**Principle:** The body maintains stable internal conditions despite external changes. When something drifts, it CORRECTS it. The ContinuityHomeostat maintains set points for visual properties and applies corrective feedback when drift is detected.

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/engines/homeostat.py` |
| **Class** | `ContinuityHomeostat`, `HemodynamicMonitor`, `SetPoint` |
| **Interface** | `ContinuityHomeostat.establish_set_points(frame_specs: list[FrameSpec]) -> None` |
| | `ContinuityHomeostat.measure_and_correct(frame_spec: FrameSpec) -> FrameSpec` |
| | `HemodynamicMonitor.autoregulate(task_type: str, available: list[str]) -> str` |
| **Behavioral change** | Replaces the absence of drift detection with a homeostatic loop: measure → detect deviation → correct. Set points established from initial frames. Identity drift gets aggressive correction (tolerance=0), artistic choices get infinite tolerance. |
| **Call site** | `Pipeline.run()` at `pipeline.py:160` — called after every Cinematographer/Gaffer output, before Compiler |

**Implementation:**
```python
from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SetPoint:
    field_name: str
    value: Any
    tolerance: float          # 0.0 = zero tolerance, inf = no constraint
    correction_strength: float  # How aggressively to correct (0.0-10.0)


@dataclass
class DriftCorrection:
    field: str
    expected: Any
    measured: Any
    correction: str


class ContinuityHomeostat:
    """Maintains creative homeostasis across frames. Detects drift and applies corrective feedback."""

    def __init__(self):
        self.set_points: dict[str, SetPoint] = {}
        self.correction_history: list[DriftCorrection] = []
        self.segment_counter: int = 0

    def establish_set_points(self, frame_specs: list[dict]) -> None:
        if not frame_specs:
            return
        # Character identity: zero tolerance, aggressive correction
        char_identity = frame_specs[0].get("character_identity", "")
        if char_identity:
            self.set_points["character_identity"] = SetPoint(
                field_name="character_identity", value=char_identity,
                tolerance=0.0, correction_strength=10.0,
            )
        # Color temperature: moderate tolerance, gentle correction
        temps = [s.get("color_temperature_k") for s in frame_specs[:3] if s.get("color_temperature_k")]
        if temps:
            self.set_points["color_temperature"] = SetPoint(
                field_name="color_temperature", value=sum(temps) / len(temps),
                tolerance=200, correction_strength=0.5,
            )
        # Shot size: no homeostatic constraint (artistic freedom)
        self.set_points["shot_size"] = SetPoint(
            field_name="shot_size", value="medium",
            tolerance=float('inf'), correction_strength=0.0,
        )

    def measure_and_correct(self, frame_spec: dict) -> dict:
        self.segment_counter += 1
        corrections: list[str] = []

        for prop_name, set_point in self.set_points.items():
            measured = frame_spec.get(prop_name)
            if measured is None:
                continue
            deviation = self._deviation(measured, set_point.value)
            if abs(deviation) > set_point.tolerance and self.segment_counter > 2:
                correction_text = f"[CORRECTION] {prop_name}: '{measured}' → '{set_point.value}'"
                corrections.append(correction_text)
                self.correction_history.append(DriftCorrection(
                    field=prop_name, expected=set_point.value,
                    measured=measured, correction=correction_text,
                ))
                # Apply correction to frame_spec
                if set_point.correction_strength > 0:
                    frame_spec[prop_name] = set_point.value

        frame_spec["_corrections"] = corrections
        return frame_spec

    def _deviation(self, measured: Any, expected: Any) -> float:
        if isinstance(measured, (int, float)) and isinstance(expected, (int, float)):
            return measured - expected
        return 0.0 if measured == expected else 1.0


class HemodynamicMonitor:
    """Cardiovascular physiology: each engine autoregulates its own 'blood flow' (model load).
    Vasodilation = high demand → more capable model. Vasoconstriction = low demand → faster model."""

    MODEL_HEMODYNAMICS: dict[str, dict] = {
        "gemma-4-12b": {"pressure": 9.5, "flow_tps": 0.7, "metabolic_cost": 7.4},
        "phi-4-mini": {"pressure": 7.0, "flow_tps": 14.3, "metabolic_cost": 2.5},
        "ornith-9b": {"pressure": 8.5, "flow_tps": 0.3, "metabolic_cost": 5.6},
        "smollm-3b": {"pressure": 3.0, "flow_tps": 16.7, "metabolic_cost": 1.9},
    }
    TASK_RESISTANCE: dict[str, float] = {
        "writer": 0.7, "dramaturg": 0.8, "film_dna": 0.1, "director": 0.7,
        "character": 0.2, "symbolism": 0.8, "compiler": 0.3,
    }
    MIN_QUALITY_THRESHOLD = 0.3

    def autoregulate(self, task_type: str, available_models: list[str]) -> str:
        """Flow = Pressure / Resistance. Pick model with sufficient pressure, lowest cost."""
        required_pressure = self.TASK_RESISTANCE.get(task_type, 0.5) * 10
        candidates = [
            m for m in available_models if m in self.MODEL_HEMODYNAMICS
            and self.MODEL_HEMODYNAMICS[m]["pressure"] >= required_pressure
        ]
        if not candidates:
            candidates = available_models
        return min(candidates, key=lambda m: self.MODEL_HEMODYNAMICS[m]["metabolic_cost"])

    def is_ischemic(self, task_type: str, model_key: str) -> bool:
        """Check if the model has enough 'blood pressure' for this task."""
        required = self.TASK_RESISTANCE.get(task_type, 0.5) * 10
        available = self.MODEL_HEMODYNAMICS.get(model_key, {}).get("pressure", 0.0)
        return available < required
```

**Tests** (`tests/test_homeostat.py`):
1. `ContinuityHomeostat.establish_set_points([{"character_identity": "Elias", "color_temperature_k": 5600}])` → creates 3 set points
2. `ContinuityHomeostat.measure_and_correct({"character_identity": "Elias"})` with segment=1 → no correction (before segment 3)
3. `ContinuityHomeostat.measure_and_correct({"character_identity": "John"})` with segment=3 → injects `[CORRECTION] character_identity: 'John' → 'Elias'`
4. `HemodynamicMonitor.autoregulate("compiler", ["phi-4-mini", "gemma-4-12b"])` → returns "gemma-4-12b" (higher pressure needed)
5. `HemodynamicMonitor.is_ischemic("compiler", "smollm-3b")` → returns True (pressure too low)

---

### Domain 9: Economics — VCG Auction Theory

**Principle:** Optimal allocation requires truthful reporting of preferences. The winner pays the second-highest bid, so everyone's dominant strategy is to bid truthfully. Models bid on tasks based on comparative advantage.

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/engines/auction.py` |
| **Class** | `TaskAuction`, `ContinuityContract` |
| **Interface** | `TaskAuction.bid(model: str, task_type: str, is_loaded: bool) -> float` |
| | `TaskAuction.allocate(task_type: str, loaded_models: list[str]) -> tuple[str, float]` |
| | `ContinuityContract.propose(frame_spec: FrameSpec, frame_number: int) -> Contract` |
| | `ContinuityContract.verify(frame_number: int, generated_prompt: str) -> list[Breach]` |
| **Behavioral change** | Replaces hard-coded model assignment (`ChainConfig` at `engine.py:52`) with VCG auction where winner pays second price. ContinuityContract locks frame properties into binding contracts with breach penalties. |
| **Call site** | `Pipeline.run()` at `pipeline.py:50` — before ANY stage executes, models bid on all tasks in the current run |

**Implementation:**
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional

MODEL_CAPABILITIES: dict[str, dict] = {
    "gemma-4-12b": {
        "reliability": 1.0, "speed_tps": 0.7, "max_complexity": "extreme",
        "task_scores": {"writer": 0.95, "dramaturg": 0.90, "compiler": 0.95,
                       "film_dna": 0.80, "character": 0.80, "director": 0.90},
    },
    "phi-4-mini": {
        "reliability": 1.0, "speed_tps": 14.3, "max_complexity": "moderate",
        "task_scores": {"writer": 0.30, "film_dna": 0.95, "character": 0.95,
                       "compiler": 0.40, "director": 0.30},
    },
    "ornith-9b": {
        "reliability": 1.0, "speed_tps": 0.3, "max_complexity": "high",
        "task_scores": {"dramaturg": 0.95, "symbolism": 0.95, "writer": 0.70,
                       "director": 0.75},
    },
    "smollm-3b": {
        "reliability": 1.0, "speed_tps": 16.7, "max_complexity": "low",
        "task_scores": {"film_dna": 0.60, "character": 0.50},
    },
}


class TaskAuction:
    """VCG auction: models bid their true (speed × quality) for each task.
    Winner pays SECOND lowest bid — ensures truthful bidding is the dominant strategy."""

    LOADING_PENALTIES = {"ornith-9b": 5.0, "phi-4-mini": 1.5, "gemma-4-12b": 3.0, "smollm-3b": 0.5}

    def bid(self, model: str, task_type: str, is_loaded: bool) -> float:
        """Truthful bid: lower is better. Incorporates speed, task score, and loading penalty."""
        cap = MODEL_CAPABILITIES.get(model)
        if not cap:
            return float('inf')
        task_score = cap["task_scores"].get(task_type, 0.0)
        if task_score < 0.01:
            return float('inf')
        base_bid = (1.0 / max(cap["speed_tps"], 0.01)) * (1.0 + (1.0 - task_score) ** 2)
        loading_penalty = 0.0 if is_loaded else self.LOADING_PENALTIES.get(model, 0.0)
        return (base_bid + loading_penalty) / cap["reliability"]

    def allocate(self, task_type: str, loaded_models: list[str]) -> tuple[str, float]:
        """Run the auction. Returns (winner_model_key, second_price)."""
        bids = [(self.bid(m, task_type, m in loaded_models), m) for m in MODEL_CAPABILITIES]
        bids = [(b, m) for b, m in bids if b != float('inf')]
        bids.sort()
        if not bids:
            raise RuntimeError(f"No models available for task '{task_type}'")
        return bids[0][1], bids[1][0] if len(bids) > 1 else bids[0][0]

    def market_clear(self, tasks: list[str], loaded_models: list[str]) -> dict[str, tuple[str, float]]:
        """Allocate all tasks. Returns {task_type: (model, price)}."""
        allocations = {}
        for task in tasks:
            model, price = self.allocate(task, loaded_models)
            allocations[task] = (model, price)
        return allocations


@dataclass
class Clause:
    field: str
    template: str
    satisfied: bool = False

    def satisfied_by(self, prompt: str) -> bool:
        return self.template in prompt


@dataclass
class Contract:
    frame_number: int
    clauses: list[Clause]
    breach_penalty: float
    signatories: list[str]


@dataclass
class Breach:
    clause: Clause
    penalty: float
    fix: str


class ContinuityContract:
    """A contract signed by every frame locking in properties established by previous frames."""

    def __init__(self):
        self.active_contracts: list[Contract] = []

    def propose(self, frame_spec: dict, frame_number: int) -> Contract:
        clauses = [
            Clause("character_identity", str(frame_spec.get("character_identity", ""))),
            Clause("camera_model", str(frame_spec.get("camera_body", ""))),
            Clause("lens", str(frame_spec.get("lens", ""))),
        ]
        contract = Contract(
            frame_number=frame_number,
            clauses=[c for c in clauses if c.template],
            breach_penalty=self._compute_penalty(frame_number),
            signatories=["Cinematographer", "Gaffer", "ProductionDesigner"],
        )
        self.active_contracts.append(contract)
        return contract

    def verify(self, frame_number: int, generated_prompt: str) -> list[Breach]:
        if frame_number < 2 or len(self.active_contracts) < 2:
            return []
        previous_contract = self.active_contracts[frame_number - 2]
        breaches = []
        for clause in previous_contract.clauses:
            if not clause.satisfied_by(generated_prompt):
                breaches.append(Breach(
                    clause=clause, penalty=previous_contract.breach_penalty,
                    fix=f"REINFORCE: {clause.template}",
                ))
        return breaches

    def enforce(self, next_frame_spec: dict, breaches: list[Breach]) -> dict:
        reinforcements = next_frame_spec.get("continuity_reinforcements", [])
        for breach in breaches:
            reinforcements.append(f"[CONTINUITY LOCK: {breach.clause.template}]")
        next_frame_spec["continuity_reinforcements"] = reinforcements
        return next_frame_spec

    def _compute_penalty(self, frame_number: int) -> float:
        # Later frames have higher breach penalties
        return min(1.0 + frame_number * 0.1, 10.0)
```

**Tests** (`tests/test_auction.py`):
1. `TaskAuction.bid("phi-4-mini", "film_dna", is_loaded=True)` → lower than `"gemma-4-12b"` for "film_dna" (Phi wins on fast analysis tasks)
2. `TaskAuction.bid("phi-4-mini", "compiler", is_loaded=True)` → higher than `"gemma-4-12b"` (Gemma wins on compiler)
3. `TaskAuction.allocate("film_dna", ["phi-4-mini"])` → winner="phi-4-mini"
4. `ContinuityContract.propose({"character_identity": "Elias", "camera_body": "Alexa 35"}, 1)` → Contract with 2 clauses
5. `ContinuityContract.verify(2, "some prompt without Elias")` → Breach for character_identity clause

---

### Domain 10: Cryptography — Merkle Continuity & Provenance

**Principle:** The identity of the entire sequence is captured in a single hash. Any drift changes the root. Frame-to-frame integrity is verified through cryptographic hashing.

**Force-Down**:

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/engines/merkle.py` |
| **Class** | `MerkleContinuity`, `IntegrityViolation` |
| **Interface** | `MerkleContinuity.commit(frame_spec: FrameSpec, frame_number: int) -> str` |
| | `MerkleContinuity.verify_chain() -> list[IntegrityViolation]` |
| | `MerkleContinuity.provenance(field: str) -> list[tuple[int, Any]]` |
| **Behavioral change** | Replaces the absence of cross-frame identity verification with a cryptographic commitment chain. Each frame commits to the previous frame's hash. Any drift is detected as a chain violation. Field provenance is traceable — you can ask "when did this field last change?" |
| **Call site** | `Pipeline.run()` at `pipeline.py:170` — called after every frame generation, before the next frame starts |

**Implementation:**
```python
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntegrityViolation:
    frame: int
    violation_type: str      # "hash_mismatch" | "continuity_breach"
    field: str = ""
    detail: str = ""


class MerkleContinuity:
    """Immutable chain of continuity commitments. Each frame commits to previous identity."""

    def __init__(self):
        self.chain: list[dict] = []
        self.state: dict = {}

    def commit(self, frame_spec: dict, frame_number: int) -> str:
        block = {
            "frame": frame_number,
            "character_identity": frame_spec.get("character_identity", ""),
            "camera_model": frame_spec.get("camera_body", ""),
            "lens": frame_spec.get("lens", ""),
            "environment_setting": frame_spec.get("setting", ""),
            "previous_hash": self._last_hash(),
        }
        block_bytes = json.dumps(block, sort_keys=True).encode()
        block_hash = hashlib.sha256(block_bytes).hexdigest()
        block["hash"] = block_hash
        self.chain.append(block)
        self.state = block
        return block_hash

    def verify_chain(self) -> list[IntegrityViolation]:
        violations = []
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Recompute previous block's hash to verify linkage
            prev_block = {k: v for k, v in previous.items() if k != "hash"}
            expected_prev_hash = hashlib.sha256(json.dumps(prev_block, sort_keys=True).encode()).hexdigest()
            if current["previous_hash"] != expected_prev_hash:
                violations.append(IntegrityViolation(
                    frame=current["frame"], violation_type="hash_mismatch",
                    detail=f"expected {expected_prev_hash[:12]}... but got {current['previous_hash'][:12]}...",
                ))

            # Check continuity-critical fields
            for field in ["character_identity", "camera_model", "lens"]:
                if current.get(field) and previous.get(field) and current[field] != previous[field]:
                    violations.append(IntegrityViolation(
                        frame=current["frame"], violation_type="continuity_breach",
                        field=field,
                        detail=f"'{field}' changed from '{previous[field]}' to '{current[field]}'",
                    ))
        return violations

    def provenance(self, field: str) -> list[tuple[int, Any]]:
        """Return (frame_number, value) for every frame where this field changed."""
        history = []
        for block in self.chain:
            value = block.get(field)
            if not history or history[-1][1] != value:
                history.append((block["frame"], value))
        return history

    def _last_hash(self) -> str:
        return self.chain[-1]["hash"] if self.chain else "GENESIS"

    def root_hash(self) -> str:
        return self.chain[-1]["hash"] if self.chain else "EMPTY"
```

**Tests** (`tests/test_merkle.py`):
1. `MerkleContinuity.commit({"character_identity": "Elias", "camera_body": "Alexa"}, 1)` → returns a 64-char hex hash
2. Two identical commits → `verify_chain()` returns 0 violations
3. Two commits with changed `character_identity` → `verify_chain()` returns 1 violation with type="continuity_breach" and field="character_identity"
4. `MerkleContinuity.provenance("character_identity")` → returns [(1, "Elias"), (2, "John")] showing every change point
5. `root_hash()` on empty chain → returns "EMPTY"
## 5. Domain Interaction Matrix (Expanded)

The 9 domains above are not independent. This expanded matrix documents every pairwise relationship, including contradictions that were implicit in the original:

| Domain A | Domain B | Relationship | Resolution / Synthesis |
|:---|:---|:---|:---|
| Biology (Mycelial) | Economics (Auctions) | **Compatible** — Distributed sensing maps to distributed bidding. Both replace central authority with local decision-making. | Unify: `CreativeNode.respond()` feeds into `TaskAuction.bid()` — nodes that sense strong signals generate higher bids. |
| Physics (Thermodynamics) | Chemistry (Catalysis) | **Compatible** — Maxwell's Demon sorts information; Catalytic Templates lock sorted information into stable slots. | Unify: `MaxwellCompiler.sort()` produces labeled dimensions that `RibosomeCompiler.translate()` fills verbatim. |
| Biomechanics (Joints) | Medicine (Homeostat) | **Compatible** — Joints flex under tension; Homeostat corrects when flex exceeds tolerance. These are the same system at different thresholds. | Unify: `CreativeJoint.transmit()` with `drift_amount` feeds into `ContinuityHomeostat.measure_and_correct()` — low drift = pass through, high drift = correction. |
| Philosophy (Death of Director) | Cryptography (Merkle) | **CONTRADICTORY** — Domain 6 asserts meaning is created at reception (no canonical interpretation). Domain 10 asserts a canonical identity chain exists and drift from it is a violation. If meaning is created at reception, there is no "truth-chain" to deviate from. | **Resolution**: The Merkle chain records *socially-verifiable* identity features (what external observers can check). The interpretation space governs *subjective* meaning-making (what the audience experiences). These operate at different levels. A character's coat color is socially verifiable (Merkle chain). The emotional tone of the scene is subjective (interpretation space). The contradiction resolves when you distinguish *facts about the world* from *meanings about the world*. |
| Psychology (Object Permanence) | Cryptography (Merkle) | **Compatible** — WorldSchema says objects persist; Merkle chain verifies their persistence across frames. | Unify: `MerkleContinuity.commit()` validates that `WorldSchema.persist()` clauses survived the generator. |
| Medicine (Homeostat) | Economics (Contracts) | **Compatible** — Homeostat corrects drift; ContinuityContract locks drift corrections into binding agreements. | Unify: `ContinuityHomeostat.correction_history` feeds into `ContinuityContract.propose()` — each correction becomes a contract clause for subsequent frames. |
| Biology (ZoneManager) | Physics (Entropy) | **Compatible** — ZoneManager assigns models to zones; EntropyAuditor measures whether the assignment preserved information. | Unify: `ZoneManager.assign()` returns a model; `EntropyAuditor.measure()` checks if that model preserved the structured input. |
| Biomechanics (Cerebellum) | Philosophy (RiverContinuity) | **Compatible** — CreativeCerebellum tracks proprioceptive state; RiverContinuity tracks what changed between frames. Both maintain identity through difference-tracking. | Unify: `CreativeCerebellum.correct()` uses `RiverContinuity.what_should_be_identical()` as its reference frame for correction. |

### Unresolved Pairings (Requires Empirical Tuning)

| Domain A | Domain B | Gap |
|:---|:---|:---|
| Chemistry (Catalytic Templates) | Psychology (WorldSchema) | Templates define *how* fields are rendered; WorldSchema defines *which* fields persist. No current mechanism ensures template slots align with persistence requirements. |
| Philosophy (Death of Director) | Medicine (Homeostat) | If multiple interpretations are equally valid, which set point does the homeostat use? The protocol currently assumes one set point per field, but multiple interpretations would produce multiple competing set points. |

---

## 5b. Domain -1: The Negative Domain — Parsimony (Occam's Razor)

**Principle:** The simplest pipeline that works is superior to any protocol-enriched pipeline. Every added domain, every new class, every additional abstraction layer is a liability — a potential point of failure, a maintenance burden, a cognitive load on the next developer. The burden of proof is on the protocol to demonstrate that its complexity is justified by measurable improvement over a simpler baseline. This domain must exist because the protocol has no built-in brake on its own expansion.

**Force-Down:**

| Step | Artifact |
|:---|:---|
| **File** | `src/cinema/audit/parsimony.py` |
| **Class** | `ParsimonyAuditor` |
| **Interface** | `ParsimonyAuditor.audit(modules: list[ModuleSpec]) -> ParsimonyScore` |
| | `ParsimonyAuditor.compare(baseline: PipelineResult, protocol_result: PipelineResult) -> Delta` |
| **Behavior** | Before any new domain or module is added to the pipeline, the ParsimonyAuditor checks: (1) Is the IRR improvement ≥ 5 percentage points over the current baseline? (2) Is the latency overhead ≤ 20% of current baseline? (3) Does the module have >80% test coverage? (4) Can the module be removed without breaking any other module? Any module that fails all four gates is rejected as insufficiently justified complexity. |
| **Call site** | `Pipeline.__init__()` at `pipeline.py:20` — before any module is registered, the ParsimonyAuditor evaluates all registered modules |
| **Tests** (`tests/test_parsimony.py`): 1. Module with IRR improvement <5% → rejected. 2. Module with >20% latency overhead → rejected. 3. Module that passes all gates → accepted. 4. Remove a module; verify no other module breaks. |

### Why this domain is necessary

Without a Negative Domain, the protocol has a systematic expansion bias: every domain that gets added stays forever, regardless of whether it earns its keep. The protocol's own governance — the Specificity Engine, the Force-Down Protocol, the Self-Check — are all *enabling* mechanisms. None of them *prune*. The Negative Domain is the pruning mechanism. It votes NAY on any proposed expansion that cannot demonstrate >5% IRR improvement or ≤20% latency overhead.

**Vote**: NAY on any new module that fails the parsimony gates. YEA on simplicity. ABSTAIN on existing modules (grandfathered in).

---

## 5c. Falsification Conditions

Each domain states explicitly what empirical finding would force its explanation to be abandoned or substantially revised:

| Domain | Falsification Condition | Current Status | Severity |
|:---|:---|:---|:---|
| Nature (Simultaneous) | A program that satisfies all 10 domain constraints simultaneously but performs *worse* on average than a baseline that optimizes for one constraint at a time, across >100 diverse tasks. | **Testable** via A/B comparison — any pipeline that enforces EquilibriumChecker vs pipeline that checks domains sequentially. | Low |
| Biology (Mycelial) | A pipeline where distributed routing produces *lower* quality than a single monolithic compiler, controlling for model capability. | **Not tested.** Requires A/B comparison. | Medium |
| Physics (Thermodynamics) | A reliable operational measure of IRR that does NOT correlate with compiler temperature. | **Cannot be falsified.** No measurement protocol exists for IRR independent of the claims it supports. The `measure()` function uses string-matching which is fragile. | High |
| Chemistry (Catalysis) | A translation table that produces IRR < 1.0 (field values lost despite one-to-one mapping). | **Should be falsifiable.** If `TRANSLATION_TABLE` covers all fields, IRR must be 1.0. Any deviation reveals an untranslated field. | Low |
| Biomechanics (Joints) | A pipeline where adding flex joints reduces, rather than improves, output quality across multiple tasks. | **Not tested.** No baseline comparison exists. | Medium |
| Philosophy (Death of Director) | A case where a single Director interpretation consistently outperforms multiple interpretations on quality metrics. | **Testable** via A/B comparison. If single-interpretation pipelines win on consistency metrics, the protocol's core claim is weakened. | Medium |
| Psychology (WorldSchema) | A generation where explicit `[PERSISTS]` clauses do NOT improve object permanence over an equivalent prompt without them. | **Testable** via A/B comparison with and without `[PERSISTS]` clauses. | Low |
| Medicine (Homeostat) | Independent measurement of set points (before observing drift events) that does not predict which corrections the homeostat applies. | **Not tested.** Requires longitudinal set-point measurement protocol. Currently set points are established from the same data used to detect drift — circular. | High |
| Economics (Auctions) | A task allocation where VCG auction selects a *worse* model than random assignment, controlling for task difficulty. | **Testable** via simulation. Requires empirical model capability scores. | Low |
| Cryptography (Merkle) | A frame sequence where Merkle chain verification detects a "continuity breach" that human evaluators unanimously consider non-problematic. | **Testable.** Would indicate the chain is too sensitive. Already partially addressed: threshold tuning is in Open Questions. | Medium |
| Metallurgy (Substrate) | A program whose runtime is better predicted by abstract algorithmic complexity alone than by a substrate-aware model that accounts for wire delay, thermal state, and material conductivity. | **Testable.** Requires benchmark with known substrate parameters vs abstract complexity model. | Low |
 
### Protocol-Level Falsification

The protocol as a whole would be falsified if: an AI creative pipeline using *none* of the domains achieves equivalent or better output quality than a pipeline using *all* domains, as measured by blind human evaluation across at least 100 generation tasks.

---

## 5d. Confidence and Calibration

The original protocol presents all domains with equal authority. This section calibrates each domain's epistemic status — distinguishing well-established mechanisms from speculative analogies.

| Domain | Status | Confidence | Rationale |
|:---|:---|:---|:---|
| Nature (Simultaneous) | **Structural axiom** | High | This is not a mechanism — it is the observation that nature never drops constraints. The axiom is verified by the continued existence of every physical object. If an artifact fails any physical constraint, it ceases to exist. Code has no such enforcement, which is why it breaks. The axiom is unfalsifiable in principle, but its *usefulness* is testable via A/B comparison. |
| Biology (Mycelial) | **Established mechanism** | High | Distributed routing is a known engineering pattern. The mycelial analogy is illustrative but the mechanism is sound. |
| Physics (Thermodynamics) | **Speculative analogy** | Low | The entropy framework is metaphorical. No operational definition of "social entropy" exists. The `EntropyAuditor` is useful as a monitoring tool but does not derive its thresholds from thermodynamics. |
| Chemistry (Catalysis) | **Established mechanism** | High | Translation tables are a well-known pattern. RibosomeCompiler is a direct implementation of lossless template filling. |
| Biomechanics (Joints) | **Analogous mechanism** | Medium | Flex joints are a reasonable pattern but the specific tension thresholds (0.8) and drift amounts are untuned. |
| Philosophy (Death of Director) | **Structural principle** | Medium | Generating multiple interpretations is well-established. The specific framing (Barthes/Derrida) is interpretive but the mechanism (multiple readings → selection) is sound. |
| Psychology (WorldSchema) | **Established mechanism** | High | Object permanence encoding is a well-known prompt engineering technique. The `[PERSISTS]` clause is a concrete, testable implementation. |
| Medicine (Homeostat) | **Analogous mechanism** | Medium | Homeostatic correction is a sound pattern but the specific set points and tolerances are arbitrary. `tolerance=0.0` for character identity may be too strict; `tolerance=inf` for shot size may be too loose. |
| Economics (Auctions) | **Established mechanism** | High | VCG auctions are mathematically well-understood. The specific bid formula `(1/speed) × (1+(1-task_score)²) / reliability` is reasonable but the weightings are untuned. |
| Cryptography (Merkle) | **Analogous mechanism** | Medium | Merkle chains for identity verification are a creative application of a sound cryptographic primitive. The chain size issue (Open Question 4) is a practical concern. |
| Metallurgy (Substrate) | **Structural principle** | High | The substrate constraint is not an analogy — it is a physical fact. Gold's conductivity, wire delay, and thermal derating are measurable, repeatable, and independent of interpretation. This is the only domain that is literally true rather than metaphorically true. |
 
### Calibration Roadmap

| Constant | Current Value | Proposed Calibration Method | Priority |
|:---|:---|:---|:---|
| `SIMILARITY_THRESHOLD` | 0.6 | Grid search 0.1-1.0 across 100 routing tasks. Measure recall vs precision. | High |
| `IRR_THRESHOLD` | 0.5 | Vary 0.3-0.9 across pipeline logs. Find value that minimizes false flags + missed losses. | High |
| `CreativeJoint.tension` | 0.8 | A/B test joint at tensions 0.5-1.0. Measure output quality vs baseline. | Medium |
| `ENTROPY_BUDGET` percentages | 40/25/15/15/5 | Derive from empirical token allocation in 1000 successful generations. | Low |
| `VCG bid weights` | 1.0 / (1-task_score)² | Learn from historical task success rates via logistic regression. | Medium |
| `Mass assignment` (CreativeInertia) | 3.0/2.0/1.0 | Calibrate from empirical drift rates. High-mass properties should drift <5% of frames. | Medium |

---


---

## 5. Domain Interconnection Web (Original)

Domains are defined by shared structural invariants. The protocol enforces explicit documentation of these connections:

| Domain A | Domain B | Shared Invariant | Concrete Integration Point |
|:---|:---|:---|:---|
| **Biology** (Mycelial) | **Medicine** (Homeostat) | Distributed sensing + corrective feedback | `MycelialNetwork.route()` feeds into `ContinuityHomeostat.measure_and_correct()` at `pipeline.py:200` |
| **Physics** (Thermodynamics) | **Economics** (Auctions) | Resource allocation under scarcity | `EntropyAuditor.flag_lossy_stages()` provides cost signal for `TaskAuction.bid()` — lossy stages pay higher |
| **Cryptography** (Merkle) | **Psychology** (WorldSchema) | Integrity verification through persistence | `MerkleContinuity.commit()` validates that `WorldSchema.persist()` clauses were preserved across frames |
| **Chemistry** (Catalysis) | **Biomechanics** (Joints) | Stable templates + flex joints | `CatalyticTemplate.fill()` feeds into `CreativeJoint.transmit()` — the template is the catalyst, the joint provides the degree of freedom |
| **Philosophy** (Death of Director) | **Psychology** (WorldSchema) | Multiple interpretations of persistent objects | `DeathOfTheDirector.run()` generates interpretations that `WorldSchema` validates for object permanence consistency |
| **Medicine** (Hemodynamic) | **Physics** (Entropy) | Metabolic cost correlates with entropy | `HemodynamicMonitor.autoregulate()` uses `EntropyAuditor.measure()` to detect ischemic (high-loss) stages and reroute |
| **Economics** (Contracts) | **Cryptography** (Merkle) | Binding commitments verified by hashing | `ContinuityContract.verify()` uses `MerkleContinuity.verify_chain()` to detect contract breaches |
| **Biology** (ZoneManager) | **Economics** (Auction) | Zone assignments constrain auction candidates | `ZoneManager.assign()` locks which models are available, `TaskAuction.allocate()` selects among them |

---

## 6. Validation Criteria & Self-Check

### The 5-Question Specificity Check

Every protocol output must pass:

| # | Criterion | This Document |
|:---|:---|:---|
| 1 | Names file paths? | YES — 9 files under `src/cinema/engines/` |
| 2 | Names functions/classes? | YES — 18 classes with typed interfaces |
| 3 | Inputs/outputs typed? | YES — `@dataclass` definitions or type annotations on all interfaces |
| 4 | Specifies test cases? | YES — 4-5 tests per domain (42 total) |
| 5 | Identifies call sites? | YES — exact pipeline.py line references for every class |

**Result: PASS** — All 5 criteria satisfied. This document is self-verifying.
### External Validation (v2 Addition)

The original self-check is necessary but not sufficient. A protocol that verifies itself is not verified. The following additional gates require external verification:

| # | Criterion | Verification Method | Current Status |
|:---|:---|:---|:---|
| 6 | IRR improvement >5% over baseline | A/B test: pipeline with vs without domains | **NOT VERIFIED** — no baseline exists |
| 7 | Latency overhead ≤20% of baseline | Profile each domain's runtime contribution | **NOT VERIFIED** — no profiling data |
| 8 | Test coverage >80% per module | `pytest --cov` per module | **PARTIAL** — tests exist but coverage not measured |
| 9 | No circular dependencies between domains | Static analysis of import graph | **NOT VERIFIED** — Biomechanics and Medicine share drift correction logic |

**Updated Result**: PASS (self-check) + FAIL (external validation) — 0/4 external gates passed. The protocol is structurally sound but empirically unvalidated. This is not a weakness of the protocol; it is a roadmap for the next development phase.


### Gate Failure Protocol

If any criterion fails:
1. Record what failed
2. Go back to Phase 3 (Force-Down to more specific)
3. Retry all 5 gates
4. Escalate if same gate fails 3 times — deliver with failure noted

---

## 7. Implementation Roadmap & Priority Matrix

### Priority 1 (Highest Impact, Lowest Effort)

| Module | Domain | Effort | Impact | File | Lines | Tests |
|:---|:---|:---|:---|:---|:---|:---|
| CharacterDNA | Biology | Low | Critical | `src/cinema/ports/continuation.py` | 30 | 3 |
| RibosomeCompiler | Chemistry | Low | Critical | `src/cinema/engines/catalyst.py` | 50 | 2 |
| Compiler temp reduction | Physics | Low | High | `src/cinema/engines/compiler.py` | 1 | 1 |
| WorldSchema | Psychology | Low | High | `src/cinema/engines/world.py` | 80 | 4 |
| EntropyAuditor | Physics | Low | High | `src/cinema/engines/entropy.py` | 60 | 4 |

### Priority 2 (High Impact, Medium Effort)

| Module | Domain | Effort | Impact | File | Lines | Tests |
|:---|:---|:---|:---|:---|:---|:---|
| ContinuityHomeostat | Medicine | Medium | High | `src/cinema/engines/homeostat.py` | 100 | 4 |
| HemodynamicMonitor | Medicine | Medium | High | `src/cinema/engines/homeostat.py` | 60 | 2 |
| CatalyticTemplate | Chemistry | Medium | High | `src/cinema/engines/catalyst.py` | 50 | 3 |
| CreativeJoint | Biomechanics | Medium | High | `src/cinema/engines/biomechanics.py` | 60 | 3 |
| RiverContinuity | Philosophy | Low | Medium | `src/cinema/engines/philosophy.py` | 60 | 4 |

### Priority 3 (Medium Impact, High Effort)

| Module | Domain | Effort | Impact | File | Lines | Tests |
|:---|:---|:---|:---|:---|:---|:---|
| MycelialNetwork | Biology | High | High | `src/cinema/engines/mycelial.py` | 130 | 5 |
| TaskAuction | Economics | High | Medium | `src/cinema/engines/auction.py` | 100 | 4 |
| ContinuityContract | Economics | Medium | Medium | `src/cinema/engines/auction.py` | 80 | 2 |
| MerkleContinuity | Crypto | Medium | Medium | `src/cinema/engines/merkle.py` | 80 | 5 |
| CreativeCerebellum | Biomechanics | High | High | `src/cinema/engines/biomechanics.py` | 60 | 2 |
| SemanticIsotope | Chemistry | Low | Medium | `src/cinema/engines/catalyst.py` | 60 | 3 |

**Total**: ~1,070 lines of implementation, ~44 test cases across 9 files.

### Performance Budget

| Component | Budget (ms) | Impact on IRR |
|:---|:---|:---|
| CharacterDNA encoding | 5 | Baseline (IRR=0.34 → 0.50 with this alone) |
| RibosomeCompiler translation | 10 | Major (IRR=0.50 → 0.85) |
| ContinuityHomeostat correction | 15 | Major (IRR=0.85 → 0.92, reduces drift) |
| EntropyAuditor measurement | 5 | Monitoring (no direct IRR impact, enables debugging) |
| MerkleContinuity verification | 10 | Assurance (no direct IRR impact, enables detection) |
| **Total overhead** | **45** | **IRR target: ≥ 0.89** |

## 7b. Failure Mode Taxonomy

Each domain has documented failure modes. The protocol acknowledges these explicitly to prevent surprise when they manifest in production:

| Domain | Failure Mode | Symptom | Likely Cause | Mitigation |
|:---|:---|:---|:---|:---|
| Biology (Mycelial) | **Node starvation** | Only 1-2 nodes respond to all signals | `SIMILARITY_THRESHOLD` too high; most nodes can't resonate | Reduce threshold or add fallback assignment |
| Biology (Mycelial) | **Node flooding** | Every node responds to every signal | `SIMILARITY_THRESHOLD` too low; no specialization emerges | Increase threshold or add energy budgeting |
| Physics (Entropy) | **False positive cascade** | IRR flags on every stage, desensitizing operators | `IRR_THRESHOLD` misaligned with actual model behavior | Calibrate from empirical data |
| Chemistry (Catalysis) | **Template explosion** | Unbounded template registry | No pruning mechanism for unused templates | Add template eviction policy (LRU or TTL) |
| Biomechanics (Joints) | **Joint runaway** | Every stage flexes, no direct pass-through | Baseline tension drifts upward over time | Add tension reset on each pipeline run |
| Philosophy (Death of Director) | **Interpretation overload** | Too many interpretations, model cannot choose | `NUM_INTERPRETATIONS` too high for task complexity | Set `NUM_INTERPRETATIONS = f(task_complexity)` |
| Psychology (WorldSchema) | **Persistence spam** | Every frame has 10+ `[PERSISTS]` clauses | No limit on persisted objects | Add max `[PERSISTS]` per frame (recommended: 3) |
| Medicine (Homeostat) | **Oscillation** | Corrections flip-flop between two values every frame | Tolerance too tight, natural variation triggers correction | Add hysteresis: correction must deviate by >2× tolerance before re-correction |
| Economics (Auctions) | **Bid convergence** | All bids converge to same value, auction becomes random | Model capabilities not differentiated enough for task types | Add random tie-breaking with exploration factor |
| Cryptography (Merkle) | **Chain bloat** | Memory grows without bound | No chain pruning | Archive blocks older than N frames, keep only last N+1 |
| **Cross-domain** | **Positive feedback loop** | Two domains amplify each other's errors | Unanticipated interaction between independent mechanisms | Add interaction testing as part of pre-deployment check |

### Cascading Failure Analysis

Some failures propagate across domains. The following sequences are known risks:

1. **Template explosion (Chemistry) → Node flooding (Biology) → Chain bloat (Cryptography)**: Too many templates create too many routing options, which creates too many persistence records. Mitigation: limit template count to 50.
2. **Joint runaway (Biomechanics) → Oscillation (Medicine) → Bid convergence (Economics)**: Flexing joints cause drift; homeostat tries to correct but oscillation makes the drift look patterned; auction models converge on the same bid because they can't distinguish stable from oscillating tasks. Mitigation: add joint stiffness decay that prevents runaway.

---


---

## Key Equations

### Information Retention Ratio
```
IRR = |structured_output| / |structured_input|
     = 1.0 for lossless stages
     = 0.34 for lossy stages (Compiler at T=1.5)
     = 0.89 with RibosomeCompiler + T=0.3
```

### Field Confidence Score
```
confidence = survival_rate × frequency × specificity
```

### Entropy Budget Allocation
```
E_total = E_character + E_environment + E_camera + E_lighting + E_action
E_character = 0.4 × E_total
E_environment = 0.25 × E_total
E_camera = 0.15 × E_total
E_lighting = 0.15 × E_total
E_action = 0.05 × E_total
```

### VCG Auction Bid
```
bid_i = (1 / speed_i) × (1 + (1 - task_score_i)²) / reliability_i
winner = argmin(bid_i)
price = second_lowest_bid
```

### Continuity Homeostat Correction
```
if mass(p) >= 2.0 and segment > 2 and value(p) != expected(p):
    inject(f"[CORRECTION] {p}: '{value(p)}' → '{expected(p)}'")
```

### Phase Transition Boundary (from MODELTUNE)
```
safe_t_range(model, task) = { T | delivery_rate(T) > 0.5 ∧ repetition_risk(T) < 0.3 }
```

---

## Open Questions & Escalations

1. **MycelialNetwork.threshold**: The `SIMILARITY_THRESHOLD = 0.6` is a guess. Needs empirical tuning from MODELTUNE data — what resonance threshold maximizes recall without flooding?
2. **Homeostat field enumeration**: Which fields need set points? The current implementation covers identity, temperature, and shot size. Every new field requires explicit registration. This doesn't scale.
3. **VCG pricing with 2 models**: When only 2 models bid, the second price is the single competitor's bid — this is still truthful but less efficient. With N=2, VCG devolves to second-price auction. Acceptable.
4. **Merkle chain size**: An unbounded chain grows without bound. Need pruning strategy: archive old blocks, keep only the last N+1 for verification.

5. **Cross-version domain mismatch**: The `absurdity-protocol.md` and `SKILL.md` documents contain different domain lists. `absurdity-protocol.md` uses: Biology, Physics, Chemistry, Biomechanics, Philosophy, Psychology, Medicine, Economics, Cryptography. `SKILL.md` uses: Biology, Physics, Chemistry, Neuroscience, Thermodynamics, Economics, Cryptography, Immunology, Tea Ceremony. Only 5 of 9 domains overlap. The missing domains (Neuroscience, Thermodynamics, Immunology, Tea Ceremony vs Biomechanics, Philosophy, Psychology, Medicine) represent a substantive disagreement about which domains are core to the protocol. This needs reconciliation: either the two documents describe different versions of the protocol, or one is a superset of the other. Recommend: designate `absurdity-protocol.md` as v2.0 and `SKILL.md` as v1.9, with a migration guide for the removed domains.
6. **Protocol self-application**: The Force-Down Protocol does not apply to itself. Where is the file path, interface, call site, and test plan for the Force-Down Protocol's *own* implementation? The fractal invariant states "Each step in the protocol is its own 6-step mini-workflow" but this is not demonstrated anywhere. A true fractal protocol would include itself in its own roadmap.
7. **Document entropy**: The protocol grows by accumulation, never by pruning. Over time, it will accumulate conflicting principles, redundant mechanisms, and abandoned implementations. A document-level entropy audit is needed — measuring the ratio of active to deprecated content.

---

*The palace is burning. The dictator is dead. Long live the mycelium. Every insight terminates in code.*  
*absurdity-protocol.md v2 — Audited and restructured by Protocol Auditor. No original text was removed or rewritten.*

# Empirical Calibration Experiment

> *A/B test: protocol-enriched pipeline vs vanilla pipeline across 100 generation tasks with blind human evaluation.*

---

## Experiment Rationale

The Absurdity Protocol makes strong claims: that its 9 domains improve Information Retention Ratio (IRR) from 0.34 toward 1.0, that homeostatic drift correction improves identity consistency, that mycelial routing produces higher-quality outputs than monolithic compilation, and that VCG auctioning selects better models than static assignment. None of these claims has been tested against a baseline.

This experiment is the **first empirical gate** for the protocol. If the protocol-enriched pipeline does not outperform the vanilla pipeline on at least 4 of 6 primary metrics with statistical significance (p < 0.05), the protocol's core claims are not supported and must be revised or abandoned.

---

## 1. Conditions

### Condition A: Vanilla Pipeline (Control)

The baseline TruePlan pipeline as defined in `src/cinema/pipeline.py`. No protocol domains active. Single Gemma-12B model at T=1.5 for all stages. Standard prompt assembly: Screenwriter → Dramaturg → Director → Cinematographer → Gaffer → Editor → Compiler → Generator.

**Compiler behavior**: Summarizes structured specs into natural language prose before passing to the generative model.

### Condition B: Protocol-Enriched Pipeline (Treatment)

The same TruePlan pipeline with all 9 protocol domains active at their default configurations as specified in `absurdity-protocol.md`:

| Domain | Module Active | Key Configuration |
|:---|:---|:---|
| Biology (Mycelial) | `MycelialNetwork.route()` | `SIMILARITY_THRESHOLD = 0.6` |
| Physics (Thermodynamics) | `MaxwellCompiler.sort()` | Dimension-sorted prompt assembly |
| Chemistry (Catalysis) | `RibosomeCompiler.translate()` | Translation table field→slot mapping |
| Biomechanics (Joints) | `CreativeJoint.transmit()` | `tension_threshold = 0.8` |
| Philosophy (Death of Director) | `DeathOfTheDirector.run()` | `NUM_INTERPRETATIONS = 3` |
| Psychology (WorldSchema) | `WorldSchema.persist()` | `[PERSISTS]` clause injection |
| Medicine (Homeostat) | `ContinuityHomeostat.measure_and_correct()` | Set points: identity (tol=0), color temp (tol=200), shot size (tol=inf) |
| Economics (Auctions) | `TaskAuction.allocate()` | VCG bidding with `MODEL_CAPABILITIES` |
| Cryptography (Merkle) | `MerkleContinuity.commit()` | SHA256 chain verification |

**Compiler behavior**: Dimension-sorted prompt assembly with `[CORRECTION]` and `[PERSISTS]` clause injection. Catalytic template filling instead of prose summarization.

### Condition C (Optional): Ablation — Protocol-Lite

A third condition that activates only 3 domains (Chemistry — Catalytic Templates, Psychology — WorldSchema, Medicine — Homeostat) to measure whether full protocol complexity is justified. This condition is optional pending compute budget. It answers: "does the protocol need all 9 domains, or is a 3-domain subset sufficient for most improvement?"

---

## 2. Task Selection (100 Generation Tasks)

The 100 tasks are stratified across 5 categories to ensure coverage of the protocol's claimed capabilities:

### Category 1: Narrative Continuity (25 tasks)

Tasks designed to test identity preservation across multiple frames. Example:
- "A woman in a red coat walks through a market, stops at a fruit stall, picks up an apple, examines it, puts it back, continues walking"
- "Two characters have a conversation at a dinner table; one leaves the room; the other reacts alone"
- "A car chase through a city: driver's appearance, vehicle color, time of day must remain consistent across 6 shots"

**Primary metric**: Identity drift rate (characters, objects, environment)

### Category 2: Object Permanence (15 tasks)

Tasks where props and characters exit and re-enter the frame. Tests whether WorldSchema preserves object existence.
- "A dog runs into a park, disappears behind a tree, emerges 3 shots later"
- "A character sets down a coffee cup, it remains on the table through 3 subsequent shots with different framing"

**Primary metric**: Object persistence rate (objects that exist in later frames)

### Category 3: Technical Precision (25 tasks)

Tasks requiring specific camera, lighting, and lens specifications. Tests whether the compiler preserves structured field values.
- "ARRI Alexa 35, 75mm at T/2.0, Zeiss Suprema Prime, key light HMI 5600K, fill light 3000K at 40%"
- Sequence: same camera specs across 5 shots, then explicitly change one parameter

**Primary metric**: IRR (Information Retention Ratio) — field preservation rate

### Category 4: Multi-Model Orchestration (20 tasks)

Tasks requiring different capabilities across stages. Tests whether the VCG auction allocates models optimally.
- Complex narrative requiring both creative writing (high-temp model) and precise technical specification (low-temp model)
- Tasks spanning symbolic, emotional, and technical dimensions

**Primary metric**: Model-task fit score (correctness × latency)

### Category 5: Creative Variety (15 tasks)

Open-ended creative tasks to test whether protocol enrichment harms or helps creative range.
- "A cyberpunk dream sequence in neons and rain"
- "A historical battle scene from the perspective of a child hiding under a cart"
- "An abstract meditation on entropy told through falling leaves"

**Primary metric**: Creative quality score (blind evaluator rating on range, originality, coherence)

---

## 3. Metrics

### Primary Metrics (6)

| # | Metric | Definition | Measurement Method | Minimum Improvement Required |
|:---|:---|:---|:---|:---|
| 1 | **IRR** | `preserved_fields / total_structured_fields` in the generated prompt | Automated: string-match field values from structured spec against generated output | +10 percentage points over vanilla |
| 2 | **Identity Drift Rate** | % of frames where a character identity attribute (coat color, hair, props) changes without explicit direction | Blind evaluator: per-frame identity checklist | -30% (30% fewer drift events) |
| 3 | **Object Persistence Rate** | % of objects that survive frame transitions (exiting and re-entering) | Blind evaluator: object checklist per frame | +20 percentage points over vanilla |
| 4 | **Latency Overhead** | Total pipeline runtime in seconds | Automated: `time` measurement | ≤ 20% increase over vanilla |
| 5 | **Overall Quality** | 1-5 Likert scale: coherence, visual consistency, narrative clarity | Blind evaluator (3 evaluators per output, averaged) | +0.5 mean improvement |
| 6 | **Creative Range** | 1-5 Likert scale: originality, emotional range, unexpectedness | Blind evaluator (3 evaluators per output, averaged) | Not worse than vanilla (non-inferiority) |

### Secondary Metrics (4)

| # | Metric | Purpose |
|:---|:---|:---|
| 7 | **Auction Efficiency** | % of tasks where the VCG-selected model outperforms random assignment | Validates Domain 9 (Economics) specifically |
| 8 | **Correction Necessity** | % of frames where `[CORRECTION]` clauses are triggered vs. actually needed | Calibrates Domain 8 (Medicine) set points |
| 9 | **Template Coverage** | % of structured fields that have a corresponding Catalytic Template entry | Validates Domain 4 (Chemistry) completeness |
| 10 | **Evaluator Agreement** | Inter-rater reliability (Fleiss' kappa) across 3 blind evaluators | Validates the human evaluation itself |

---

## 4. Experimental Protocol

### Phase 0: Pipeline Instrumentation (Pre-Experiment)

Before any generation, instrument both pipelines with:

```python
class ExperimentLogger:
    """Logs every stage output for both conditions."""
    def __init__(self):
        self.logs: list[StageRecord] = []

    def record(self, condition: str, task_id: str, stage: str, input_fields: dict, output_text: str, latency_ms: float):
        self.logs.append(StageRecord(condition, task_id, stage, input_fields, output_text, latency_ms))

    def get_irr(self, condition: str, task_id: str) -> float:
        """Compute IRR for a specific condition+task across all stages."""
        records = [r for r in self.logs if r.condition == condition and r.task_id == task_id]
        total_input = sum(len(r.input_fields) for r in records)
        total_preserved = sum(1 for r in records for k, v in r.input_fields.items() if str(v) in r.output_text)
        return total_preserved / max(total_input, 1)
```

**File**: `empirical_calibration_experiment.py` (standalone executable; contains `ExperimentLogger`, `ExperimentConfig`, `Anonymizer`, and `run_experiment`)

### Phase 1: Generation (Automated)

1. For each of the 100 tasks, generate both Condition A and Condition B outputs
2. Randomize the order of condition presentation per task (to control for model warm-up effects)
3. Record latency, token count, and IRR for each generation
4. Store all outputs with anonymized condition labels (A or B, with mapping held separately)

**Randomization**: Use a Latin square design: tasks 1-100, conditions A and B, swapped order every 10 tasks.

**Sample ID format**: `TASK_{id}_COND_{A|B}_RUN_{1|2}` (each condition run twice to measure variance)

**Total generations**: 100 tasks × 2 conditions × 2 runs = 400 generations

### Phase 2: Anonymization

1. Strip all pipeline metadata from outputs
2. Remove any formatting artifacts that would identify which condition produced which output
3. Assign random 4-digit evaluation IDs
4. Create paired sets: for each task, present outputs side-by-side without condition labels

**Anonymization check**: A pilot test with 5 outputs shown to a non-evaluator — if they can guess the condition at >60% accuracy, anonymization is insufficient and must be strengthened.

### Phase 3: Blind Human Evaluation

1. Recruit 3 evaluators (domain experts in film, AI, or both)
2. Each evaluator reviews all 100 tasks × 2 conditions = 200 outputs
3. Evaluators rate each output on the 6 primary metrics (1-5 scales)
4. Evaluators also provide free-text comments on notable successes or failures
5. Evaluators do NOT know which condition produced which output
6. Evaluators do NOT know which metrics are primary vs secondary

**Evaluation order**: Randomized per evaluator to control for order effects.

**Evaluator training**: Provide 5 calibration examples before the main evaluation to anchor the 1-5 scale.

**Time estimate per evaluator**: ~8 hours (100 tasks × 2 outputs × ~2.5 minutes per output + breaks)

### Phase 4: Statistical Analysis

| Test | Purpose | Threshold |
|:---|:---|:---|
| Paired t-test (or Wilcoxon signed-rank) | Compare metric means across conditions for each task | p < 0.05 |
| Cohen's d | Effect size | d > 0.3 (small but meaningful) |
| Fleiss' kappa | Inter-rater reliability across 3 evaluators | κ > 0.4 (moderate agreement) |
| Benjamini-Hochberg correction | Adjust for multiple comparisons (6 primary metrics) | q < 0.1 |
| Mixed-effects model | `metric ~ condition + (1|task_id) + (1|evaluator)` | Random effects for task and evaluator variation |

**Power analysis**: With 100 paired observations and an expected effect size of Cohen's d = 0.3, the experiment has 80% power at α = 0.05 (calculated via G*Power). This justifies the 100-task sample size.

### Phase 5: Protocol Adjustment

Based on results, apply the following decision tree:

```
IF (primary_metrics_won >= 4) AND (latency_overhead <= 20%):
    → Protocol validated. Proceed to production deployment with current configs.
    → Trigger calibration roadmap for individual constants (SIMILARITY_THRESHOLD, temps, etc.)
    → Archive results as empirical baseline for future comparisons.

ELSE IF (primary_metrics_won >= 2) AND (latency_overhead > 20%):
    → Protocol partially validated. Investigate latency bottlenecks per domain.
    → Disable domains with poorest latency/impact ratio. Re-run experiment with reduced protocol.
    → Update Implementation Roadmap with latency findings.

ELSE:
    → Protocol not supported by this experiment.
    → Flag which metrics failed and which conditions (if any) showed improvement.
    → Revert to vanilla pipeline. Open protocol for architectural review.
    → Publish negative results. The protocol must document its own failures.
```

---

## 5. Power Analysis & Sample Size Justification

### Why 100 tasks?

| Parameter | Value | Rationale |
|:---|:---|:---|
| Expected effect size (IRR) | d = 0.5 | Estimated from the claimed improvement from 0.34 → 0.89 IRR |
| Expected effect size (Quality) | d = 0.3 | Conservative estimate; quality is harder to shift than IRR |
| α | 0.05 | Standard for behavioral experiments |
| Power (1-β) | 0.80 | Standard minimum |
| Required N | 64 (IRR) / 90 (Quality) | Calculated via G*Power for paired t-test |
| **Selected N** | **100** | Rounds up to cover both effect sizes, plus 10% buffer for failed generations |

### Why 3 evaluators?

With 3 evaluators and Fleiss' kappa target > 0.4, the reliability of the quality metric is defensible. A single evaluator would be vulnerable to individual bias. More than 3 evaluators would reduce the pool size per evaluation and increase scheduling complexity without proportional increase in reliability (diminishing returns after 3-4 evaluators per output).

---

## 6. Implementation Plan

### Files to Create

| File | Purpose | Priority |
|:---|:---|:---|
| `empirical_calibration_experiment.py` | Standalone executable: orchestrates 400 generations across both conditions with randomized order, automated logging, anonymization, IRR computation | P0 |
| `deploy/experiment/evaluation_interface.html` | Static page for blind evaluators: side-by-side output comparison with 1-5 scales per metric | P1 |
| `deploy/experiment/analyzer.py` | Runs paired t-tests, Cohen's d, Fleiss' kappa, mixed-effects models, generates report | P1 |
| `deploy/experiment/tasks.json` | 100 task descriptions in structured JSON format, stratified across 5 categories | P0 |
| `deploy/experiment/calibration_set.json` | 5 calibration examples for evaluator training | P1 |
| `deploy/experiment/config.py` | Both condition configurations, model definitions, temperature settings | P0 |

### Task Description Schema

```json
{
  "task_id": 1,
  "category": "narrative_continuity",
  "title": "Woman in red coat at market",
  "prompt": "A woman in a red coat walks through a market...",
  "structured_spec": {
    "character_identity": "woman|red coat|brown hair|30s|tired expression",
    "camera_body": "ARRI Alexa 35",
    "lens": "75mm",
    "focal_length_mm": 75,
    "aperture": "2.0",
    "key_light": "HMI",
    "color_temp_k": 5600,
    "setting": "open-air market",
    "weather": "sunny",
    "action": "walking, stopping, examining"
  },
  "critical_fields": ["character_identity", "setting", "camera_body"],
  "num_segments": 5
}
```

### Pipeline Configuration Schema

```python
@dataclass
class ExperimentConfig:
    """Configuration for one experimental condition."""
    name: str  # "vanilla" | "protocol" | "protocol_lite"
    model_key: str
    temperature: float
    domains_enabled: list[str]  # domain names active in this condition
    compiler_mode: str  # "prose" | "dimension_sorted" | "catalytic"
    use_homeostat: bool
    use_merkle: bool
    use_auction: bool

VANILLA_CONFIG = ExperimentConfig(
    name="vanilla",
    model_key="gemma-4-12b",
    temperature=1.5,
    domains_enabled=[],
    compiler_mode="prose",
    use_homeostat=False,
    use_merkle=False,
    use_auction=False,
)

PROTOCOL_CONFIG = ExperimentConfig(
    name="protocol",
    model_key="gemma-4-12b",
    temperature=0.3,
    domains_enabled=[
        "mycelial", "entropy", "catalyst", "biomechanics",
        "philosophy", "world_schema", "homeostat", "auction", "merkle",
    ],
    compiler_mode="catalytic",
    use_homeostat=True,
    use_merkle=True,
    use_auction=True,
)
```

### Generation Script Structure

```python
# experiment_runner.py

def run_experiment(tasks_path: str, configs: list[ExperimentConfig], output_dir: str):
    """Run all conditions for all tasks with randomized order."""
    logger = ExperimentLogger()
    tasks = json.load(open(tasks_path))

    for task in tasks:
        for config in randomized_configs(configs, seed=task["task_id"]):
            # Run pipeline with this config
            output = pipeline.run(task["prompt"], config)
            # Record all stage outputs
            for stage_name, stage_output in output["stages"].items():
                logger.record(
                    condition=config.name,
                    task_id=task["task_id"],
                    stage=stage_name,
                    input_fields=task.get("structured_spec", {}),
                    output_text=stage_output["text"],
                    latency_ms=stage_output["latency_ms"],
                )
            # Save anonymized output
            save_anonymized(output, config.name, task["task_id"], output_dir)

    return logger.summary()
```

---

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|:---|:---|:---|:---|
| Evaluator fatigue — quality drops after 50+ evaluations | High | Medium | Limit evaluations to 25 per session across 4 sessions. Include attention checks (known-good outputs interspersed). |
| Anonymization failure — evaluators can identify condition from output characteristics | Medium | High | Run anonymization pilot test. If condition-identifying artifacts remain, strip more aggressively or add synthetic artifacts to both conditions. |
| Pipeline crashes — a generation fails for one condition but not the other | Medium | Medium | Implement retry logic (3 attempts). If persistent failure for one condition, record as missing data and use mixed-effects models that handle unbalanced designs. |
| Model updates during experiment — Ollama model is updated between conditions | Low | High | Run all generations in a single batch. Lock model versions. Document SHA256 of model files at experiment start. |
| Confounding variable: temperature — vanilla uses T=1.5, protocol uses T=0.3 | Certain | High | This is intentional and documented. The compiler temperature reduction IS one of the protocol's interventions. To disentangle: include a Condition D (vanilla at T=0.3 without protocol domains) as a secondary control. |
| Evaluator disagreement — Fleiss' kappa < 0.4 | Medium | High | If kappa < 0.4, switch from Likert ratings to pairwise preference judgments ("which output is better for metric X?"), which produce higher inter-rater reliability. |
| Task selection bias — chosen tasks favor protocol domains | Low | Medium | Tasks selected by an independent researcher (not the protocol author) using a stratified random sampling from a corpus of 1000 prompts. Protocol author has no input on task selection. |

---

## 8. Evaluation Interface Specification

### Side-by-Side Comparison View

The blind evaluator sees:

```
┌─────────────────────────────────────────────────────────────┐
│  TASK 14: "A car chase through neo-Tokyo at midnight"        │
│  ───────────────────────────────────────────────────────────  │
│                                                               │
│  ┌─── Output 7319 ───────────────────┐  ┌─── Output 4286 ──┐ │
│  │ [generated narrative text...]     │  │ [generated       │ │
│  │                                   │  │  narrative       │ │
│  │                                   │  │  text...]        │ │
│  └───────────────────────────────────┘  └──────────────────┘ │
│                                                               │
│  Rate each output:                                            │
│                                                               │
│  Coherence:       [1] [2] [3] [4] [5]    [1] [2] [3] [4] [5] │
│  Visual Consistency: [1] [2] [3] [4] [5] [1] [2] [3] [4] [5] │
│  Identity Consistency: [1] [2] [3] [4] [5] [1] [2] [3] [4] [5]│
│  Technical Precision: [1] [2] [3] [4] [5] [1] [2] [3] [4] [5]│
│  Originality:    [1] [2] [3] [4] [5]    [1] [2] [3] [4] [5] │
│                                                               │
│  Did you notice any specific errors?                          │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ [free text]                                            │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Deliverables

| Deliverable | Format | Recipient |
|:---|:---|:---|
| Raw generation logs | JSON (400 records) | Experiment archive |
| Anonymized outputs with evaluation IDs | JSON (400 records) | Blind evaluators |
| Evaluator ratings | CSV (3 evaluators × 200 ratings × 6 metrics) | Statistical analysis |
| Statistical analysis report | Markdown + PDF | Protocol authors |
| Calibration recommendations | JSON (updated constants) | Pipeline config |
| Experiment summary | Markdown | Protocol README |

---

## 10. Timeline

| Phase | Duration | Dependencies |
|:---|:---|:---|
| Pipeline instrumentation (logging, configs) | 2 days | Existing pipeline |
| Task generation and validation | 2 days | Independent researcher task selection |
| 400 generations (automated) | ~3 days (continuous) | Instrumented pipeline |
| Anonymization and quality check | 1 day | Completed generations |
| Evaluator training | 0.5 day | Anonymized calibration set |
| Blind evaluation (3 evaluators × 8 hrs) | 3 days (parallel) | Anonymized outputs |
| Statistical analysis | 1 day | Evaluator ratings |
| Report writing | 1 day | Analysis results |
| **Total** | **~14 days** | |

---

## 11. Stopping Criteria

The experiment must be stopped early if:

1. **Pipeline consistently fails** for one condition (>20% of generations return errors): halt and debug before continuing.
2. **Evaluators report fatigue** after <50 evaluations despite breaks: reduce task count to 50 and increase power by running 3 runs instead of 2.
3. **Anonymization is broken** (pilot test >60% accuracy): halt, redesign anonymization, restart.
4. **Protocol pipeline causes hardware failure** (OOM, thermal throttling) for >10% of generations: protocol fails the latency overhead gate by definition.

---

## 12. Falsification Conditions

This experiment is designed to falsify the protocol's core claims. The following outcomes would count as falsification:

| Outcome | Implication |
|:---|:---|
| IRR improvement < 5 percentage points | Catalytic Templates and MaxwellCompiler do not preserve field values better than prose summarization |
| Identity drift rate not reduced (or increased) | Homeostat corrections are counterproductive or misconfigured |
| Latency overhead > 40% | Protocol computational cost is not justified by marginal quality gain |
| Evaluators consistently prefer vanilla over protocol (p < 0.05) | Protocol enrichment actively degrades output quality |
| Fleiss' kappa > 0.6 but protocol does not win on any metric | Metrics are reliable and protocol simply doesn't help |

---

*This design protocol is self-verifying: it names files, defines interfaces, specifies behavioral changes, identifies call sites, and includes falsification conditions. Every insight terminates in an experiment.*
