"""Offline deterministic tests. No Ollama/model/microphone required."""
import json
import os
import platform
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from lappy.agent import Assistant, OllamaPlanner, parse_plan
from lappy.config import Settings, ALLOWED_MODELS
from lappy.context import LaptopContext
from lappy.tools import ToolRouter
from lappy.voice import strip_wake_word


class TestValidation(unittest.TestCase):
    def test_valid_open(self):
        self.assertEqual(parse_plan('{"action":"open_application","target":"notepad","reply":"Opening"}').target, "notepad")

    def test_disallow_shell(self):
        with self.assertRaises(ValueError):
            parse_plan('{"action":"run_shell","target":"none","reply":"done"}')

    def test_disallow_extra_fields(self):
        with self.assertRaises(ValueError):
            parse_plan('{"action":"answer","target":"none","reply":"ok","command":"del /q *"}')

    def test_disallow_invalid_target_pair(self):
        with self.assertRaises(ValueError):
            parse_plan('{"action":"get_system_status","target":"calculator","reply":"ok"}')

    def test_block_external_endpoint(self):
        for url in ("https://127.0.0.1:11434", "http://example.com:11434", "http://127.0.0.1:11434@evil.com", "http://127.0.0.1:11434/path"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                OllamaPlanner("qwen3:1.7b", url)

    def test_disallow_remote_model_tags(self):
        with self.assertRaises(ValueError):
            OllamaPlanner("qwen3:cloud")

    def test_wake_phrase_orvyn(self):
        self.assertEqual(strip_wake_word("Hey ORVYN, open notepad"), "open notepad")
        self.assertEqual(strip_wake_word("hey orvyn"), "")
        self.assertIsNone(strip_wake_word("open notepad"))

    def test_wake_phrase_lappy_backward_compat(self):
        """Legacy 'Hey Lappy' wake phrase still works."""
        self.assertEqual(strip_wake_word("Hey Lappy, open notepad"), "open notepad")
        self.assertEqual(strip_wake_word("hey lappy"), "")


class TestContextAndTools(unittest.TestCase):
    def test_workspace_listing_is_shallow(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "hello.txt").write_text("TOP SECRET CONTENT", encoding="utf-8")
            (root / "subfolder").mkdir()
            (root / "subfolder" / "child.txt").write_text("deep secret", encoding="utf-8")
            summary = LaptopContext(root).workspace()
            self.assertIn("hello.txt", summary)
            self.assertIn("subfolder", summary)
            self.assertNotIn("TOP SECRET", summary)
            self.assertNotIn("child.txt", summary)

    def test_router_rejects_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            router = ToolRouter(LaptopContext(Path(folder)), launcher=lambda *a, **k: None)
            self.assertIn("Blocked", router.execute("run_shell", "none"))
            self.assertIn("Blocked", router.execute("get_system_status", "notepad"))

    def test_open_allowlist_only(self):
        events = []
        with tempfile.TemporaryDirectory() as folder:
            router = ToolRouter(LaptopContext(Path(folder)), launcher=lambda *a, **k: events.append((a, k)))
            with patch("lappy.tools.platform.system", return_value="Windows"):
                msg = router.execute("open_application", "notepad")
                self.assertIn("Requested Windows", msg)
                self.assertEqual(events, [((["notepad.exe"],), {"shell": False})])
                self.assertIn("Blocked", router.execute("open_application", "powershell"))


class TestAgentEndToEnd(unittest.TestCase):
    def test_block_hallucinated_launch_without_user_request(self):
        class FakePlanner:
            def plan(self, text):
                return parse_plan('{"action":"open_application","target":"notepad","reply":"Opening"}')
        launched = []
        with tempfile.TemporaryDirectory() as folder:
            tools = ToolRouter(LaptopContext(Path(folder)), launcher=lambda *a, **k: launched.append(a))
            assistant = Assistant(FakePlanner(), tools)
            self.assertIn("Blocked", assistant.respond("How are you?"))
            self.assertEqual(launched, [])

    def test_planning_through_mock_loopback_http_and_dispatch(self):
        """Exercise real HTTP payload+schema+parser+dispatcher against local mock endpoint."""
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                req = json.loads(self.rfile.read(length))
                self.server.last_request = req
                response = {"message": {"content": json.dumps({
                    "action": "list_workspace", "target": "none", "reply": "I'll list it",
                })}}
                data = json.dumps(response).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                (Path(folder) / "OrvynProject").mkdir()
                planner = OllamaPlanner("qwen3:1.7b", f"http://127.0.0.1:{server.server_port}")
                assistant = Assistant(planner, ToolRouter(LaptopContext(Path(folder))))
                result = assistant.respond("What is in my workspace?")
                self.assertIn("OrvynProject", result)
                req = server.last_request
                self.assertEqual(req["model"], "qwen3:1.7b")
                self.assertEqual(req["format"]["properties"]["action"]["enum"][0], "answer")
                self.assertEqual(req["messages"][1]["content"], "What is in my workspace?")
                # Verify ORVYN identity is in the system prompt
                system_msg = req["messages"][0]["content"]
                self.assertIn("ORVYN", system_msg)
                self.assertIn("NOT cloud-hosted", system_msg)
                self.assertIn("local Ollama server", system_msg)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class TestConfiguration(unittest.TestCase):
    """Tests for ORVYN_MODEL / LAPPY_MODEL configuration and fallback."""

    def test_default_model_is_qwen3_1_7b(self):
        # Remove model env vars without clearing entire environment (Path.home() needs USERPROFILE)
        env_overrides = {}
        for key in ("ORVYN_MODEL", "LAPPY_MODEL"):
            if key in os.environ:
                env_overrides[key] = ""
        with patch.dict(os.environ, env_overrides):
            # Temporarily delete the keys so _env() falls through to default
            for key in ("ORVYN_MODEL", "LAPPY_MODEL"):
                os.environ.pop(key, None)
            settings = Settings.from_environment()
            self.assertEqual(settings.model, "qwen3:1.7b")

    def test_orvyn_model_env_var(self):
        with patch.dict(os.environ, {"ORVYN_MODEL": "qwen3:4b"}, clear=False):
            settings = Settings.from_environment()
            self.assertEqual(settings.model, "qwen3:4b")

    def test_lappy_model_fallback(self):
        with patch.dict(os.environ, {"LAPPY_MODEL": "qwen3:4b"}, clear=False):
            os.environ.pop("ORVYN_MODEL", None)
            settings = Settings.from_environment()
            self.assertEqual(settings.model, "qwen3:4b")

    def test_orvyn_model_takes_precedence_over_lappy(self):
        with patch.dict(os.environ, {"ORVYN_MODEL": "qwen3:1.7b", "LAPPY_MODEL": "qwen3:4b"}, clear=False):
            settings = Settings.from_environment()
            self.assertEqual(settings.model, "qwen3:1.7b")

    def test_invalid_model_rejected(self):
        with patch.dict(os.environ, {"ORVYN_MODEL": "gpt-4"}, clear=False):
            with self.assertRaises(ValueError) as ctx:
                Settings.from_environment()
            self.assertIn("gpt-4", str(ctx.exception))
            self.assertIn("not in the allowed list", str(ctx.exception))

    def test_allowed_models_matches_planner(self):
        """All configured allowed models are accepted by OllamaPlanner."""
        for model in ALLOWED_MODELS:
            planner = OllamaPlanner(model)  # Should not raise
            self.assertEqual(planner.model, model)


class TestErrorRecovery(unittest.TestCase):
    """Tests for improved error handling and failure scenarios."""

    def test_ollama_unreachable_gives_helpful_message(self):
        """When Ollama is unreachable, the error message should be actionable."""
        class UnreachablePlanner:
            def plan(self, text):
                import urllib.error
                raise urllib.error.URLError("Connection refused")
        with tempfile.TemporaryDirectory() as folder:
            tools = ToolRouter(LaptopContext(Path(folder)))
            assistant = Assistant(UnreachablePlanner(), tools)
            result = assistant.respond("Hello")
            self.assertIn("Ollama is unavailable", result)
            self.assertIn("Ollama is running", result)

    def test_tool_execution_error_recovery(self):
        """Tool execution errors are caught and reported gracefully."""
        class ErrorPlanner:
            def plan(self, text):
                return parse_plan('{"action":"get_system_status","target":"none","reply":"checking"}')
        with tempfile.TemporaryDirectory() as folder:
            ctx = LaptopContext(Path(folder))
            # Patch system_status to raise an OSError
            original = ctx.system_status
            def broken_status():
                raise OSError("Access denied to hardware monitor")
            ctx.system_status = broken_status
            tools = ToolRouter(ctx)
            assistant = Assistant(ErrorPlanner(), tools)
            result = assistant.respond("How is my system?")
            self.assertIn("Local tool could not complete", result)
            self.assertIn("OSError", result)

    def test_malformed_model_response(self):
        """Malformed JSON from model is handled gracefully."""
        class BrokenPlanner:
            def plan(self, text):
                return parse_plan('not valid json at all')
        with tempfile.TemporaryDirectory() as folder:
            tools = ToolRouter(LaptopContext(Path(folder)))
            assistant = Assistant(BrokenPlanner(), tools)
            result = assistant.respond("Hello")
            self.assertIn("Blocked invalid model response", result)

    def test_workspace_missing_shows_orvyn_env_var(self):
        """Missing workspace message references ORVYN_WORKSPACE_DIR."""
        ctx = LaptopContext(Path("/nonexistent/path/that/does/not/exist"))
        result = ctx.workspace()
        self.assertIn("ORVYN_WORKSPACE_DIR", result)

    def test_psutil_missing_graceful(self):
        """When psutil import fails, system_status returns a helpful message."""
        import importlib
        ctx = LaptopContext(Path.home())
        with patch.dict("sys.modules", {"psutil": None}):
            # Forcing ImportError by patching builtins import
            original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
            def mock_import(name, *args, **kwargs):
                if name == "psutil":
                    raise ImportError("No module named 'psutil'")
                return original_import(name, *args, **kwargs)
            with patch("builtins.__import__", side_effect=mock_import):
                result = ctx.system_status()
                self.assertIn("psutil", result.lower())


if __name__ == "__main__":
    unittest.main()
