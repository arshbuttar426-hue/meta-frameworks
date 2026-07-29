import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class PipelineBuilder:
    def __init__(self, scheduler: Any = None):
        self.scheduler = scheduler
        self._stages: list[dict] = []

    def add_stage(self, capability: str, inputs: Optional[dict] = None) -> PipelineBuilder:
        self._stages.append({"capability": capability, "inputs": inputs or {}})
        return self

    def build(self) -> list[dict]:
        return self._stages
