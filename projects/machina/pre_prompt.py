"""Pre-deployment hook: validate pipeline config against empirical phase diagram."""

import json
import sys

KNOWN_DEAD_CONFIGS = [
    ("VibeThinker-3B", "any", "temp<0.7", "Analysis paralysis — never delivers output"),
    ("Qwen3.5-4B", "math", "any", "100% failure rate on math tasks"),
    ("Qwen3.5-4B", "translate", "any", "100% failure rate on translation"),
    ("Ornith-9B", "any", "temp>=0.7", "Repetition loop risk (114.2s observed)"),
]


def check_chain_config(chain_config: dict) -> list[str]:
    violations = []
    for role_name, config in chain_config.items():
        model_key = config.get("model_key", "")
        temperature = config.get("temperature", 0.5)
        task_type = config.get("task_type", "any")

        for dead_model, dead_task, dead_temp_cond, reason in KNOWN_DEAD_CONFIGS:
            if dead_model not in model_key:
                continue
            if dead_task != "any" and dead_task != task_type:
                continue
            if dead_temp_cond.startswith("temp<") and temperature < float(dead_temp_cond.split("<")[1]):
                continue
            if dead_temp_cond.startswith("temp>=") and temperature >= float(dead_temp_cond.split(">=")[1]):
                continue
            if dead_temp_cond == "any":
                pass
            violations.append(
                f"DEAD CONFIG: {model_key} @ T={temperature} for {task_type}: {reason}"
            )

    return violations


def run_strip_tags_test(llm_client) -> tuple[bool, str]:
    """Send 'hello world' through the pipeline and verify it emerges intact."""
    try:
        result = llm_client.complete(
            model_key="phi4_mini_reviewer",
            prompt="Reply with exactly: hello world",
            temperature=0.1,
        )
        output = result.text.strip() if result.text else ""
        if output == "hello world":
            return True, "strip_tags test passed"
        return False, f"strip_tags test failed: got '{output[:50]}'"
    except Exception as e:
        return False, f"strip_tags test error: {e}"


if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "chain_config.json"
    with open(config_path) as f:
        config = json.load(f)
    violations = check_chain_config(config)
    if violations:
        print("✗ CHAIN CONFIG VIOLATIONS FOUND:")
        for v in violations:
            print(f"  ✗ {v}")
        sys.exit(1)
    else:
        print("✓ Chain config is safe — no known dead configurations")
        sys.exit(0)
