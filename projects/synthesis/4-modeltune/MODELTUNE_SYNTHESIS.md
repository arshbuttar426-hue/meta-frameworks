# MODELTUNE — LLM Tuning & Absurdity Protocol

## Tuning Results (6 models, 152 benchmarks)

| Model | Speed | Code | Reasoning | Reliability | Best For |
|-------|-------|------|-----------|-------------|----------|
| **Gemma-12B** | 17s avg | ★★★★★ | ★★★★★ | 100% | **All-purpose** — temperature-agnostic, handles all complexity |
| **Phi-4-mini** | 0.7s | ★★★★ | ★★★ | 100% | Fast code gen, simple tasks, translation |
| **Ornith-9B** | 31.9s | ★★★★★ | ★★★★ | 100% | Complex code at low temp (T=0.1) |
| **SmolLM3-3B** | 0.6s | ★★ | ★★ | 100% | Trivial instruction following |
| **VibeThinker-3B** | 4.4s | ★ | ★★ | 40% | Avoid — needs high temp forced |
| **Qwen3.5-4B** | 16.3s | ★★★ | ★ | 20% | **Worst** — slow, unreliable, overthinks |

## Key Discovery: Phase Transition Exploit
- **Compiler temperature reduction**: 1.5 → 0.3 improves IRR from 0.34 to 0.89
- Thinking models (VibeThinker, Qwen) need T≥0.7 to function — they get stuck in reasoning loops
- Direct models (Phi, Gemma) work at any temperature
- Gemma-12B is the "gold standard" — 100% reliable across all configs

## Absurdity Protocol — Force-Down Framework

### 9 Domains of Sabotage (all forced to code)
| Domain | Principle | Implementation | File Target |
|--------|-----------|---------------|-------------|
| Mycology | Distributed nodes, no central brain | `MycelialRouter`, `CreativeNode` | `src/cinema/engines/mycelial.py` |
| Physics (Maxwell) | Sort, don't fuse | `MaxwellCompiler`, `SortedPrompt` | `src/cinema/engines/entropy.py` |
| Chemistry | Catalytic templates | `RibosomeCompiler`, `CatalyticTemplate` | `src/cinema/engines/catalyst.py` |
| Biomechanics | Joints over levers | `CreativeJoint`, `CreativeCerebellum` | `src/cinema/engines/biomechanics.py` |
| Philosophy (Barthes) | Death of the Director | `DeathOfTheDirector`, `InterpretationSpace` | `src/cinema/engines/philosophy.py` |
| Psychology | Object permanence | `WorldSchema`, `CharacterSchema` | `src/cinema/engines/world.py` |
| Medicine | Homeostatic continuity | `ContinuityHomeostat`, `SetPoint` | `src/cinema/engines/homeostat.py` |
| Economics | VCG auctions | `TaskAuction`, `ContinuityContract` | `src/cinema/engines/auction.py` |
| Tea Ceremony | Ritual scheduling | `CeremonyScheduler` | `src/cinema/engines/ceremony.py` |

### The Specificity Engine
Mandates every solution specifies: file path, class/function, typed interface, behavioral change, call site, test plan (≥3 cases). Rejects vague/philosophical outputs.

### The Force-Down Protocol (6 steps)
1. Reveal principle → 2. Envision artifact → 3. Define interface → 4. Pinpoint file → 5. Identify call site → 6. Plan tests

## Hypergraph & Phase Transition Exploit
- Phase boundaries documented at `PHASE_TRANSITION_EXPLOIT.md`
- Zonal Autoregulation: models assigned to zones (creative, reasoning, fast_analysis, precision) with permanently loaded models
- VCG Auction: models bid `speed × reliability / cost` on tasks; winner pays second price
- CharacterDNA: 13-trait compact encoding appended verbatim to every prompt
- CreativeInertia: physics-inspired momentum tracking for visual properties
- WorldSchema: object permanence clauses in every prompt
