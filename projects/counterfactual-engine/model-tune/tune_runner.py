"""
tune_runner — Shared Ollama benchmarking module.

Extracted from duplicated logic across tune_phi.py, tune_gemma.py,
tune_smol.py, tune_qwen.py, tune_vibe.py, tune_ornith.py.

Domain 1 (Mycelial Distribution): One shared runner, model-specific configs as data.
Domain -1 (Parsimony): Only what's truly duplicated — no over-abstraction.
"""

import json
import time
import urllib.request
import urllib.error
from typing import Any


OLLAMA_URL = "http://localhost:11434/api/generate"


def ollama_call(
    model_id: str,
    prompt: str,
    temperature: float = 0.7,
    top_p: float = 0.9,
    num_predict: int = 500,
) -> str | None:
    """Call an Ollama model and return the raw response text.

    Args:
        model_id: The Ollama model identifier (e.g. "hf.co/...:Q4_K_M").
        prompt: The text prompt to send.
        temperature: Sampling temperature (0.0–2.0).
        top_p: Nucleus sampling threshold (0.0–1.0).
        num_predict: Maximum tokens to generate.

    Returns:
        The model's response text, stripped of leading/trailing whitespace,
        or None if the request failed.
    """
    payload = json.dumps({
        "model": model_id,
        "prompt": prompt,
        "temperature": temperature,
        "top_p": top_p,
        "num_predict": num_predict,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("response", "").strip() or None
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, OSError) as exc:
        print(f"  [ERROR] Ollama call failed: {exc}")
        return None


def run_tuning(
    model_name: str,
    model_id: str,
    configs: list[tuple[float, float, int]],
    tasks: dict[str, str],
    results_file: str,
) -> None:
    """Run a tuning grid-search over the given tasks and configs.

    For each (task, config) combination, calls the Ollama model, times the
    inference, and saves all results to a JSON file.

    Args:
        model_name: Human-readable label for logging (e.g. "Phi-4-mini").
        model_id:  Ollama model identifier.
        configs:   List of (temperature, top_p, num_predict) tuples.
        tasks:     Dictionary mapping task name -> prompt string.
        results_file: Path to write the JSON results file.
    """
    print(f"\n{'='*60}")
    print(f"  Tuning: {model_name}  ({model_id})")
    print(f"  Tasks: {len(tasks)}  Configs: {len(configs)}")
    print(f"{'='*60}")

    results: dict[str, list[dict[str, Any]]] = {name: [] for name in tasks}
    total = len(tasks) * len(configs)
    done = 0

    for task_name, task_prompt in tasks.items():
        print(f"\n  --- {task_name} ---")

        for temp, top_p, num_pred in configs:
            label = f"T={temp}, P={top_p}, N={num_pred}"
            print(f"    [{label}] ", end="", flush=True)

            start = time.time()
            response = ollama_call(model_id, task_prompt, temp, top_p, num_pred)
            elapsed = time.time() - start

            entry: dict[str, Any] = {
                "temperature": temp,
                "top_p": top_p,
                "num_predict": num_pred,
                "response": response,
                "elapsed_seconds": round(elapsed, 2),
                "error": None,
            }

            if response is None:
                entry["error"] = "Request failed (see above)"
                print("FAIL")
            else:
                preview = response[:80].replace("\n", " ")
                print(f"OK ({elapsed:.1f}s) — {preview}...")

            results[task_name].append(entry)
            done += 1

    # Save results
    output = {
        "model_name": model_name,
        "model_id": model_id,
        "total_runs": done,
        "results": results,
    }
    with open(results_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n  Done. {done}/{total} runs saved to {results_file}")


if __name__ == "__main__":
    print("tune_runner — shared module. Import from your tune scripts.")
