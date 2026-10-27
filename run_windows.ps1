param(
    [ValidateSet('text','voice','ptt','check','mic-check')]
    [string] $Mode = 'text',
    [switch] $NoSpeech,
    [switch] $NoAutoStart,
    [switch] $Whisper
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Run setup_windows.ps1 first.' }
$arguments = @('-m', 'lappy')
if (!$NoAutoStart -and $Mode -ne 'mic-check') { $arguments += '--start-ollama' }
switch ($Mode) {
    'voice' { $arguments += '--voice' }
    'ptt'   { $arguments += '--push-to-talk' }
    'check' { $arguments += '--check' }
    'mic-check' { $arguments += '--mic-check' }
}
if ($NoSpeech) { $arguments += '--no-speech' }
if ($Whisper) { $arguments += '--whisper' }
Write-Host 'Starting ORVYN v0.2.0...'
& $python @arguments
