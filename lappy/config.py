"""Local configuration. No network endpoint except loopback is permitted."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Allowed local model tags — only downloaded local models, no cloud variants.
ALLOWED_MODELS = ("qwen3:4b", "qwen3:1.7b")


def _env(orvyn_key: str, lappy_key: str, default: str) -> str:
    """Read ORVYN_* env var, fall back to legacy LAPPY_* for backward compat."""
    return os.environ.get(orvyn_key) or os.environ.get(lappy_key) or default


@dataclass(frozen=True)
class Settings:
    model: str = "qwen3:1.7b"
    ollama_url: str = "http://127.0.0.1:11434"
    vosk_model_path: Path = PROJECT_ROOT / "models" / "vosk-model-small-en-us-0.15"
    # Deliberately read-only in v0.1. No full-disk scans or file-content access.
    workspace_dir: Path = Path.home() / "Documents"

    @classmethod
    def from_environment(cls) -> "Settings":
        model = _env("ORVYN_MODEL", "LAPPY_MODEL", "qwen3:1.7b")
        if model not in ALLOWED_MODELS:
            raise ValueError(
                f"Model '{model}' is not in the allowed list: {ALLOWED_MODELS}. "
                f"Set ORVYN_MODEL to one of: {', '.join(ALLOWED_MODELS)}"
            )
        return cls(
            model=model,
            workspace_dir=Path(
                _env("ORVYN_WORKSPACE_DIR", "LAPPY_WORKSPACE_DIR",
                     str(Path.home() / "Documents"))
            ).expanduser(),
            vosk_model_path=Path(
                _env("ORVYN_VOSK_MODEL", "LAPPY_VOSK_MODEL",
                     str(PROJECT_ROOT / "models" / "vosk-model-small-en-us-0.15"))
            ).expanduser(),
        )
