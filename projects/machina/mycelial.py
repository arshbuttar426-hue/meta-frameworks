from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class InferenceTask:
    mission_id: str
    query: str
    input_fields: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeOutput:
    role: str
    output: str
    confidence: float = 0.5
    evidence_refs: list[str] = field(default_factory=list)


class MycelialNode:
    def __init__(self, role: str, model_key: str, temperature: float,
                 execute_fn: Callable[[InferenceTask], str],
                 interest_signals: Optional[list[str]] = None):
        self.role = role
        self.model_key = model_key
        self.temperature = temperature
        self.execute_fn = execute_fn
        self.interest_signals = interest_signals or []

    def should_respond(self, task: InferenceTask) -> bool:
        if not self.interest_signals:
            return True
        return any(signal in task.input_fields for signal in self.interest_signals)

    def execute(self, task: InferenceTask) -> NodeOutput:
        try:
            output = self.execute_fn(task)
            return NodeOutput(role=self.role, output=output)
        except Exception as e:
            logger.warning(f"MycelialNode '{self.role}' failed: {e}")
            return NodeOutput(role=self.role, output=f"", confidence=0.0)


class MycelialRouter:
    def __init__(self, max_workers: int = 4):
        self.nodes: dict[str, MycelialNode] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def register(self, node: MycelialNode) -> None:
        with self._lock:
            self.nodes[node.role] = node

    def distribute(self, task: InferenceTask,
                   result_callback: Optional[Callable[[NodeOutput], None]] = None) -> list[NodeOutput]:
        matches = [
            node for node in self.nodes.values()
            if node.should_respond(task)
        ]
        if not matches:
            logger.info(f"No mycelial nodes matched task fields: {task.input_fields}")
            return []

        futures = {
            self._executor.submit(node.execute, task): node
            for node in matches
        }

        results: list[NodeOutput] = []
        for future in as_completed(futures):
            try:
                output = future.result()
                results.append(output)
                if result_callback:
                    result_callback(output)
            except Exception as e:
                logger.warning(f"Mycelial future failed: {e}")

        return results

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
