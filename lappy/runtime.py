"""Safely start and verify the local-only Ollama runtime on Windows.

No downloads, cloud APIs, shell execution, or model mutations occur here.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.request


class RuntimeStartupError(RuntimeError):
    """Local Ollama could not be started or reached."""


def _model_directory(environ: dict[str, str]) -> Path | None:
    """Resolve model storage without silently redirecting downloads to C:."""
    configured = environ.get("ORVYN_MODELS_DIR") or environ.get("OLLAMA_MODELS")
    if not configured and os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                configured, _ = winreg.QueryValueEx(key, "OLLAMA_MODELS")
        except (OSError, ImportError):
            pass
    return Path(configured).expanduser() if configured else None


def _ollama_executable(environ: dict[str, str]) -> str:
    explicit = environ.get("ORVYN_OLLAMA_EXE")
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_file():
            raise RuntimeStartupError(f"ORVYN_OLLAMA_EXE does not exist: {candidate}")
        return str(candidate)

    found = shutil.which("ollama")
    if found:
        return found

    candidates = [
        Path("D:/ORVYN/Ollama/ollama.exe"),
        Path(environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeStartupError(
        "Ollama executable not found. Install Ollama or set ORVYN_OLLAMA_EXE."
    )


def _server_ready(url: str = "http://127.0.0.1:11434") -> bool:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url + "/api/tags", timeout=1.5) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def ensure_ollama_running(
    *,
    models_dir: Path | None = None,
    timeout_seconds: float = 15.0,
) -> str:
    """Return server status, starting one local server if necessary.

    The Ollama API is intentionally bound to loopback. Existing servers are reused,
    but their effective model directory cannot be inferred from the API; callers
    should verify the requested model separately with `--check`.
    """
    if _server_ready():
        return "Ollama already running on 127.0.0.1:11434"

    environment = os.environ.copy()
    chosen = models_dir or _model_directory(environment)
    if chosen is None:
        raise RuntimeStartupError(
            "Model storage isn't configured. Set ORVYN_MODELS_DIR or "
            "OLLAMA_MODELS to your D: drive model directory before starting."
        )
    chosen = Path(chosen).expanduser()
    if not chosen.is_dir():
        raise RuntimeStartupError(
            f"Model directory does not exist: {chosen}. "
            "Check your configured D: drive path."
        )
    # Do not modify the caller's environment or user registry settings.
    environment["OLLAMA_MODELS"] = str(chosen)
    environment["OLLAMA_HOST"] = "127.0.0.1:11434"
    environment["OLLAMA_NO_CLOUD"] = "1"
    executable = _ollama_executable(environment)

    kwargs = {
        "env": environment,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        process = subprocess.Popen([executable, "serve"], **kwargs)
    except OSError as exc:
        raise RuntimeStartupError(f"Could not start Ollama: {exc}") from exc

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if _server_ready():
            return f"Started local Ollama using models at {chosen}"
        if process.poll() is not None:
            raise RuntimeStartupError(
                "Ollama exited during startup. Check for a port conflict or "
                "start 'ollama serve' manually to see its logs."
            )
        time.sleep(0.3)
    raise RuntimeStartupError(
        "Ollama did not become reachable on 127.0.0.1:11434. "
        "Try running 'ollama serve' manually to inspect startup logs."
    )
