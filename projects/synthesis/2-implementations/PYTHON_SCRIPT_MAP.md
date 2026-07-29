# Python Scripts — Implementation Map

## Pipeline Scripts
| Script | Purpose | Cinema Book | Status |
|--------|---------|-------------|--------|
| `cinema_frame.py` | Single frame generation | Book III (Camera) + Book XIII (Compiler) | Test |
| `cinema_pipeline.py` | Multi-segment pipeline | Full Books I-XIII | Working |
| `cinema_full_pipeline.py` | 5-keyframe → FFmpeg video | Books III, IX, XIII | Working |
| `cinema_diffusion_test.py` | Diffusion model testing | Book III (Renderer) | Test |
| `cinema_v2_experiment.py` | MPS optimization v2 | Book III | Experimental |
| `cinema_v3_realvisxl.py` | RealVisXL V5.0 config | Book III + XIII | **Preferred** |
| `controlnet_test.py` | ControlNet integration | Book III | Test |
| `exp1_merged.py` → `exp3_max.py` | MPS stress test, float16→32 | Book III | Experimental |
| `gen5.py` | Generation script v5 | Book XIII | Working |

## MPS Hardware Config (Apple Silicon)
- **Float32 mode** (float16 produces NaN on MPS)
- `enable_model_cpu_offload()` — reduces VRAM pressure
- `enable_attention_slicing()` — required for MPS stability
- Working models: SD-Turbo (4 steps, guidance=0.0), RealVisXL V5.0 (15 steps, preferred)
- CLIP token limit: 77 tokens

## Key Lessons (lessons.md)
1. Prompt structure: character > lighting > spatial > camera (priority order due to CLIP limit)
2. Float32 prevents NaN on MPS
3. SD-Turbo is fast (4 steps) — good for iteration, poor for quality
4. RealVisXL V5.0 is the quality choice (15 steps, CFG=3.5+)
5. `cinema_spec.json` defines Cinematic Specification — typed, structured intermediate format
6. `cinema_assemble.sh` — the assembly script that orchestrates the full pipeline
