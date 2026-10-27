# Explicit online setup only. Installs higher-accuracy Whisper model on D:.
# No cloud inference. Runtime uses local weights only.
param([string] $ModelDir = 'D:\ORVYN\VoiceModels\whisper-base.en')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (!(Test-Path $Python)) { throw "Python environment missing: $Python" }
& $Python -m pip install -r (Join-Path $ProjectRoot 'requirements-whisper.txt')
if ($LASTEXITCODE -ne 0) { throw 'Failed to install faster-whisper dependencies' }
New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
Write-Host "Downloading Whisper base.en weights into $ModelDir ..."
$env:ORVYN_WHISPER_MODEL = $ModelDir
& $Python -c "import os; from huggingface_hub import snapshot_download; snapshot_download(repo_id='Systran/faster-whisper-base.en', local_dir=os.environ['ORVYN_WHISPER_MODEL'])"
if ($LASTEXITCODE -ne 0 -or !(Test-Path (Join-Path $ModelDir 'model.bin'))) {
    throw "Whisper model download incomplete at $ModelDir"
}
[Environment]::SetEnvironmentVariable('ORVYN_WHISPER_MODEL', $ModelDir, 'User')
Write-Host 'Whisper setup complete. Open a new terminal, then test:'
Write-Host '.\run_windows.ps1 -Mode ptt -Whisper -NoSpeech'
