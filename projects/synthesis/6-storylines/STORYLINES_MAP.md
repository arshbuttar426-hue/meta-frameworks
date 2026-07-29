# Storylines — Narrative Implementations

## biscuit/ (6 files)
| File | Purpose |
|------|---------|
| `_sequence.yaml` | Episode sequence definition |
| `S01-jobs-discussion.yaml` | Scene 1: Characters discuss jobs |
| `S02-old-memories.yaml` | Scene 2: Flashback/reminiscence |
| `S03-coming-back.yaml` | Scene 3: Return narrative |
| `S04-samosa.yaml` | Scene 4: Food/comfort scene |
| `specs/` | Per-scene cinematic specifications |
| `world/` | Per-storyline world state |

## gas-station/ (5 files)
| File | Purpose |
|------|---------|
| `_sequence.yaml` | Episode sequence |
| `S02_dismount_test_prompt.md` | Scene 2 test prompt |
| `S07_departure_test_prompt.md` | Scene 7 test prompt |
| `specs/` | Cinematic specifications |
| `world/` | World state |

## microcosmos/ (storylines subfolder)
- Scene files for ant (S01-S03) and honeybee (S01)
- Each scene has: scene YAML with beats, spatial_staging_specification, lighting_specification, sound_specification
- Structured per the 12-Book constitution format

## Pattern
- Each storyline is self-contained with its own `specs/` and `world/` directory
- `_sequence.yaml` defines the episode arc
- Scene files follow `S{NN}-{slug}.yaml` naming convention
- Specification files contain structured Camera/Lighting/Sound/Editor specs per scene
- Gas-station has test prompts (`.md` files) — direct prompt experiments
