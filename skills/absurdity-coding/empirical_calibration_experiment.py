#!/usr/bin/env python3
"""Empirical Calibration Experiment for the Absurdity Protocol.

A/B test: protocol-enriched pipeline vs vanilla pipeline across 100 generation tasks
with blind human evaluation. See SKILL.md section "Empirical Calibration Experiment"
for full protocol specification.

Usage:
    python empirical_calibration_experiment.py --tasks tasks.json --output ./results
"""

import json
import random
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class StageRecord:
    condition: str
    task_id: int
    stage: str
    input_fields: dict
    output_text: str
    latency_ms: float


@dataclass
class ExperimentConfig:
    """Configuration for one experimental condition."""
    name: str
    model_key: str
    temperature: float
    domains_enabled: list[str]
    compiler_mode: str
    use_homeostat: bool
    use_merkle: bool
    use_auction: bool


VANILLA_CONFIG = ExperimentConfig(
    name="vanilla",
    model_key="gemma-4-12b",
    temperature=1.5,
    domains_enabled=[],
    compiler_mode="prose",
    use_homeostat=False,
    use_merkle=False,
    use_auction=False,
)

PROTOCOL_CONFIG = ExperimentConfig(
    name="protocol",
    model_key="gemma-4-12b",
    temperature=0.3,
    domains_enabled=[
        "mycelial", "entropy", "catalyst", "biomechanics",
        "philosophy", "world_schema", "homeostat", "auction", "merkle",
    ],
    compiler_mode="catalytic",
    use_homeostat=True,
    use_merkle=True,
    use_auction=True,
)


# ---------------------------------------------------------------------------
# Experiment logger
# ---------------------------------------------------------------------------

class ExperimentLogger:
    """Logs every stage output for both conditions."""

    def __init__(self):
        self.logs: list[StageRecord] = []

    def record(
        self,
        condition: str,
        task_id: int,
        stage: str,
        input_fields: dict,
        output_text: str,
        latency_ms: float,
    ):
        self.logs.append(StageRecord(condition, task_id, stage, input_fields, output_text, latency_ms))

    def get_irr(self, condition: str, task_id: int) -> float:
        """Compute Information Retention Ratio for a specific condition+task across all stages."""
        records = [r for r in self.logs if r.condition == condition and r.task_id == task_id]
        total_input = sum(len(r.input_fields) for r in records)
        total_preserved = sum(
            1
            for r in records
            for k, v in r.input_fields.items()
            if str(v) in r.output_text
        )
        return total_preserved / max(total_input, 1)

    def summary(self) -> dict:
        """Aggregate IRR and latency per condition across all tasks."""
        conditions = set(r.condition for r in self.logs)
        result = {}
        for cond in conditions:
            cond_logs = [r for r in self.logs if r.condition == cond]
            task_ids = set(r.task_id for r in cond_logs)
            irrs = [self.get_irr(cond, tid) for tid in task_ids]
            latencies = [r.latency_ms for r in cond_logs]
            result[cond] = {
                "mean_irr": statistics.mean(irrs),
                "std_irr": statistics.stdev(irrs) if len(irrs) > 1 else 0.0,
                "mean_latency_ms": statistics.mean(latencies),
                "total_tasks": len(task_ids),
                "total_stage_records": len(cond_logs),
            }
        return result


# ---------------------------------------------------------------------------
# Anonymizer
# ---------------------------------------------------------------------------

class Anonymizer:
    """Strips condition-identifying metadata from pipeline outputs."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.id_map: dict[str, str] = {}

    def assign_id(self, condition: str, task_id: int) -> str:
        key = f"{condition}_{task_id}"
        if key not in self.id_map:
            self.id_map[key] = f"{self.rng.randint(1000, 9999)}"
        return self.id_map[key]

    def strip_metadata(self, output_text: str) -> str:
        lines = [
            line
            for line in output_text.split("\n")
            if not line.startswith("[CONDITION:")
            and not line.startswith("[PIPELINE:")
            and not line.startswith("[STAGE:")
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

def randomized_configs(configs: list[ExperimentConfig], seed: int) -> list[ExperimentConfig]:
    rng = random.Random(seed)
    shuffled = list(configs)
    rng.shuffle(shuffled)
    return shuffled


def save_anonymized(
    output: dict,
    condition: str,
    task_id: int,
    output_dir: Path,
    anonymizer: Anonymizer,
):
    eval_id = anonymizer.assign_id(condition, task_id)
    safe_text = anonymizer.strip_metadata(output.get("final_text", ""))
    record = {
        "eval_id": eval_id,
        "task_id": task_id,
        "text": safe_text,
        "latency_ms": output.get("latency_ms", 0),
    }
    path = output_dir / f"task_{task_id}_cond_{condition}.json"
    path.write_text(json.dumps(record, indent=2))


def run_experiment(
    tasks_path: str,
    configs: list[ExperimentConfig],
    output_dir: str,
):
    logger = ExperimentLogger()
    anonymizer = Anonymizer()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    tasks = json.loads(Path(tasks_path).read_text())

    for task in tasks:
        for config in randomized_configs(configs, seed=task["task_id"]):
            # Placeholder: replace with actual pipeline call
            from pipeline import run as run_pipeline

            pipeline_output = run_pipeline(task["prompt"], config)

            for stage_name, stage_output in pipeline_output.get("stages", {}).items():
                logger.record(
                    condition=config.name,
                    task_id=task["task_id"],
                    stage=stage_name,
                    input_fields=task.get("structured_spec", {}),
                    output_text=stage_output.get("text", ""),
                    latency_ms=stage_output.get("latency_ms", 0.0),
                )

            save_anonymized(
                pipeline_output,
                config.name,
                task["task_id"],
                out,
                anonymizer,
            )

    result = logger.summary()
    result_path = out / "experiment_summary.json"
    result_path.write_text(json.dumps(result, indent=2))
    print(f"Experiment complete. Summary written to {result_path}")
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Absurdity Protocol Empirical Calibration Experiment")
    parser.add_argument("--tasks", required=True, help="Path to tasks.json")
    parser.add_argument("--output", default="./results", help="Output directory for results")
    parser.add_argument("--condition", choices=["vanilla", "protocol", "both"], default="both")
    args = parser.parse_args()

    configs = []
    if args.condition in ("vanilla", "both"):
        configs.append(VANILLA_CONFIG)
    if args.condition in ("protocol", "both"):
        configs.append(PROTOCOL_CONFIG)

    run_experiment(args.tasks, configs, args.output)
