<#
Builds a standalone, portable Windows bundle of Photo Organizer using
PyInstaller: a folder (dist/photo_organizer/) containing photo_organizer.exe
plus every dependency it needs, including its own Python runtime. Copy that
whole folder to a Windows machine with no Python installed and double-click
the .exe -- confirmed working by launching it with Python stripped from PATH.

Run from the repo root:
    .\.venv\Scripts\pip install -e ".[build]"
    .\packaging\build_windows.ps1
#>

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& .\.venv\Scripts\pyinstaller.exe `
    --distpath dist `
    --workpath build `
    --noconfirm `
    .\packaging\photo_organizer.spec

Write-Host ""
Write-Host "Built: dist\photo_organizer\photo_organizer.exe"
Write-Host "Copy the whole dist\photo_organizer folder to move the app elsewhere."
