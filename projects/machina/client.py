from __future__ import annotations
import json
import logging
import subprocess
from typing import Optional

from core.config import LLMProviderConfig
from ..lib.json_extract import extract_json as _json_extract

logger = logging.getLogger(__name__)


class LLMResult:
    def __init__(self, text: str, raw: Optional[dict] = None,
                 success: bool = True, error: Optional[str] = None):
        self.text = text
        self.raw = raw or {}
        self.success = success
        self.error = error


class LLMClient:
    def __init__(self, config: LLMProviderConfig):
        self.config = config
        self._provider = self._init_provider()

    def _init_provider(self):
        if self.config.provider == "ollama":
            return OllamaProvider(self.config)
        elif self.config.provider == "llamacpp":
            return LlamaCppProvider(self.config)
        elif self.config.provider == "mock":
            return MockProvider(self.config)
        else:
            logger.warning(f"Unknown provider {self.config.provider}, using mock")
            return MockProvider(self.config)

    def complete(self, model_key: str, prompt: str,
                 system: Optional[str] = None,
                 temperature: Optional[float] = None,
                 top_p: Optional[float] = None,
                 top_k: Optional[int] = None,
                 max_tokens: Optional[int] = None) -> LLMResult:
        model = self.config.model_map.get(model_key, model_key)
        temp = temperature if temperature is not None else self.config.temperature
        return self._provider.complete(
            model=model,
            prompt=prompt,
            system=system,
            temperature=temp,
            max_tokens=max_tokens or self.config.max_tokens,
            top_p=top_p,
            top_k=top_k,
        )

    @staticmethod
    def _extract_json(text: str) -> str:
        return _json_extract(text)

    def structured(self, model_key: str, prompt: str,
                   system: Optional[str] = None,
                   temperature: float = 0.3,
                   top_p: Optional[float] = None,
                   top_k: Optional[int] = None) -> dict:
        result = self.complete(
            model_key=model_key,
            prompt=prompt + "\n\nRespond with valid JSON only, no markdown formatting.",
            system=system,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )
        if not result.success:
            return {"error": result.error, "raw": result.text}
        text = self._extract_json(result.text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw": result.text}


class OllamaProvider:
    def __init__(self, config: LLMProviderConfig):
        self.config = config

    def complete(self, model: str, prompt: str,
                 system: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 2048,
                 top_p: Optional[float] = None,
                 top_k: Optional[int] = None) -> LLMResult:
        import urllib.request
        import urllib.error

        options = {
            "temperature": temperature,
            "num_predict": max_tokens,
        }
        if top_p is not None:
            options["top_p"] = top_p
        if top_k is not None:
            options["top_k"] = top_k

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if system:
            payload["system"] = system

        url = f"{self.config.host}/api/generate"
        data = json.dumps(payload).encode()

        try:
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                result = json.loads(resp.read().decode())
            return LLMResult(
                text=result.get("response", ""),
                raw=result,
            )
        except urllib.error.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e.code} {e.reason}")
            return LLMResult(text="", success=False, error=str(e))
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            return LLMResult(text="", success=False, error=str(e))


class LlamaCppProvider:
    def __init__(self, config: LLMProviderConfig):
        self.config = config

    def complete(self, model: str, prompt: str,
                 system: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 2048) -> LLMResult:
        try:
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            result = subprocess.run(
                [
                    "llama-cli",
                    "--model", model,
                    "--prompt", full_prompt,
                    "--temp", str(temperature),
                    "--n-predict", str(max_tokens),
                    "--no-display-prompt",
                ],
                capture_output=True, text=True, timeout=self.config.timeout,
            )
            return LLMResult(
                text=result.stdout.strip(),
                raw={"returncode": result.returncode},
                success=result.returncode == 0,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return LLMResult(text="", success=False, error=str(e))


class MockProvider:
    def __init__(self, config: LLMProviderConfig):
        self.config = config

    def complete(self, model: str, prompt: str,
                 system: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 2048) -> LLMResult:
        logger.info(f"[MOCK] {model} received prompt ({len(prompt)} chars)")
        return LLMResult(
            text=(
                f"[Mock response from {model}]\n"
                f"Acknowledged. Processing research objective.\n"
                f"Confidence: 0.5\n"
                f"Key findings will be documented following analysis."
            ),
            raw={"model": model, "mock": True},
        )
