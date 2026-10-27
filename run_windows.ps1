param(
    [ValidateSet('text','voice','ptt','check')]
    [string] $Mode = 'text',
    [switch] $NoSpeech,
    [switch] $NoAutoStart
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Run setup_windows.ps1 first.' }
$arguments = @('-m', 'lappy')
if (!$NoAutoStart) { $arguments += '--start-ollama' }
switch ($Mode) {
    'voice' { $arguments += '--voice' }
    'ptt'   { $arguments += '--push-to-talk' }
    'check' { $arguments += '--check' }
}
if ($NoSpeech) { $arguments += '--no-speech' }
Write-Host 'Starting ORVYN v0.2.0...'
& $python @arguments
