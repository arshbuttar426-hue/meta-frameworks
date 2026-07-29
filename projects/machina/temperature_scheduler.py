from dataclasses import dataclass, field

from research_runtime.phase_diagram import PhaseDiagram


@dataclass
class TemperatureSchedule:
    model: str
    task_type: str
    base_temp: float
    phase_boundaries: list[float] = field(default_factory=lambda: [0.0, 2.0])
    adjustment_rules: dict[str, float] = field(default_factory=dict)


SCHEDULES: dict[str, dict[str, TemperatureSchedule]] = {
    "Ornith-9B": {
        "code": TemperatureSchedule(
            model="Ornith-9B", task_type="code",
            base_temp=0.1,
            phase_boundaries=[0.0, 0.3, 0.6, 2.0],
            adjustment_rules={"high_complexity": -0.05, "needs_creativity": +0.1},
        ),
        "analysis": TemperatureSchedule(
            model="Ornith-9B", task_type="analysis",
            base_temp=0.5,
            phase_boundaries=[0.0, 0.3, 0.6, 2.0],
            adjustment_rules={"needs_examples": +0.1},
        ),
        "simple": TemperatureSchedule(
            model="Ornith-9B", task_type="simple",
            base_temp=0.5,
            phase_boundaries=[0.0, 0.3, 0.6, 2.0],
            adjustment_rules={},
        ),
    },
    "VibeThinker-3B": {
        "creative": TemperatureSchedule(
            model="VibeThinker-3B", task_type="creative",
            base_temp=0.9,
            phase_boundaries=[0.0, 0.7, 2.0],
            adjustment_rules={"needs_divergent": +0.1},
        ),
    },
    "Gemma-12B": {
        "any": TemperatureSchedule(
            model="Gemma-12B", task_type="any",
            base_temp=0.3,
            phase_boundaries=[0.0, 2.0],
            adjustment_rules={},
        ),
    },
}


class TemperatureScheduler:
    def __init__(self, phase_diagram: PhaseDiagram):
        self.diagram = phase_diagram

    def get_temperature(self, model: str, task_type: str,
                        complexity: str = "normal",
                        require_deterministic: bool = False) -> float:
        empirical = self.diagram.optimal_config(model, task_type)
        if empirical["confidence"] > 0.5:
            temp = empirical["temperature"]
        else:
            schedule = SCHEDULES.get(model, {}).get(
                task_type,
                SCHEDULES.get(model, {}).get("any", None)
            )
            if not schedule:
                return 0.3
            temp = schedule.base_temp
            for rule, adj in schedule.adjustment_rules.items():
                if rule == "high_complexity" and complexity == "high":
                    temp += adj
                if rule == "needs_creativity" and not require_deterministic:
                    temp += adj
                if rule == "needs_examples":
                    temp += adj
                if rule == "needs_divergent" and not require_deterministic:
                    temp += adj

        boundaries = (
            SCHEDULES.get(model, {}).get(
                task_type,
                TemperatureSchedule(model, task_type, 0.3, [0.0, 2.0], {}),
            ).phase_boundaries
        )
        if len(boundaries) > 2:
            if model == "Ornith-9B" and temp >= 0.7:
                temp = 0.5
            if model == "VibeThinker-3B" and temp < 0.7:
                temp = 0.9

        if require_deterministic:
            temp = min(temp, 0.1)

        return round(temp, 2)
