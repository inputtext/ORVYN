"""Voice foundation tests; no microphone, network or Vosk installation required."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from lappy.microphone import microphone_check
from lappy.voice import strip_wake_word


class WakeNameTests(unittest.TestCase):
    def test_orvin_variant(self):
        self.assertEqual(strip_wake_word("Hey Orvin, open notepad"), "open notepad")

    def test_orvion_variant(self):
        self.assertEqual(strip_wake_word("Hey Orvion, what is my RAM usage?"), "what is my ram usage")

    def test_orveeon_spacing(self):
        self.assertEqual(strip_wake_word("Hey or vee on open calculator"), "open calculator")

    def test_no_accidental_mid_sentence_activation(self):
        self.assertIsNone(strip_wake_word("My friend said hey orvion yesterday"))


class MicrophoneCheckTests(unittest.TestCase):
    def test_missing_model_is_actionable(self):
        result, reason = microphone_check(Path("Z:/this/does/not/exist"))
        self.assertFalse(result)
        self.assertIn("setup_voice_windows.ps1", reason)

    def test_microphone_ready(self):
        fake_sd = types.ModuleType("sounddevice")
        fake_sd.query_devices = lambda kind: {
            "name": "Test Microphone", "default_samplerate": 16000,
        }
        fake_sd.check_input_settings = lambda **kwargs: None
        fake_vosk = types.ModuleType("vosk")
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            sys.modules, {"sounddevice": fake_sd, "vosk": fake_vosk}
        ):
            ready, message = microphone_check(Path(folder))
        self.assertTrue(ready)
        self.assertIn("Test Microphone", message)

    def test_missing_input_device_reports_error(self):
        fake_sd = types.ModuleType("sounddevice")
        def missing(kind):
            raise ValueError("no default input")
        fake_sd.query_devices = missing
        fake_vosk = types.ModuleType("vosk")
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            sys.modules, {"sounddevice": fake_sd, "vosk": fake_vosk}
        ):
            ready, message = microphone_check(Path(folder))
        self.assertFalse(ready)
        self.assertIn("Microphone unavailable", message)


if __name__ == "__main__":
    unittest.main()
