"""Optional fully offline higher-accuracy push-to-talk speech recognition.

The model must be installed to a local directory in advance.
No downloads or HTTP calls are made by this module.
"""
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_WHISPER_MODEL = Path("D:/ORVYN/VoiceModels/whisper-base.en")


class WhisperPushToTalk:
    """Record a bounded audio clip in memory, then transcribe using CPU int8."""

    def __init__(self, model_dir: Path | None = None):
        chosen = model_dir or Path(os.environ.get("ORVYN_WHISPER_MODEL", str(DEFAULT_WHISPER_MODEL)))
        self.model_dir = Path(chosen).expanduser()
        if not (self.model_dir / "model.bin").is_file():
            raise FileNotFoundError(
                f"Whisper model not found at {self.model_dir}. "
                "Install it using scripts/setup_whisper_windows.ps1 first."
            )
        try:
            import sounddevice as sd
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                f"Whisper dependency missing: {exc}. "
                "Install requirements-whisper.txt into ORVYN's .venv."
            ) from exc
        self.sd = sd
        # Only load model weights from existing local files.
        self.model = WhisperModel(
            str(self.model_dir), device="cpu", compute_type="int8",
            local_files_only=True, cpu_threads=4,
        )

    def capture_once(self, seconds: float = 8) -> str:
        """Record a fixed short clip without saving or uploading audio."""
        if not 1 <= seconds <= 30:
            raise ValueError("Recording duration must be between 1 and 30 seconds")
        rate = 16000
        try:
            audio = self.sd.rec(
                int(rate * seconds), samplerate=rate,
                channels=1, dtype="float32",
            )
            self.sd.wait()
        except (OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError(f"Microphone capture failed: {exc}") from exc
        segments, _info = self.model.transcribe(
            audio.reshape(-1),
            language="en",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()
