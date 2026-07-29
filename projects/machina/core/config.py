from dataclasses import dataclass, field


@dataclass
class LLMProviderConfig:
    provider: str = "mock"
    host: str = "http://localhost:11434"
    model_map: dict = field(default_factory=dict)
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 120
