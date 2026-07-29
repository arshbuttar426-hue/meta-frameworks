"""
Phi-4-mini tuning — thin wrapper over tune_runner.
"""
from tune_runner import run_tuning

MODEL_NAME = "Phi-4-mini"
MODEL_ID = "hf.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF:Q4_K_M"

CONFIGS = [
    (0.1, 0.9, 500),
    (0.5, 0.7, 1000),
    (0.7, 0.9, 1500),
    (1.0, 0.9, 2000),
    (1.5, 0.95, 3000),
]

TASKS = {
    "follow": "Reply with exactly: hello world",
    "list_json": "List 3 primary colors as a JSON array. Return ONLY the array.",
    "sentence": "Write one sentence describing a cat. No extra text.",
    "explain": "Explain what 'recursion' means in exactly 2 sentences.",
    "class_code": "Write a Python class called BankAccount with: owner, balance, deposit(), withdraw(), __str__. Return ONLY the class.",
    "translate": "Translate 'Hello, how are you?' to French. Return ONLY the translation.",
    "solve": "Solve for x: 3x + 7 = 22. Show only the answer.",
}

RESULTS_FILE = "tune_phi_results.json"

if __name__ == "__main__":
    run_tuning(MODEL_NAME, MODEL_ID, CONFIGS, TASKS, RESULTS_FILE)
