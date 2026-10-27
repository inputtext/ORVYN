"""Whisper integration tests use local stubs; no audio hardware or downloads."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from lappy.whisper_voice import WhisperPushToTalk


class WhisperTests(unittest.TestCase):
    def test_missing_model_is_actionable(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "setup_whisper_windows"):
                WhisperPushToTalk(Path(directory))

    def test_invalid_capture_duration(self):
        voice = object.__new__(WhisperPushToTalk)
        with self.assertRaises(ValueError):
            voice.capture_once(0)

    def test_local_only_model_and_transcription(self):
        fake_sd = types.ModuleType("sounddevice")
        fake_sd.rec = Mock(return_value=Mock(reshape=lambda _n: "audio"))
        fake_sd.wait = Mock()
        model = Mock()
        model.transcribe.return_value = ([types.SimpleNamespace(text=" Open notepad. ")], None)
        fw = types.ModuleType("faster_whisper")
        fw.WhisperModel = Mock(return_value=model)
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "model.bin").write_bytes(b"fixture")
            with patch.dict(sys.modules, {"sounddevice": fake_sd, "faster_whisper": fw}):
                voice = WhisperPushToTalk(Path(directory))
                self.assertEqual(voice.capture_once(seconds=2), "Open notepad.")
        self.assertTrue(fw.WhisperModel.call_args.kwargs["local_files_only"])
        self.assertEqual(fw.WhisperModel.call_args.kwargs["device"], "cpu")
        self.assertEqual(fw.WhisperModel.call_args.kwargs["compute_type"], "int8")
