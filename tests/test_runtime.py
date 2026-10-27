"""Runtime manager tests: no external process or Ollama required."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from lappy.runtime import (
    RuntimeStartupError, _model_directory, _ollama_executable,
    ensure_ollama_running,
)


class RuntimeTests(unittest.TestCase):
    def test_existing_server_is_reused(self):
        with patch("lappy.runtime._server_ready", return_value=True), patch(
            "lappy.runtime.subprocess.Popen"
        ) as popen:
            result = ensure_ollama_running()
        self.assertIn("already running", result)
        popen.assert_not_called()

    def test_missing_model_config_fails_without_starting(self):
        with patch("lappy.runtime._server_ready", return_value=False), patch(
            "lappy.runtime._model_directory", return_value=None
        ), patch("lappy.runtime.subprocess.Popen") as popen:
            with self.assertRaisesRegex(RuntimeStartupError, "Model storage"):
                ensure_ollama_running()
        popen.assert_not_called()

    def test_nonexistent_model_directory_rejected(self):
        with patch("lappy.runtime._server_ready", return_value=False):
            with self.assertRaisesRegex(RuntimeStartupError, "does not exist"):
                ensure_ollama_running(models_dir=Path("Z:/orvyn/path/missing"))

    def test_explicit_executable_must_exist(self):
        with self.assertRaisesRegex(RuntimeStartupError, "does not exist"):
            _ollama_executable({"ORVYN_OLLAMA_EXE": "Z:/missing/ollama.exe"})

    def test_model_directory_prioritizes_orvyn_variable(self):
        result = _model_directory({
            "ORVYN_MODELS_DIR": "D:/ORVYN/Models",
            "OLLAMA_MODELS": "C:/old",
        })
        self.assertEqual(result, Path("D:/ORVYN/Models"))

    def test_start_sets_local_only_env_and_d_drive(self):
        with tempfile.TemporaryDirectory() as folder:
            process = Mock()
            process.poll.return_value = None
            with patch("lappy.runtime._server_ready", side_effect=[False, False, True]), patch(
                "lappy.runtime._ollama_executable", return_value="ollama.exe"
            ), patch("lappy.runtime.subprocess.Popen", return_value=process) as popen, patch(
                "lappy.runtime.time.sleep"
            ):
                message = ensure_ollama_running(models_dir=Path(folder))
            args, kwargs = popen.call_args
            self.assertEqual(args[0], ["ollama.exe", "serve"])
            self.assertEqual(kwargs["env"]["OLLAMA_MODELS"], folder)
            self.assertEqual(kwargs["env"]["OLLAMA_HOST"], "127.0.0.1:11434")
            self.assertEqual(kwargs["env"]["OLLAMA_NO_CLOUD"], "1")
            self.assertIn("Started local Ollama", message)

    def test_start_failure_is_actionable(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch("lappy.runtime._server_ready", return_value=False), patch(
                "lappy.runtime._ollama_executable", return_value="ollama.exe"
            ), patch("lappy.runtime.subprocess.Popen", side_effect=OSError("denied")):
                with self.assertRaisesRegex(RuntimeStartupError, "denied"):
                    ensure_ollama_running(models_dir=Path(folder))


if __name__ == "__main__":
    unittest.main()
