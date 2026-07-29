import json
import sys
import time

sys.path.insert(0, "/Users/arshbuttar/cinema/src")

from trueplan.llm.runner import call_stage
from trueplan.llm.prompts import FRONTEND_SYSTEM, INTERPRETATION_SYSTEM, POLICY_SYSTEM, BACKEND_SYSTEM

MODELS = {
    "smollm3": "hf.co/ggml-org/SmolLM3-3B-GGUF:Q4_K_M",
    "phi4mini": "hf.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF:Q4_K_M",
    "vibethinker": "hf.co/prithivMLmods/VibeThinker-3B-GGUF:Q4_K_M",
    "gemma4": "hf.co/yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF:Q4_K_M",
    "qwen4b": "hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M",
    "ornith9b": "hf.co/zaakirio/Ornith-1.0-9B-uncensored-GGUF:Q4_K_M",
}

TESTS = {
    "frontend": (FRONTEND_SYSTEM, "a hospital with hypnotized nurses", 1500),
    "interpretation": (INTERPRETATION_SYSTEM, '[{"id": "NARRATIVE_EVENT_1", "type": "ARRIVAL", "actor": "nurse", "target": "hospital"}]', 2000),
    "policy": (POLICY_SYSTEM, "Nurse arrives at hospital.\nEmotions: anticipation, tension\nSet policy.", 1000),
    "backend": (BACKEND_SYSTEM, 'Scene: SCENE_001\nTone: tense\nPacing: slow_burn\n\nShot SHOT_001: MEDIUM — nurse enters hospital\n  Camera: STATIC | 50mm\n  Duration: 5s\n  Lighting: Soft', 3000),
}


def benchmark(model_name, model_id, task_name, system, user, num_predict):
    try:
        start = time.time()
        result = call_stage(
            stage="frontend",  # use frontend stage config but override model
            system_prompt=system,
            user_content=user,
            num_predict=num_predict,
            timeout=60,
        )
        elapsed = time.time() - start
        # Check if result is valid
        valid = False
        if task_name == "frontend":
            valid = isinstance(result, list) and len(result) > 0 and all(isinstance(e, dict) and e.get("actor") for e in result)
        elif task_name == "interpretation":
            valid = isinstance(result, list) and len(result) > 0 and all(isinstance(a, dict) and a.get("emotion") for a in result)
        elif task_name == "policy":
            valid = isinstance(result, dict) and result.get("primary_tone")
        elif task_name == "backend":
            valid = isinstance(result, dict) and result.get("prompt")
        return {"valid": valid, "elapsed": round(elapsed, 2), "preview": str(result)[:200]}
    except Exception as e:
        return {"valid": False, "elapsed": 0, "error": str(e)[:100]}


print("=" * 80)
print("OLLAMA MODEL BENCHMARK")
print("=" * 80)

for task_name, (system, user, num_predict) in TESTS.items():
    print(f"\n{'=' * 40}")
    print(f"TASK: {task_name}")
    print(f"{'=' * 40}")
    for model_label, model_id in MODELS.items():
        # Monkey-patch model map temporarily
        from trueplan.llm import runner
        original_map = dict(runner.MODEL_MAP)
        runner.MODEL_MAP["frontend"] = model_id
        try:
            result = benchmark(model_label, model_id, task_name, system, user, num_predict)
            status = "✓ VALID" if result.get("valid") else "✗ FAIL"
            print(f"  {model_label:12s} {status:10s} {result.get('elapsed', 0):5.1f}s  {result.get('preview', result.get('error', ''))[:80]}")
        finally:
            runner.MODEL_MAP = original_map

print("\n" + "=" * 80)
