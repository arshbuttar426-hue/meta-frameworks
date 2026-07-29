from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG_PATH = Path.home() / ".research_lab" / "config.json"


@dataclass
class LLMProviderConfig:
    provider: str = "ollama"
    host: str = "http://localhost:11434"
    api_key: Optional[str] = None
    inference_chain: list[str] = field(default_factory=lambda: [
        "smolm3_research_associate",
        "vibe_thinker",
        "phi4_mini_reviewer",
        "gemma_composer",
    ])
    model_map: dict[str, str] = field(default_factory=lambda: {
        "gemma_composer": "hf.co/yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF:Q4_K_M",
        "smolm3_research_associate": "hf.co/ggml-org/SmolLM3-3B-GGUF:Q4_K_M",
        "phi4_mini_reviewer": "hf.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF:Q4_K_M",
        "vibe_thinker": "hf.co/prithivMLmods/VibeThinker-3B-GGUF:Q4_K_M",
        "ornith_anarchist": "Ornith-9B-uncensored",
    })
    timeout: int = 60
    max_tokens: int = 2048
    temperature: float = 0.7


@dataclass
class StorageConfig:
    db_path: str = str(Path.home() / ".research_lab" / "lab.db")
    journal_path: str = str(Path.home() / ".research_lab" / "journal")
    export_path: str = str(Path.home() / ".research_lab" / "exports")


@dataclass
class LabConfig:
    lab_name: str = "research-lab"
    storage: StorageConfig = field(default_factory=StorageConfig)
    llm: LLMProviderConfig = field(default_factory=LLMProviderConfig)
    max_debate_rounds: int = 5
    confidence_threshold: float = 0.7
    log_level: str = "INFO"
    data_dir: str = field(default_factory=lambda: str(Path.home() / ".research_lab"))


def load_config(path: Optional[str] = None) -> LabConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if config_path.exists():
        with open(config_path) as f:
            data = json.load(f)
        storage_data = data.get("storage", {})
        llm_data = data.get("llm", {})
        return LabConfig(
            lab_name=data.get("lab_name", "research-lab"),
            storage=StorageConfig(**storage_data) if isinstance(storage_data, dict) else StorageConfig(),
            llm=LLMProviderConfig(**llm_data) if isinstance(llm_data, dict) else LLMProviderConfig(),
            max_debate_rounds=data.get("max_debate_rounds", 5),
            confidence_threshold=data.get("confidence_threshold", 0.7),
            log_level=data.get("log_level", "INFO"),
            data_dir=data.get("data_dir", str(Path.home() / ".research_lab")),
        )
    return LabConfig()


def save_config(config: LabConfig, path: Optional[str] = None) -> None:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(asdict(config), f, indent=2, default=str)


def ensure_dirs(config: LabConfig) -> None:
    data_dir = Path(config.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    Path(config.storage.journal_path).mkdir(parents=True, exist_ok=True)
    Path(config.storage.export_path).mkdir(parents=True, exist_ok=True)
    db_dir = Path(config.storage.db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
