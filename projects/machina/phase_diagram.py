import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class PhasePoint:
    model: str
    task: str
    temperature: float
    top_p: float
    max_tokens: int
    latency_s: float
    ok: bool
    has_thinking_wrapper: bool
    repetition_ratio: float
    output_hash: str


@dataclass
class PhaseRegion:
    model: str
    task: str
    temp_min: float
    temp_max: float
    delivery_rate: float
    avg_latency_s: float
    has_thinking: bool
    repetition_risk: float


BENCHMARK_PATHS = [
    "/Users/arshbuttar/modeltune/tune_gemma_results.json",
    "/Users/arshbuttar/modeltune/tune_ornith_results.json",
    "/Users/arshbuttar/modeltune/tune_phi_results.json",
    "/Users/arshbuttar/modeltune/tune_qwen_results.json",
    "/Users/arshbuttar/modeltune/tune_smol_results.json",
    "/Users/arshbuttar/modeltune/tune_vibe_results.json",
]

KNOWN_MODELS = [
    "Gemma-12B", "Phi-4-mini", "Ornith-9B",
    "SmolLM3-3B", "VibeThinker-3B", "Qwen3.5-4B",
]


class PhaseDiagram:
    def __init__(self, benchmark_paths: Optional[list[str]] = None):
        self.points: list[PhasePoint] = []
        self.regions: dict[tuple[str, str], list[PhaseRegion]] = {}
        self.benchmark_hash: str = ""
        paths = benchmark_paths or BENCHMARK_PATHS
        self._load_benchmarks(paths)
        self._compute_regions()

    def _load_benchmarks(self, paths: list[str]) -> None:
        combined_hash_input = b""
        for path in paths:
            p = Path(path)
            if not p.exists():
                continue
            raw = p.read_bytes()
            combined_hash_input += hashlib.sha256(raw).digest()
            data = json.loads(raw)
            for entry in data:
                output = entry.get("output", "") or ""
                self.points.append(PhasePoint(
                    model=entry["model"],
                    task=entry["task"],
                    temperature=entry.get("temp", 0.5),
                    top_p=entry.get("top_p", 0.9),
                    max_tokens=entry.get("tokens", 500),
                    latency_s=entry.get("time", 0.0),
                    ok=entry.get("ok", False),
                    has_thinking_wrapper="<think>" in output,
                    repetition_ratio=self._measure_repetition(output),
                    output_hash=hashlib.sha256(output.encode()).hexdigest()[:16],
                ))
        self.benchmark_hash = hashlib.sha256(combined_hash_input).hexdigest()

    def _compute_regions(self) -> None:
        keys = {(p.model, p.task) for p in self.points}
        for (model, task) in keys:
            pts = [p for p in self.points if p.model == model and p.task == task]
            if not pts:
                continue
            pts.sort(key=lambda p: p.temperature)
            boundaries = [0.0]
            for i in range(1, len(pts)):
                if (pts[i].ok != pts[i - 1].ok
                        or pts[i].has_thinking_wrapper != pts[i - 1].has_thinking_wrapper
                        or pts[i].latency_s > pts[i - 1].latency_s * 2):
                    boundaries.append(pts[i].temperature)
            boundaries.append(2.0)
            regions = []
            for j in range(len(boundaries) - 1):
                region_pts = [p for p in pts
                              if boundaries[j] <= p.temperature < boundaries[j + 1]]
                if not region_pts:
                    continue
                regions.append(PhaseRegion(
                    model=model,
                    task=task,
                    temp_min=boundaries[j],
                    temp_max=boundaries[j + 1],
                    delivery_rate=sum(1 for p in region_pts if p.ok) / max(len(region_pts), 1),
                    avg_latency_s=sum(p.latency_s for p in region_pts) / max(len(region_pts), 1),
                    has_thinking=any(p.has_thinking_wrapper for p in region_pts),
                    repetition_risk=sum(p.repetition_ratio for p in region_pts) / max(len(region_pts), 1),
                ))
            self.regions[(model, task)] = regions

    def optimal_config(self, model: str, task: str) -> dict:
        key = (model, task)
        if key not in self.regions:
            return {"model": model, "temperature": 0.5, "confidence": 0.0}
        regions = self.regions[key]
        best = max(regions, key=lambda r: (r.delivery_rate, -r.avg_latency_s))
        optimal_temp = (best.temp_min + best.temp_max) / 2
        return {
            "model": model,
            "task": task,
            "temperature": optimal_temp,
            "delivery_rate": best.delivery_rate,
            "repetition_risk": best.repetition_risk,
            "confidence": best.delivery_rate * (1 - best.repetition_risk),
        }

    def best_model_for_task(self, task: str) -> dict:
        candidates = []
        for model in KNOWN_MODELS:
            config = self.optimal_config(model, task)
            if config["confidence"] > 0:
                candidates.append(config)
        if not candidates:
            return {"model": "Gemma-12B", "temperature": 0.3, "confidence": 0.5}
        return max(candidates, key=lambda c: c["confidence"])

    def detect_drift(self, model: str, task: str, production_output: str,
                     production_latency: float, production_temp: float) -> list[str]:
        key = (model, task)
        if key not in self.regions:
            return ["No benchmark data for this model+task"]
        benchmark_pts = [p for p in self.points if p.model == model and p.task == task]
        if not benchmark_pts:
            return ["No benchmark points"]
        closest = min(benchmark_pts, key=lambda p: abs(p.temperature - production_temp))
        drifts = []
        if production_latency > closest.latency_s * 3:
            drifts.append(
                f"LATENCY_ANOMALY: {production_latency:.1f}s vs benchmark {closest.latency_s:.1f}s"
            )
        has_think = "<think>" in production_output
        if has_think != closest.has_thinking_wrapper:
            drifts.append(
                f"THINKING_PATTERN_SHIFT: expected wrapper={closest.has_thinking_wrapper}, got={has_think}"
            )
        rep = self._measure_repetition(production_output)
        if rep > 0.5 and closest.repetition_ratio < 0.1:
            drifts.append(
                f"REPETITION_ANOMALY: production repetition {rep:.2f} vs benchmark {closest.repetition_ratio:.2f}"
            )
        if task == "follow" and closest.ok:
            if production_output.strip() != "hello world":
                drifts.append(
                    f"INSTRUCTION_DRIFT: expected 'hello world', got '{production_output.strip()[:50]}'"
                )
        return drifts

    def verify_benchmark_integrity(self) -> bool:
        combined = b""
        for path in BENCHMARK_PATHS:
            p = Path(path)
            if not p.exists():
                return False
            combined += hashlib.sha256(p.read_bytes()).digest()
        return hashlib.sha256(combined).hexdigest() == self.benchmark_hash

    def ingest_production_point(self, model: str, task: str, temperature: float,
                                 top_p: float, max_tokens: int, latency_s: float,
                                 ok: bool, output: str) -> None:
        self.points.append(PhasePoint(
            model=model,
            task=task,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            latency_s=latency_s,
            ok=ok,
            has_thinking_wrapper="<think>" in output,
            repetition_ratio=self._measure_repetition(output),
            output_hash=hashlib.sha256(output.encode()).hexdigest()[:16],
        ))
        if len(self.points) % 100 == 0:
            self._compute_regions()

    def _measure_repetition(self, text: str) -> float:
        if len(text) < 100:
            return 0.0
        ngrams: set[str] = set()
        total = 0
        for i in range(len(text) - 20):
            ngrams.add(text[i:i + 20])
            total += 1
        return 1.0 - (len(ngrams) / max(total, 1))
