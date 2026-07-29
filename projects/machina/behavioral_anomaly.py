from datetime import datetime, timezone

from research_runtime.phase_diagram import PhaseDiagram


class BehavioralAnomalyDetector:
    def __init__(self, phase_diagram: PhaseDiagram):
        self.diagram = phase_diagram
        self.anomaly_log: list[dict] = []

    def analyze(self, model: str, task: str, output: str,
                latency_s: float, temperature: float,
                mission_id: str) -> list[dict]:
        drifts = self.diagram.detect_drift(model, task, output, latency_s, temperature)
        anomalies = []
        for drift in drifts:
            anomaly = {
                "model": model, "task": task,
                "drift": drift, "severity": self._classify(drift),
                "mission_id": mission_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            anomalies.append(anomaly)
            self.anomaly_log.append(anomaly)

        if not output and latency_s > 0:
            anomalies.append({
                "model": model, "task": task,
                "drift": "ZERO_OUTPUT_ANOMALY: output is empty but model ran",
                "severity": "CRITICAL",
                "likely_cause": "_strip_tags bug or pipeline lossy stage",
                "mission_id": mission_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return anomalies

    def _classify(self, drift: str) -> str:
        if "ZERO_OUTPUT" in drift or "CRITICAL" in drift:
            return "CRITICAL"
        if "LATENCY_ANOMALY" in drift or "REPETITION" in drift:
            return "WARNING"
        if "THINKING_PATTERN" in drift or "INSTRUCTION_DRIFT" in drift:
            return "INFO"
        return "UNKNOWN"

    def find_bug_patterns(self, pipeline_runs: list[dict]) -> list[dict]:
        zero_output_runs = [
            r for r in pipeline_runs
            if not r.get("output", "") and r.get("latency_s", 0) > 1
        ]
        findings = []
        if len(zero_output_runs) > 3:
            findings.append({
                "pattern": "PERSISTENT_ZERO_OUTPUT",
                "count": len(zero_output_runs),
                "suggestion": "Check _strip_tags and all pipeline lossy stages for silent data loss",
                "severity": "CRITICAL",
            })
        return findings

    def report(self) -> str:
        if not self.anomaly_log:
            return "No behavioral anomalies detected."
        criticals = sum(1 for a in self.anomaly_log if a["severity"] == "CRITICAL")
        warnings = sum(1 for a in self.anomaly_log if a["severity"] == "WARNING")
        infos = sum(1 for a in self.anomaly_log if a["severity"] == "INFO")
        return (
            f"Behavioral Anomaly Report\n"
            f"  Total: {len(self.anomaly_log)}\n"
            f"  Critical: {criticals}\n"
            f"  Warnings: {warnings}\n"
            f"  Info: {infos}\n"
        )
