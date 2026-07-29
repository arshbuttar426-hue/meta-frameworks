"""
SmolLM3-3B tuning — thin wrapper over tune_runner.
"""
from tune_runner import run_tuning

MODEL_NAME = "SmolLM3-3B"
MODEL_ID = "hf.co/ggml-org/SmolLM3-3B-GGUF:Q4_K_M"

CONFIGS = [
    (0.1, 0.5, 100),
    (0.1, 0.9, 200),
    (0.5, 0.7, 300),
    (0.7, 0.9, 400),
    (1.2, 0.95, 500),
]

TASKS = {
    "follow": "Reply with exactly: hello world",
    "list_json": "List 3 primary colors as a JSON array. Return ONLY the array.",
    "sentence": "Write one sentence describing a cat. No extra text.",
    "explain": "Explain what 'recursion' means in exactly 2 sentences.",
}

RESULTS_FILE = "tune_smol_results.json"

if __name__ == "__main__":
    run_tuning(MODEL_NAME, MODEL_ID, CONFIGS, TASKS, RESULTS_FILE)
