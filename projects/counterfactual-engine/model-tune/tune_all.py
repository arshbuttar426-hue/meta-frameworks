import sys
import time
sys.path.insert(0, "/Users/arshbuttar/cinema/src")

from trueplan.llm.runner import _call_raw

MODELS = [
    ("Gemma-12B", "hf.co/yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF:Q4_K_M"),
    ("Ornith-9B", "hf.co/zaakirio/Ornith-1.0-9B-uncensored-GGUF:Q4_K_M"),
    ("Qwen3.5-4B", "hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M"),
    ("Phi-4-mini", "hf.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF:Q4_K_M"),
    ("VibeThinker-3B", "hf.co/prithivMLmods/VibeThinker-3B-GGUF:Q4_K_M"),
    ("SmolLM3-3B", "hf.co/ggml-org/SmolLM3-3B-GGUF:Q4_K_M"),
]

PROMPT = """System: Extract narrative events from the scene description. Return ONLY a JSON array. No commentary.

Rules:
- type: ENTER, PLACE, READ, or EXIT
- actor: REQUIRED string, never null
- target: location (null if absent)
- object: item (null if absent)
- surface: surface for PLACE (null if absent)

Extract events from: a hospital with hypnotized nurses"""

EXTREMES = [
    (0.1, 0.1, 300),   # narrow, tight
    (0.1, 0.9, 300),   # cold, open
    (0.5, 0.5, 600),   # balanced
    (0.9, 0.9, 1000),  # hot, open
    (1.5, 0.95, 1500), # max creativity
    (2.0, 0.1, 300),   # max temp, tight
]

for model_label, model_id in MODELS[1:]:  # skip Gemma, already tested
    print(f"\n{'='*70}")
    print(f"Model: {model_label}")
    print(f"{'='*70}")
    for temp, top_p, num_pred in EXTREMES:
        print(f"\n  temp={temp}  top_p={top_p}  tokens={num_pred}")
        try:
            start = time.time()
            r = _call_raw(model_id, PROMPT, temp, top_p, num_pred, 90)
            elapsed = time.time() - start
            print(f"  Time: {elapsed:.1f}s")
            print(f"  Output: {r[:300]}")
        except Exception as e:
            print(f"  FAIL ({time.time()-start:.1f}s): {str(e)[:150]}")