from typing import Any


class GemmaComposer:
    def __init__(self, llm: Any = None, journal: Any = None):
        self.llm = llm
        self.journal = journal

    def plan_mission(self, question: str) -> dict:
        return {"objective": question, "sub_tasks": [question]}
