# Redundancy Analysis

## Duplicate/Overlapping Concepts

### 1. Style Anchors (`_style.yaml`)
- **Found at**: `shorts/characters/_style.yaml`, `shorts/characters/_style_rider.yaml`, `microcosmos/characters/_style.yaml`
- **Overlap**: All define visual style, camera behavior, lighting specs, negative prompts
- **Difference**: Microcosmos version is 255 lines of physics-based detail (icosahedral grid, SSS materials, df/dt focus). Shorts version is aesthetic/narrative.
- **Action**: Each `_style.yaml` is universe-specific — no dedup needed but should be reconciled against Book II (World) as the single source

### 2. Architectural Spec (`shorts_architecture.txt` vs Cinema Books)
- `shorts_architecture.txt` describes the high-level system design
- Cinema Books (I-XIII) are the authoritative, full-depth version
- **Redundancy**: Architecture.txt is a summary — Books contain the full spec. Keep Books as source of truth.

### 3. Character YAML field patterns
- `biscuit.yaml`, `chiku.yaml`, `scraps.yaml`, `bandu.yaml`, `golu.yaml`, `rider.yaml` all share similar structure: name → appearance → personality → backstory → relationships → abilities
- Microcosmos `ant.yaml` and `honeybee.yaml` use fundamentally different structure: external morphology → internal anatomy → materials → movement
- **Redundancy**: The Biscuit-series YAMLs are redundant in structure but unique in content. Could be templated.

### 4. Prompt templates
- `_style.yaml prompt_template` in microcosmos
- `cinema_spec.json` struct definitions
- Book XIII (Prompt Compiler) template
- `cinema_v3_realvisxl.py` prompt construction
- **Redundancy**: 4 competing prompt template definitions. Book XIII should be authoritative.

### 5. MPS config wisdom
- Documented in: `lessons.md`, `cinema_v3_realvisxl.py` comments, `exp1-3` scripts
- **Redundancy**: Same knowledge (float32, cpu_offload, attention_slicing) scattered. Should be unified in a MPS profile document.

### 6. Absurdity Protocol vs Cinema Books
- Absurdity Protocol covers: continuity, character identity, world persistence, model routing
- Cinema Books cover: same domains through department isolation (Character Supervisor, Producer, Compiler)
- **Overlap exists but complementary**: Absurdity adds cross-domain metaphors (mycology, immunology, economics) that Cinema Books lack. Cinema Books add department isolation and workflow discipline that Absurdity lacks.

### 7. Microcosmos Constitution vs Cinema Books
- Microcosmos has 12 Books that parallel Cinema's 13 Books
- **Redundancy**: Naming differs (e.g., Microcosmos "Writer" = Cinema "Director"). Content models differ (Microcosmos is physics-based, Cinema is film-production-based).
- **Reconciliation needed**: The microcosmos constitution is more implementable (has coordinate systems, velocity limits, anomaly registries). Cinema Books are more philosophically complete (have department purpose, creative intent).

## Summary of Critical Redundancies
1. Prompt templates in 4 places → consolidate to Book XIII
2. `_style.yaml` scattered across characters/ and microcosmos/ → each is universe-scoped, acceptable
3. MPS config in 5+ locations → consolidate to one document
4. Architecture description in txt + Books + scripts → Books are authoritative
5. Cross-book concept mapping (Microcosmos Books vs Cinema Books) → needs explicit translation table
