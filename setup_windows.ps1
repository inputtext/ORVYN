# Run in Windows PowerShell after installing Python 3.11 and Ollama.
# Downloads happen ONLY during setup, not when running ORVYN.
param([switch] $SkipModelDownloads)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'ORVYN v0.1.1 Windows installer (Python 3.11 64-bit recommended)'
Write-Host '(formerly known as LAPPY)'
py -3.11 --version
if (!(Test-Path '.venv\Scripts\python.exe')) {
    py -3.11 -m venv .venv
}
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }

if (!$SkipModelDownloads) {
    if (!(Get-Command ollama -ErrorAction SilentlyContinue)) {
        throw 'Install Ollama from https://ollama.com/download/windows and reopen PowerShell.'
    }
    & ollama pull qwen3:1.7b
    if ($LASTEXITCODE -ne 0) { throw 'Ollama model download failed.' }
    $modelDir = Join-Path $PSScriptRoot 'models\vosk-model-small-en-us-0.15'
    if (!(Test-Path $modelDir)) {
        $zip = Join-Path $env:TEMP 'vosk-model-small-en-us-0.15.zip'
        Invoke-WebRequest -Uri 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip' -OutFile $zip
        Expand-Archive -Path $zip -DestinationPath (Join-Path $PSScriptRoot 'models') -Force
        Remove-Item $zip
    }
}
# Configures Ollama for local-only operation on the NEXT server restart.
[Environment]::SetEnvironmentVariable('OLLAMA_NO_CLOUD', '1', 'User')
[Environment]::SetEnvironmentVariable('OLLAMA_HOST', '127.0.0.1:11434', 'User')
Write-Host 'Setup finished. Fully quit Ollama in the system tray and relaunch it to apply local-only settings.'
Write-Host 'Check: .\run_windows.ps1 -Mode check'
Write-Host 'Start: .\run_windows.ps1 -Mode text'
