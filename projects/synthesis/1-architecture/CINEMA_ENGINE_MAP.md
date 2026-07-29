# Cinema Engine — Full Book-to-Implementation Map

## Book I: Director (Constitution)
- **Files**: `.config/opencode/skills/cinema/SKILL.md`, `cinema_spec.json`
- **Domain**: Intent, emotional purpose, department isolation
- **Microcosmos mirror**: `CONSTITUTION.yaml` Book I — 5 articles, 3 ratified, 2 conditional
- **Principle**: Director sets WHY. No department invents intention.

## Book II: World
- **Files**: `.config/opencode/skills/cinema/BOOK_II_WORLD.md`, `_style.yaml` (shorts/)
- **Domain**: Single source of truth — nothing exists unless in `world/`
- **Microcosmos mirror**: `world/*.yaml` (memory, state, timeline, characters, props, locations)
- **Files mapped**: `characters/*.yaml`, `storylines/*/world/`

## Book III: Camera
- **Files**: `.config/opencode/skills/cinema/BOOK_III_CAMERA.md`
- **Domain**: Position, lens, movement, focus, framing
- **Microcosmos mirror**: `spatial/rules.yaml` — icosahedral geodesic grid, distance bands, velocity profiles
- **Implementation**: `cinema-frame.py`, `cinema_v2_experiment.py`, `cinema_v3_realvisxl.py`

## Book IV: Cinematic Language
- **Files**: `.config/opencode/skills/cinema/BOOK_IV_CINEMATIC_LANGUAGE.md`
- **Domain**: Visual grammar, emotional translation, symbolism
- **Microcosmos mirror**: CONSTITUTION.yaml Book II — visual rhythm, symbolism registry, emotional translation

## Book V: Director (Leadership)
- **Files**: `.config/opencode/skills/cinema/BOOK_V_DIRECTOR.md`
- **Domain**: Creative leadership, department coordination

## Book VI: Lighting
- **Files**: `.config/opencode/skills/cinema/BOOK_VI_LIGHTING.md`
- **Domain**: Light sources, shadow, color temperature, exposure
- **Microcosmos mirror**: CONSTITUTION.yaml Book VIII — lighting arc, source positions, shadow depth

## Book VII: Spatial Staging
- **Files**: `.config/opencode/skills/cinema/BOOK_VII_SPATIAL_STAGING.md`
- **Domain**: Camera paths, positions, spatial relationships
- **Microcosmos mirror**: CONSTITUTION.yaml Book V, `spatial/rules.yaml` (full icosahedral implementation)

## Book VIII: Sound
- **Files**: `.config/opencode/skills/cinema/BOOK_VIII_SOUND.md`
- **Domain**: Soundscape, foley, music
- **Microcosmos mirror**: CONSTITUTION.yaml Book IX — sound hierarchy, spatial audio, temporal sync

## Book IX: Editor
- **Files**: `.config/opencode/skills/cinema/BOOK_IX_EDITOR.md`
- **Domain**: Rhythm, pacing, temporal structure, transitions
- **Microcosmos mirror**: CONSTITUTION.yaml Book X — temporal phases, information release, transition types

## Book X: Production Designer
- **Files**: `.config/opencode/skills/cinema/BOOK_X_PRODUCTION_DESIGNER.md`
- **Domain**: Environment, objects, atmosphere, physical space
- **Microcosmos mirror**: CONSTITUTION.yaml Book IV — objects with coordinates, atmosphere as medium

## Book XI: Character Supervisor
- **Files**: `.config/opencode/skills/cinema/BOOK_XI_CHARACTER_SUPERVISOR.md`
- **Domain**: Character state, continuity, appearance verification
- **Microcosmos mirror**: CONSTITUTION.yaml Book VI — character state, corrections tracking

## Book XII: Producer
- **Files**: `.config/opencode/skills/cinema/BOOK_XII_PRODUCER.md`
- **Domain**: Merge, conflict detection, final approval
- **Microcosmos mirror**: CONSTITUTION.yaml Book XI — conflict detection, cross-Book verification

## Book XIII: Prompt Compiler
- **Files**: `.config/opencode/skills/cinema/BOOK_XIII_PROMPT_COMPILER.md`
- **Domain**: Final render prompt — the executable output
- **Microcosmos mirror**: CONSTITUTION.yaml Book XII — structured output, complete coverage
- **Implementation**: `cinema_full_pipeline.py`, `cinema_v3_realvisxl.py`

## Adjacent Concept: Absurdity Protocol
- **Files**: `MODELTUNE/SKILL.md`, `MODELTUNE/absurdity-protocol.md`
- **Domain**: Multidisciplinary problem-solving (mycology → continuity, thermodynamics → entropy, economics → auctions)
- **Code artifacts**: 9 domain implementations with full class/interface/call-site/test-plan specs
- **Applying to Cinema**: Each domain forces down to concrete pipeline changes
