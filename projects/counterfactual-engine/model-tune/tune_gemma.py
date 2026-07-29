"""
Gemma-12B tuning — thin wrapper over tune_runner.
"""
from tune_runner import run_tuning

MODEL_NAME = "Gemma-12B"
MODEL_ID = "hf.co/yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF:Q4_K_M"

CONFIGS = [
    (0.1, 0.9, 500),
    (0.5, 0.7, 1000),
    (0.7, 0.9, 2000),
]

TASKS = {
    "follow": "Reply with exactly: hello world",
    "list_json": "List 3 primary colors as a JSON array. Return ONLY the array.",
    "sentence": "Write one sentence describing a cat. No extra text.",
    "observe_pattern": "Implement the Observer pattern in Python for a weather station that notifies displays when temperature changes. Return ONLY the code.",
    "nested_json": "Write a Python function that transforms a nested JSON (keys with dots) into a flat JSON. Input: {'a.b.c': 1, 'd.e': 2}. Output: {'a': {'b': {'c': 1}, 'e': 2}}.",
    "physics_reason": "If a 2kg ball is dropped from 10m, ignoring air resistance, how fast is it moving just before hitting the ground? Show only the final answer with units.",
    "philosophy": "Explain the trolley problem in exactly 3 sentences. Then state which choice you'd make.",
    "creative": "Write exactly 2 sentences describing a library at midnight where the books are alive but pretending to sleep.",
}

RESULTS_FILE = "tune_gemma_results.json"

if __name__ == "__main__":
    run_tuning(MODEL_NAME, MODEL_ID, CONFIGS, TASKS, RESULTS_FILE)
