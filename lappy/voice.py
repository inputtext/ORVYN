"""Offline voice I/O. The microphone stream is closed before speaking."""
from __future__ import annotations

import json
from pathlib import Path
import queue
import re
import time


# Wake phrases — supports both ORVYN and legacy LAPPY names.
_WAKE_PHRASES = (
    "hey orvyn", "hey orvin", "hey orven",
    "hey lappy", "hey lapi", "hey lapy",
)


def strip_wake_word(transcript: str) -> str | None:
    """Returns the same-utterance command if a wake phrase is present."""
    cleaned = re.sub(r"[^a-z0-9\s]", " ", transcript.lower())
    cleaned = " ".join(cleaned.split())
    for phrase in _WAKE_PHRASES:
        if cleaned == phrase:
            return ""
        if cleaned.startswith(phrase + " "):
            return cleaned[len(phrase):].strip()
    return None


class OfflineVoice:
    def __init__(self, model_path: Path):
        if not model_path.is_dir():
            raise FileNotFoundError(f"Vosk model missing at {model_path}")
        try:
            import sounddevice as sd
            from vosk import Model, KaldiRecognizer, SetLogLevel
        except ImportError as exc:
            raise RuntimeError("Install dependencies using requirements.txt") from exc
        SetLogLevel(-1)
        self.sd = sd
        self.model = Model(str(model_path))
        self.recognizer = KaldiRecognizer

    def utterances(self, max_seconds: float | None = None):
        """Yields finalized speech utterances; audio is processed in RAM only."""
        audio: queue.Queue[bytes] = queue.Queue(maxsize=32)
        info = self.sd.query_devices(kind="input")
        sample_rate = int(info["default_samplerate"])
        recognizer = self.recognizer(self.model, sample_rate)

        def callback(indata, frames, timing, status):
            try:
                audio.put_nowait(bytes(indata))
            except queue.Full:
                pass  # Drop old audio instead of blocking the microphone callback.

        deadline = time.monotonic() + max_seconds if max_seconds is not None else None
        with self.sd.RawInputStream(samplerate=sample_rate, blocksize=4000,
                                    dtype="int16", channels=1, callback=callback):
            while deadline is None or time.monotonic() < deadline:
                try:
                    data = audio.get(timeout=0.4)
                except queue.Empty:
                    continue
                if recognizer.AcceptWaveform(data):
                    sentence = json.loads(recognizer.Result()).get("text", "").strip()
                    if sentence:
                        yield sentence

    def capture_once(self, seconds: float = 20) -> str:
        for sentence in self.utterances(max_seconds=seconds):
            return sentence
        return ""

    def wait_for_wake_command(self) -> str:
        print("[Mic live] Say 'Hey ORVYN', then give a command. Ctrl+C to stop.")
        deadline = None
        for sentence in self.utterances():
            if deadline is not None:
                if time.monotonic() > deadline:
                    deadline = None
                elif sentence.strip():
                    return sentence
            remainder = strip_wake_word(sentence)
            if remainder is not None:
                if remainder:
                    return remainder
                print("[Wake detected] Listening for a command (10 seconds)...")
                deadline = time.monotonic() + 10
        return ""


def speak(text: str) -> None:
    """Windows SAPI5 text to speech; no internet service is called."""
    import pyttsx3
    engine = pyttsx3.init("sapi5")
    engine.setProperty("rate", 175)
    engine.say(text[:450])
    engine.runAndWait()
    engine.stop()
