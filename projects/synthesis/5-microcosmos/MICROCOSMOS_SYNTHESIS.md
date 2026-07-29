# Microcosmos — The 12-Book Compact in Practice

## Overview
Microcosmos is the Cinema engine **as a complete working system** — a 12-Book constitution governing macro-anatomy visualization of insects. It is the most advanced instantiation of the Cinema architecture.

## Constitution Structure
- **12 Books** (mapping directly to Cinema Books I-XIII but with different names)
- **35 articles total**: 24 ratified, 8 conditional, 3 anomalous
- **5 cross-book anomalies**, 1 resolved, 4 unresolved
- **Amendment process** (6 steps, non-negotiable)

| Book | Microcosmos Title | Image Source | Cinema Book |
|------|------------------|--------------|-------------|
| I | Director | Intent, emotion, narrative purpose | Book I (Director) + Book V |
| II | Cinematic Language | Visual grammar, symbolism | Book IV |
| III | Writer | Beats, timing, action | Book V (Director narrative) |
| IV | Production Designer | Environment, objects, atmosphere | Book X |
| V | Spatial Staging | Camera paths, coordinates, velocity | Book VII |
| VI | Character Supervisor | State, continuity, appearance | Book XI |
| VII | Camera | Lens, position, movement, focus | Book III |
| VIII | Lighting | Sources, shadow, color, exposure | Book VI |
| IX | Sound | Soundscape, foley, music | Book VIII |
| X | Editor | Rhythm, pacing, temporal structure | Book IX |
| XI | Producer | Merge, conflict detection | Book XII |
| XII | Prompt Compiler | Final render prompt | Book XIII |

## Key Architectural Differences from Standard Cinema
1. **Physics-based camera**: Icosahedral geodesic grid (12/42/162/642/2562 vertices), real 3D coordinates in mm, great-circle arcs, C² continuous acceleration
2. **Velocity enforcement**: 3mm/s external max, 1mm/s internal (hemolymph-damped), 0.1mm/s min
3. **Focus as dependent variable**: `df/dt = v * cos(θ)` — focus is servo-locked to spatial path
4. **Coordinate system**: All departments (Camera, Lighting, Sound, Production Designer) share a unified 3D coordinate system with origin at subject center
5. **Anomalies are explicit**: Fields that exist textually but enforce nothing are documented with remedies

## Detected Anomalies (from CONSTITUTION.yaml)
| ID | Issue | Books Affected | Status |
|----|-------|---------------|--------|
| CROSS-1 | No unified coordinate system across Books | IV, V, VII, VIII, IX | PARTIALLY RESOLVED |
| CROSS-2 | No velocity budget constraint | III, V, VII, X | UNRESOLVED |
| CROSS-3 | Decorative fields without enforcement | I, II, VI, XI | UNRESOLVED |
| CROSS-4 | Symbol persistence gap | II, I | UNRESOLVED |
| CROSS-5 | Focus treated as independent parameter | III, VII | RESOLVED |

## Characters
- **Solenopsis invicta (fire ant worker)**: ~924 lines of anatomical detail — every body region, internal organ, material, movement pattern
- **Apis mellifera (honeybee worker)**: ~867+ lines — full respiratory system, glandular system, signature "spiracle entry" motif
- **Style anchor** (`_style.yaml`): 255 lines defining the rendering universe — materials, lighting, camera physics, color pipeline, prompt template

## Spatial System (`spatial/rules.yaml`)
- **313 lines** of physics-based camera positioning
- 5 distance bands (establishing → internal cellular)
- 20-faced icosahedron base grid with 4 levels of subdivision
- 75+ anatomical landmark coordinates for the honeybee in real mm
- Path enforcement rules: no teleportation, no axis-locked movement, C² continuous

## World State
- Memory: 19 established facts
- World state: current episode, time, light level, character state, environment
- Timeline: pre-scene colony establishment (11 lines)
- Continuity: per-scene character tracking
- Props: persisted across scenes
