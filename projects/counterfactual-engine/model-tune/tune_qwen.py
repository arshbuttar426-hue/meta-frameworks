"""
Qwen3.5-4B tuning — thin wrapper over tune_runner.
"""
from tune_runner import run_tuning

MODEL_NAME = "Qwen3.5-4B"
MODEL_ID = "hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M"

CONFIGS = [
    (0.1, 0.5, 150),
    (0.1, 0.9, 300),
    (0.5, 0.7, 500),
    (0.7, 0.9, 800),
    (1.2, 0.95, 1000),
]

TASKS = {
    "follow": "Reply with exactly: hello world",
    "list_json": "List 3 primary colors as a JSON array. Return ONLY the array.",
    "sentence": "Write one sentence describing a cat. No extra text.",
    "explain": "Explain what 'recursion' means in exactly 2 sentences.",
    "palindrome": "Write a Python function that checks if a string is a palindrome. Return ONLY the function.",
    "translate": "Translate 'Hello, how are you?' to Spanish. Return ONLY the translation.",
    "solve": "Solve for x: 3x + 7 = 22. Show only the answer.",
}

RESULTS_FILE = "tune_qwen_results.json"

if __name__ == "__main__":
    run_tuning(MODEL_NAME, MODEL_ID, CONFIGS, TASKS, RESULTS_FILE)
