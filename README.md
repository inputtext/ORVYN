# ORVYN v0.1.1 — Offline-First, On-Device AI Assistant (Windows)

*Formerly known as LAPPY.*

A deliberately narrow **working prototype**, not yet a full computer-use agent or animated notch. The LLM, speech recognition, speech synthesis, device queries and tool execution all run **on the device** after the one-time installation/downloads.

**Recommended machine:** Windows 10/11, 16 GB RAM, Intel Core i5-12500H, Intel Iris Xe. Start with CPU inference; dedicated GPU acceleration is **not assumed**.

## Architecture

```text
Text / mic -> [Vosk local STT + wake phrase (voice modes)]
           -> Local Ollama / Qwen3:1.7b -> JSON action plan
           -> strict schema+argument validation
           -> explicit launch-intent check (for opening applications)
           -> allowlisted Windows/psutil context tools
           -> verified data / *launch-request* result
           -> terminal + optional offline SAPI5 speech
```

- `lappy/agent.py`: loopback-only HTTP JSON-schema planner, strict action validation, no redirects and no proxy. System prompt identifies the AI as ORVYN running locally.
- `lappy/tools.py`: allowlisted tools; never runs AI-provided shell commands.
- `lappy/context.py`: minimized CPU/RAM/battery/process/window information and one-level listing of one configured workspace. **No full-disk indexing, file reads, or background observation.** Graceful handling when psutil is missing.
- `lappy/voice.py`: optional microphone input (Vosk) and local Windows TTS (SAPI5 via pyttsx3). Microphone stream closes before TTS. Supports both "Hey ORVYN" and legacy "Hey Lappy" wake phrases.
- `lappy/__main__.py`: text/voice/check CLI.
- `lappy/config.py`: configuration with `ORVYN_*` env vars (falls back to `LAPPY_*` for backward compatibility). Model is configurable via `ORVYN_MODEL`.
- `tests/test_agent.py`: offline functional tests, including a fake local Ollama HTTP server.
- `setup_windows.ps1`, `run_windows.ps1`: Windows setup and launch.

> **Note:** The Python package directory is still named `lappy/` in v0.1.1 to avoid breaking existing virtual environments. A full package rename is planned for v0.2.

## Exact Windows setup commands

### Prerequisites (internet needed ONCE)

1. Install **Python 3.11 (64-bit)** from https://www.python.org/downloads/ and enable the Python Launcher (`py`).
2. Install **Ollama for Windows** from https://ollama.com/download/windows . Launch it once. Make sure `ollama --version` works in a NEW PowerShell window.
3. Extract this ZIP. For example, put `lappy-v0.1` in `D:\ORVYN\Projects`.
4. Open **PowerShell** in the extracted folder.

**Simple setup:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_windows.ps1
```

This installs the Python dependencies, pulls the approximately **1 GB** Qwen3 1.7B model, downloads and extracts Vosk's **40 MB** small English speech model, and sets `OLLAMA_NO_CLOUD=1` and `OLLAMA_HOST=127.0.0.1:11434` for your user account. **Fully quit and relaunch Ollama** to apply the environment settings. The original Ollama installer, Python installer and packages must be obtained from their official sources and verified by the user.

**Manual setup alternative:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen3:1.7b
New-Item -ItemType Directory -Force models | Out-Null
Invoke-WebRequest 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip' -OutFile '.\models\vosk.zip'
Expand-Archive '.\models\vosk.zip' -DestinationPath '.\models' -Force
Remove-Item '.\models\vosk.zip'
[Environment]::SetEnvironmentVariable('OLLAMA_NO_CLOUD','1','User')
[Environment]::SetEnvironmentVariable('OLLAMA_HOST','127.0.0.1:11434','User')
```

Quit/relaunch Ollama after setting the environment variables. Avoid enabling any cloud model or plugin in your Ollama environment.

### Start ORVYN

```powershell
.\run_windows.ps1 -Mode check    # Ollama, model, voice files
.\run_windows.ps1 -Mode text     # Most reliable first run
.\run_windows.ps1 -Mode ptt      # Press Enter, talk, get spoken reply
.\run_windows.ps1 -Mode voice    # Say "Hey ORVYN" then give a command
```

If script execution is disallowed, use Python directly from PowerShell:

```powershell
.\.venv\Scripts\python.exe -m lappy --check
.\.venv\Scripts\python.exe -m lappy
.\.venv\Scripts\python.exe -m lappy --push-to-talk
.\.venv\Scripts\python.exe -m lappy --voice
```

### Try these requests

- `How are you?`
- `What is my CPU and RAM usage?`
- `What applications are running?`
- `What is my active window?`
- `List my workspace folder.`
- `Open notepad.`
- `Open calculator.`
- `Open my workspace in Explorer.`

**Not supported in this version:** arbitrary shell, web browsing, manipulating files, controlling third-party apps, reading entire drive contents, screenshots, browser profile selection, multi-step agent planning, screen vision, or notch animations. These are later milestones.

### Change workspace or model size

Only the configured workspace's top-level names are examined when asked. Nothing is automatically indexed.

```powershell
$env:ORVYN_WORKSPACE_DIR='D:\Projects'
.\run_windows.ps1 -Mode text
```

To use the larger Qwen3 4B model for higher capability (more compute/RAM required):

```powershell
ollama pull qwen3:4b
$env:ORVYN_MODEL='qwen3:4b'
.\run_windows.ps1 -Mode text
```

The default 1.7B model is faster on CPU but has a lower capability ceiling. The 4B model uses more compute but generally produces better results. Both models still need real testing on your machine.

> **Backward compatibility:** `LAPPY_MODEL`, `LAPPY_WORKSPACE_DIR`, and `LAPPY_VOSK_MODEL` environment variables are still respected as fallbacks if the `ORVYN_*` variants are not set.

### Validate with tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests run without a microphone or installed Ollama and verify the logic against deterministic mock components; they **do not prove** the actual Windows runtime, model quality, Vosk transcription accuracy, physical audio hardware, battery usage, or app-launch success. Test those on your own machine.

## What offline/privacy means here

- Every ORVYN-created LLM request goes to loopback `127.0.0.1:11434`; an external endpoint, proxy, and HTTP redirects are rejected.
- `OLLAMA_NO_CLOUD=1` disables Ollama cloud features **after Ollama is restarted**. The app uses a downloaded local model rather than a `:cloud` model. You can verify Ollama's local-only setting in its logs.
- The system prompt explicitly instructs the AI that it is ORVYN, running locally, and must not claim to be cloud-hosted.
- Voice recognition uses a locally downloaded Vosk model. Voice output uses Windows SAPI5. No hosted speech endpoints.
- Setup, Windows, Ollama updates, other installed apps, and unrelated OS network traffic are outside ORVYN's control. This project does not promise your entire machine is offline.
- Initial setup and downloads **need internet**. After the prerequisites are installed, disconnect Wi-Fi to test actual offline operation.
- The microphone is active while the voice-mode listener runs. In v0.1, don't treat the wake phrase as voice authentication. Use `--push-to-talk` for a more intentional interaction.
- No transcription, prompts, or device snapshots are persistently logged by this code. Ollama and Windows have their own storage/log policies.

## Security boundaries

- A valid plan can only choose one of seven actions from a fixed schema. Illegal action/target combinations are rejected.
- Only explicit launch instructions for **notepad** or **calculator** are allowed; workspace Explorer has its own narrow action.
- No `shell=True`, no LLM-generated commands, no privileged operations, no file-content reads, no deletions.
- The code reports application *launch requests* rather than assuming it has verified the UI state.
- Model text is **never** a source of execution permissions. A production build will need a robust human-approval flow, OS-level sandboxing and post-action verification.

## Known limitations

- The small Vosk English model might misrecognize the coined names **ORVYN** or **Lappy**, especially with accents or microphone noise. Use `-Mode ptt` first; we can replace the wake-word path with a dedicated, properly licensed model later.
- Desktop performance depends on actual power settings, memory pressure, model context size, and CPU throttling. Initial response latency may be tens of seconds.
- The current agent uses **one** model-selected action per request, not an autonomous plan/execute/observe/replan loop.
- No desktop overlay exists yet. The next milestone is a Tauri island driven by explicit events, not a UI hiding unreliable agent behavior.
- The Python package directory is still `lappy/` in v0.1.1 to avoid breaking virtual environments. This will be renamed in v0.2.

## Changelog

### v0.1.1 (stabilization)

- Rebranded from LAPPY to ORVYN across UI, system prompt, docs, scripts.
- Clear system identity: AI knows it is ORVYN, running locally via Ollama, not cloud-hosted.
- Default model changed to `qwen3:1.7b` (configurable via `ORVYN_MODEL`).
- Environment variables renamed to `ORVYN_*` with `LAPPY_*` backward-compatible fallback.
- Model validation in configuration prevents unsupported model tags.
- Improved error messages: Ollama unavailability now shows actionable troubleshooting steps.
- Graceful handling when psutil is not installed (returns helpful message instead of crash).
- Added "Hey ORVYN" wake phrases alongside legacy "Hey Lappy".
- 23 automated tests (up from 12): new tests for config, error recovery, and identity.

### v0.1.0

- Initial prototype with text/voice modes, JSON-schema planning, and allowlisted tools.

## Next milestone (v0.2)

Introduce a local event bus, SQLite context cache, opt-in file index, stronger command authorization and a Tauri notification island. Retain the fixed tool API for safe extensibility. Rename `lappy/` package directory to `orvyn/`.

## Source references

- Ollama Windows: https://docs.ollama.com/windows
- Ollama structured JSON responses: https://docs.ollama.com/capabilities/structured-outputs
- Ollama local-only setting: https://docs.ollama.com/faq
- Qwen3 1.7B: https://ollama.com/library/qwen3:1.7b
- Qwen3 4B: https://ollama.com/library/qwen3:4b
- Vosk speech models: https://alphacephei.com/vosk/models
- Vosk microphone example: https://github.com/alphacep/vosk-api/blob/master/python/example/test_microphone.py
- Offline SAPI5 speech (pyttsx3): https://github.com/nateshmbhat/pyttsx3

License note: this repository is a learning prototype. No third-party weights, models or installers are redistributed in this archive. Review third-party licenses and commercial-distribution requirements before shipping any packaged product.


## ORVYN v0.2.0 — local runtime manager (development branch)

The PowerShell launcher now attempts to start Ollama automatically **only if its local HTTP API is unavailable**. It starts Ollama with `OLLAMA_NO_CLOUD=1`, binds the service to `127.0.0.1:11434`, and uses your configured model directory. There are no model downloads or shell-based actions.

On Windows, set the existing model directory once (PowerShell):

```powershell
[Environment]::SetEnvironmentVariable('ORVYN_MODELS_DIR','D:\ORVYN\Models','User')
```

Open a new terminal after changing the environment variable. Start and test:

```powershell
.\run_windows.ps1 -Mode check
.\run_windows.ps1 -Mode text
```

To reuse an already-running Ollama process without attempting to launch one:

```powershell
.\run_windows.ps1 -Mode text -NoAutoStart
```

Alternatively, `python -m lappy --start-ollama --check` explicitly enables managed startup, whereas `python -m lappy --check` leaves server startup unchanged. Existing processes may use their own model directory; verify that `qwen3:1.7b` is found using the check mode. Voice recording still requires a separately installed Vosk speech model.


## ORVYN v0.2 voice foundation (development branch)

Install the Vosk offline speech model explicitly (download is only performed during setup):

```powershell
.\scripts\setup_voice_windows.ps1
```

This stores the speech model under `D:\ORVYN\VoiceModels` and sets user variable `ORVYN_VOSK_MODEL`. Open a **new** terminal so the variable is available. Confirm Windows microphone permissions are enabled for desktop apps, then run:

```powershell
.\run_windows.ps1 -Mode mic-check
.\run_windows.ps1 -Mode ptt
```

Push-to-talk: press Enter, say a complete request (e.g. *What is my CPU usage?*), then wait for local recognition and spoken output. Wake mode is available with `.\run_windows.ps1 -Mode voice`; Vosk recognition of coined names is not guaranteed, so test both *Or-vin* and *Or-vee-on*. Use `-NoSpeech` to disable spoken answers. Press Ctrl+C to end voice mode. Audio is processed in RAM; no microphone data is uploaded or written to a recording file by this component.

The `mic-check` mode does not start Ollama or record microphone audio. It checks for Vosk model presence and an accessible input device.


## Optional higher-accuracy local speech-to-text (Whisper)

The small Vosk model can mishear natural conversational English. ORVYN now supports **faster-whisper base.en (CPU int8)** for *push-to-talk only*; existing Vosk wake mode is unchanged. This is a separately installed optional feature, not a replacement for Qwen3.

Setup (requires internet once to download weights to D:):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_whisper_windows.ps1
```

Restart the terminal, then compare transcriptions:

```powershell
.\run_windows.ps1 -Mode ptt -Whisper -NoSpeech
```

Press Enter and speak clearly during the next eight seconds. The recognized text is printed before ORVYN decides what action to take. `-NoSpeech` temporarily disables spoken output so you can focus on transcription accuracy. Try **What is my CPU usage?**, **Open Notepad**, and **List my workspace**.

The model's directory is `D:\ORVYN\VoiceModels\whisper-base.en`. Runtime loading requires `model.bin` to already exist and sets `local_files_only=True`. Audio clips are held in memory and are neither saved nor uploaded. Whisper in this first iteration is *not continuous listening* and does not handle the wake word; the separate Vosk-based wake mode remains available. CPU processing may be slower than the small Vosk model. If you want a different model directory, set `ORVYN_WHISPER_MODEL`.
