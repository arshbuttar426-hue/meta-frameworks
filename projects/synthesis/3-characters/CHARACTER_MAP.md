# Character YAMLs — World Engine Instances

## shorts/characters/ (8 files)
| File | Type | Domain | Covers |
|------|------|--------|--------|
| `_style.yaml` | Style anchor | Visual template | Camera, lighting, materials, negative prompts, spatial staging, prompt template |
| `_style_rider.yaml` | Style anchor | Rider visual template | Rider-specific style variant |
| `biscuit.yaml` | Character | Humanoid canine | Full character design: backstory, personality, appearance, costume, abilities |
| `chiku.yaml` | Character | Humanoid canine | Companion design, relationship to Biscuit |
| `scraps.yaml` | Character | Support character | Secondary character design |
| `bandu.yaml` | Character | Antagonist | Villain design, conflict role |
| `golu.yaml` | Character | Support/Antagonist | Additional character |
| `rider.yaml` | Character | Mount/companion | Mounted character design |

## microcosmos/characters/ (3 files)
| File | Subject | Detail Level | Notes |
|------|---------|-------------|-------|
| `ant.yaml` | Solenopsis invicta worker | **Extreme** (~924+ lines) | Full external + internal anatomy, materials, movement, scale references |
| `honeybee.yaml` | Apis mellifera worker | **Extreme** (~867+ lines) | Full external + internal, signature "spiracle entry" motif |
| `_style.yaml` | Universal style ref | Visual system | Macro cinematic, SSS, iridescence, camera physics, prompt template |

## Pattern
- `_style.yaml` = Book II (World) + Book X (Production Designer) — defines the rendering universe
- `biscuit.yaml` etc. = Book XI (Character Supervisor) instances
- `ant.yaml`, `honeybee.yaml` = Book XI + Book IV (Production Designer) + Book III (Camera) integrated
- Originals use ~50-100 lines per character; Microcosmos uses ~900+ lines per creature
