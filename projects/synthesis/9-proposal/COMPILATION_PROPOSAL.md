# Compilation Proposal — Unifying the Cinema Engine

## Problem
The cinematic prompt engine is distributed across:
1. 13 Cinema Books (philosophical/architectural)
2. Python scripts (implementations — scattered, versioned, some broken)
3. Character YAMLs (domain data — variable schemas)
4. MODELTUNE/absurdity (cross-domain patterns — rich but not integrated)
5. Microcosmos constitution (working physics-based implementation — parallel but not unified)
6. Storylines (narrative content — no standard format)

**Cost of fragmentation**: Prompt templates in 4 places, MPS config in 5 places, cross-Book concept mismatches, no single integration point.

## Proposal: The Unified Cinema Compendium

### Structure

```
cinema-compendium/
├── CONSTITUTION/           # (from microcosmos CONSTITUTION.yaml)
│   ├── 00-preamble.md
│   ├── 01-director.md
│   ├── 02-cinematic-language.md
│   ├── 03-camera.md
│   ├── 04-lighting.md
│   ├── 05-spatial-staging.md
│   ├── 06-sound.md
│   ├── 07-editor.md
│   ├── 08-production-designer.md
│   ├── 09-character-supervisor.md
│   ├── 10-producer.md
│   ├── 11-prompt-compiler.md
│   ├── 12-world-engine.md
│   └── 13-absurdity-protocol.md   # NEW — cross-domain patterns
├── TEMPLATES/               # Unified prompt templates (from Book XIII)
│   ├── veo31-template.yaml
│   ├── sdxl-template.yaml
│   ├── catalytic-compiler.yaml
│   └── prompt-templates.md
├── HARDWARE/                # Unified hardware profiles
│   ├── mps-apple-silicon.md
│   ├── model-performance-benchmarks.json
│   └── phase-transition-table.md
├── DOMAINS/                 # Absurdity protocol domains (from MODELTUNE)
│   ├── mycelial-router.md
│   ├── continuity-homeostat.md
│   ├── task-auction.md
│   ├── world-schema.md
│   └── character-dna.md
├── WORLDS/                  # World instances (from shorts/characters, microcosmos)
│   ├── microcosmos/
│   │   ├── characters/      # ant.yaml, honeybee.yaml, _style.yaml
│   │   ├── spatial/         # rules.yaml (+ ant landmarks)
│   │   ├── world/           # memory, state, timeline, props
│   │   └── storylines/      # ant scenes, bee scenes
│   ├── biscuit/
│   │   ├── characters/      # biscuit.yaml, chiku.yaml, etc.
│   │   └── storylines/      # S01-S04
│   └── gas-station/
│       ├── characters/
│       └── storylines/
├── SPECS/                   # Structured spec schemas (from cinema_spec.json)
│   ├── CineSpec.yaml
│   ├── LightSpec.yaml
│   ├── CharacterDNA.yaml
│   ├── SoundSpec.yaml
│   └── ContinuityVerdict.yaml
├── ENGINE/                  # Pipeline implementations (from Python scripts)
│   ├── compiler-engine.py
│   ├── continuity-engine.py
│   ├── world-engine.py
│   ├── character-dna.py
│   └── pipeline-assembly.sh
└── ANOMALY_REGISTRY/        # Known issues (from microcosmos anomalies)
    ├── cross-book-conflicts.yaml
    ├── decorative-fields.yaml
    └── velocity-budget.yaml
```

### Key Integration Decisions

1. **Book XIII (Prompt Compiler) is the single integration point** — all other specs feed into it. The Compiler must be accessible to the user as the primary interface.

2. **The Microcosmos constitution becomes the canonical Book structure** — its physics-based approach (coordinates, velocities, anomaly registry, enforcement rules) is more implementable than the current Cinema Books' narrative descriptions.

3. **The Absurdity Protocol becomes Book XIV** — its 9-domain framework provides cross-domain pattern language that the current architecture lacks. The MycelialRouter, ContinuityHomeostat, and TaskAuction are concrete architectural components.

4. **Self-attention mechanism as the third generation** — Absurdity protocol mentions "zonal autoregulation" but the next evolution is clear: the MycelialRouter + ContinuityHomeostat + MaxwellCompiler form a self-attention mechanism where each prompt component attends to others. The `[CAMERA]` block attends to `[CHARACTER]` position to compute focus. The architecture is *already* an attention mechanism — it just hasn't named itself as one.

5. **MPS config is a single document** — consolidate `lessons.md`, script comments, and experiment notes into `HARDWARE/mps-apple-silicon.md` with a single source of truth.

6. **Prompt templates consolidate to four** — `veo31-template.yaml`, `sdxl-template.yaml`, `catalytic-compiler.yaml`, and a generic `prompt-templates.md`. All scripts reference these templates; none hardcode prompt structures.

### Implementation Plan

| Phase | Task | Files Affected |
|-------|------|---------------|
| 1 | Consolidate prompt templates to Book XIII | cinema_v3_realvisxl.py, cinema_full_pipeline.py, _style.yaml, cinema_spec.json |
| 2 | Unify hardware config to single document | lessons.md, exp1-3, cinema_v2/3 scripts |
| 3 | Adopt microcosmos constitution as canonical | cinema Books I-XIII rewrite |
| 4 | Integrate absurdity protocol as Book XIV | MODELTUNE/SKILL.md → compendium DOMAINS/ |
| 5 | Create unified spec schemas | cinema_spec.json → SPECS/ directory |
| 6 | Build character DNA pipeline | CharacterDNA from absurdity protocol |
| 7 | Build continuity homeostat | ContinuityHomeostat + CreativeInertia + WorldSchema |
| 8 | Document anomaly registry | All microcosmos anomalies + newly discovered |

### Success Criteria

1. A single `cinema <topic>` command invokes the full TruePlan pipeline
2. All prompts use centralized templates (no hardcoded prompt construction)
3. ContinuityVerdict is generated for every segment (zero frames without identity locks)
4. Anomaly registry has at least 10 entries from real pipeline runs
5. MPS config works on first read (no more "float16 NaN" surprises)
6. Cross-Book conflicts are detected at merge time, not assumed away
