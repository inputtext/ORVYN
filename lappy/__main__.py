"""Command-line interface: text by default, optional entirely offline voice."""
from __future__ import annotations

import argparse
import platform
import urllib.error

from .agent import Assistant, OllamaPlanner
from .config import Settings
from .context import LaptopContext
from .tools import ToolRouter


def diagnostics(settings: Settings, planner: OllamaPlanner) -> bool:
    print("ORVYN v0.2.0 offline prerequisites")
    print(f"OS: {platform.system()} {platform.release()} | Target: Windows")
    print(f"Ollama endpoint: {settings.ollama_url} (loopback only)")
    ok = True
    try:
        installed = planner.has_model()
        print(f"Local model {settings.model}: {'OK' if installed else 'NOT DOWNLOADED'}")
        if not installed:
            print(f"  -> Fix: run 'ollama pull {settings.model}' to download the model")
        ok &= installed
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        print(f"Ollama server: NOT REACHABLE ({type(exc).__name__})")
        print("  -> Fix: start the Ollama application and try again")
        ok = False
    print(f"Vosk voice model: {'OK' if settings.vosk_model_path.is_dir() else 'MISSING (text mode works)'}")
    print(f"Workspace directory: {settings.workspace_dir}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m lappy",
                                     description="ORVYN — offline-first, on-device AI assistant")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Check local Ollama/model and voice files")
    modes.add_argument("--mic-check", action="store_true", help="Check offline voice model and microphone without recording")
    modes.add_argument("--voice", action="store_true", help="Wake-word microphone mode")
    modes.add_argument("--push-to-talk", action="store_true", help="Microphone mode with Enter to talk")
    parser.add_argument("--no-speech", action="store_true", help="Disable spoken responses")
    parser.add_argument("--whisper", action="store_true", help="Use local Whisper for push-to-talk recognition")
    parser.add_argument("--start-ollama", action="store_true", help="Start local Ollama if not already running")
    args = parser.parse_args()

    try:
        settings = Settings.from_environment()
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 1

    if args.whisper and not args.push_to_talk:
        parser.error("--whisper requires --push-to-talk")

    if args.mic_check:
        from .microphone import microphone_check
        ready, message = microphone_check(settings.vosk_model_path)
        print(message)
        return 0 if ready else 2

    if args.start_ollama:
        from .runtime import RuntimeStartupError, ensure_ollama_running
        try:
            print(ensure_ollama_running())
        except RuntimeStartupError as exc:
            print(f"Local runtime startup failed: {exc}")
            return 2

    planner = OllamaPlanner(settings.model, settings.ollama_url)
    if args.check:
        return 0 if diagnostics(settings, planner) else 1

    assistant = Assistant(planner, ToolRouter(LaptopContext(settings.workspace_dir)))
    if args.voice or args.push_to_talk:
        from .voice import OfflineVoice, speak
        try:
            if args.whisper:
                from .whisper_voice import WhisperPushToTalk
                voice = WhisperPushToTalk()
                print("[Whisper offline] Recording 8-second clips when Enter is pressed.")
            else:
                voice = OfflineVoice(settings.vosk_model_path)
            while True:
                if args.push_to_talk:
                    input("\nPress Enter to speak (Ctrl+C to exit): ")
                    command = voice.capture_once()
                else:
                    command = voice.wait_for_wake_command()
                if not command:
                    print("No speech recognized; try again.")
                    continue
                print("You:", command)
                if command.lower() in ("exit", "quit", "stop orvyn", "stop lappy"):
                    return 0
                reply = assistant.respond(command)
                print("ORVYN:", reply)
                if not args.no_speech:
                    try:
                        speak(reply)
                    except (RuntimeError, ImportError, OSError) as exc:
                        print("Speech output unavailable:", exc)
        except (RuntimeError, FileNotFoundError) as exc:
            print("Voice setup error:", exc)
            return 2
        except KeyboardInterrupt:
            print("\nGoodbye!")
            return 0

    print("ORVYN v0.2.0 — LOCAL TEXT MODE. Type 'exit' to quit.")
    try:
        while True:
            command = input("You > ").strip()
            if command.lower() in ("exit", "quit"):
                break
            print("ORVYN >", assistant.respond(command))
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
