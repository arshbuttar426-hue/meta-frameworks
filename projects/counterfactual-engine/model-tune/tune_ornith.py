"""
Ornith-9B tuning — thin wrapper over tune_runner.
"""
from tune_runner import run_tuning

MODEL_NAME = "Ornith-9B"
MODEL_ID = "hf.co/zaakirio/Ornith-1.0-9B-uncensored-GGUF:Q4_K_M"

CONFIGS = [
    (0.1, 0.9, 500),
    (0.5, 0.7, 1000),
    (0.7, 0.9, 1500),
]

TASKS = {
    "follow": "Reply with exactly: hello world",
    "list_json": "List 3 primary colors as a JSON array. Return ONLY the array.",
    "sentence": "Write one sentence describing a cat. No extra text.",
    "class_code": "Write a Python class called BankAccount with: owner, balance, deposit(), withdraw(), __str__. Return ONLY the class.",
    "multi_step": "Two trains leave from the same station at 7 AM. Train A travels east at 60 mph. Train B travels west at 75 mph. At what time will they be 405 miles apart? Show only the answer.",
    "analyze": "Explain the difference between sympathy and empathy in exactly 3 sentences with examples.",
}

RESULTS_FILE = "tune_ornith_results.json"

if __name__ == "__main__":
    run_tuning(MODEL_NAME, MODEL_ID, CONFIGS, TASKS, RESULTS_FILE)
