"""Offline microphone diagnostics; nothing recorded to disk."""
from __future__ import annotations

from pathlib import Path


def microphone_check(model_path: Path) -> tuple[bool, str]:
    """Check installed voice files and input-device access without recording audio."""
    if not model_path.is_dir():
        return False, (
            f"Vosk model missing: {model_path}. "
            "Run scripts/setup_voice_windows.ps1 first."
        )
    try:
        import sounddevice as sd
        import vosk  # noqa: F401
    except ImportError as exc:
        return False, f"Voice Python dependency missing: {exc}. Install requirements.txt."
    try:
        device = sd.query_devices(kind="input")
        sample_rate = int(device["default_samplerate"])
        if sample_rate <= 0:
            return False, "Microphone does not report a valid sample rate."
        sd.check_input_settings(
            device=None, samplerate=sample_rate, channels=1, dtype="int16"
        )
    except (OSError, ValueError, RuntimeError) as exc:
        return False, (
            f"Microphone unavailable: {exc}. Check Windows microphone permissions, "
            "input device selection, and whether another app owns the device."
        )
    return True, f"Offline voice model found. Microphone ready: {device['name']} ({sample_rate} Hz)."
