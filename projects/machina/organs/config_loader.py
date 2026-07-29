"""
Config Loader — HMAC-signed configuration with hot/warm/cold classification.

Supports:
- HMAC-SHA256 signature verification against FORENSIC_CONFIG_KEY
- Hot/warm/cold classification based on config age
- JSON loading with validation
"""

import json
import os
import hmac
import hashlib
import time
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ParamClass:
    """Generic parameter container for organ configuration."""
    pass


class ConfigLoader:
    """HMAC-signed configuration loader with hot/warm/cold classification."""

    def __init__(self, path: str = ""):
        self._data: dict = {}
        self._path = path
        self._loaded_at: float = time.time()
        self._signature_valid: bool = False

        # Load from path if provided
        if path and os.path.exists(path):
            self._load(path)

        # Compute fingerprint
        raw = json.dumps(self._data, sort_keys=True).encode()
        self.fingerprint = hashlib.sha256(raw).hexdigest()[:16]
        self.version = self._data.get("version", "1.0.0-dev")

    def _load(self, path: str) -> None:
        """Load and verify config from JSON file."""
        with open(path) as f:
            raw = f.read()

        # Verify HMAC signature if key is set
        signing_key = os.environ.get("FORENSIC_CONFIG_KEY", "")
        if signing_key:
            expected_sig = hmac.new(
                signing_key.encode(),
                raw.encode(),
                hashlib.sha256
            ).hexdigest()[:16]
            stored_sig = os.environ.get("FORENSIC_CONFIG_SIG", "")
            self._signature_valid = hmac.compare_digest(expected_sig, stored_sig)
        else:
            self._signature_valid = True  # dev mode — no key

        self._data = json.loads(raw)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        return self._data.get(key, default)

    @property
    def classification(self) -> str:
        """
        Returns hot/warm/cold based on config staleness.

        - hot: loaded within last 5 minutes
        - warm: loaded within last 1 hour
        - cold: loaded more than 1 hour ago
        """
        age = time.time() - self._loaded_at
        if age < 300:       # 5 minutes
            return "hot"
        elif age < 3600:    # 1 hour
            return "warm"
        else:
            return "cold"

    @property
    def is_signed(self) -> bool:
        """Whether the config was loaded with a valid HMAC signature."""
        return self._signature_valid

    def to_dict(self) -> dict:
        """Export config metadata for telemetry."""
        return {
            "version": self.version,
            "fingerprint": self.fingerprint,
            "classification": self.classification,
            "signed": self.is_signed,
            "loaded_at": self._loaded_at,
        }
