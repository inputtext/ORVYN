# Install an offline English Vosk speech model on D:. No admin rights required.
# Downloads only when explicitly run. Runtime voice processing is entirely local.
param(
    [string] $ModelsRoot = 'D:\ORVYN\VoiceModels'
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (!(Test-Path $Python)) {
    throw "Project Python environment is missing at $Python. Create .venv first."
}
Write-Host 'Installing voice Python dependencies into the project virtual environment...'
& $Python -m pip install -r (Join-Path $ProjectRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) {
    throw 'Voice dependency installation failed. Review pip output before continuing.'
}
$ProgressPreference = 'SilentlyContinue'
$ModelName = 'vosk-model-small-en-us-0.15'
$Destination = Join-Path $ModelsRoot $ModelName
$Archive = Join-Path $ModelsRoot ($ModelName + '.zip')
$Url = 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip'

New-Item -ItemType Directory -Force -Path $ModelsRoot | Out-Null
if (!(Test-Path (Join-Path $Destination 'am'))) {
    Write-Host 'Downloading official Vosk model to D: (setup-time internet required)...'
    Invoke-WebRequest -Uri $Url -OutFile $Archive
    try {
        Expand-Archive -LiteralPath $Archive -DestinationPath $ModelsRoot -Force
    }
    finally {
        Remove-Item -LiteralPath $Archive -Force -ErrorAction SilentlyContinue
    }
}
if (!(Test-Path (Join-Path $Destination 'am'))) {
    throw "Speech model install incomplete: $Destination"
}
[Environment]::SetEnvironmentVariable('ORVYN_VOSK_MODEL', $Destination, 'User')
$env:ORVYN_VOSK_MODEL = $Destination
Write-Host "Voice model installed at: $Destination"
Write-Host 'Open a new PowerShell terminal for the saved user setting.'
Write-Host 'Check microphone: .\run_windows.ps1 -Mode mic-check -NoAutoStart'
Write-Host 'Push-to-talk: .\run_windows.ps1 -Mode ptt'
