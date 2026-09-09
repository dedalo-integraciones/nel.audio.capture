# Nel Audio Capture - Windows 11 Setup Script
# Run as Administrator in PowerShell
# Usage: Right-click -> Run with PowerShell (as Admin)

$ErrorActionPreference = "Stop"
$AppName = "Nel Audio Capture 1.0 beta"

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  $AppName - Windows 11 Installer" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/6] Checking Python installation..." -ForegroundColor Yellow
try {
    $pyver = python --version 2>&1
    Write-Host "  Found: $pyver" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found." -ForegroundColor Red
    Write-Host "  Please install Python 3.10+ from https://python.org" -ForegroundColor Red
    Write-Host "  Make sure to check 'Add Python to PATH' during install." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Upgrade pip
Write-Host "[2/6] Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "  Done." -ForegroundColor Green

# Install dependencies
Write-Host "[3/6] Installing audio dependencies..." -ForegroundColor Yellow
Write-Host "  Installing numpy..."
python -m pip install numpy --quiet
Write-Host "  Installing pyaudio (WASAPI loopback support)..."
python -m pip install pyaudio --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "  pyaudio pip install failed, trying pipwin fallback..." -ForegroundColor Yellow
    python -m pip install pipwin --quiet
    python -m pipwin install pyaudio --quiet
}
Write-Host "  Installing pydub (MP3 export)..."
python -m pip install pydub --quiet
Write-Host "  Done." -ForegroundColor Green

# Install ffmpeg for MP3
Write-Host "[4/6] Checking ffmpeg (required for MP3 export)..." -ForegroundColor Yellow
try {
    $ff = ffmpeg -version 2>&1 | Select-Object -First 1
    Write-Host "  Found: $ff" -ForegroundColor Green
} catch {
    Write-Host "  ffmpeg not found. Attempting install via winget..." -ForegroundColor Yellow
    try {
        winget install Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
        Write-Host "  ffmpeg installed. You may need to restart your terminal." -ForegroundColor Green
    } catch {
        Write-Host "  Could not auto-install ffmpeg." -ForegroundColor Yellow
        Write-Host "  For MP3 export: download from https://ffmpeg.org and add to PATH." -ForegroundColor Yellow
        Write-Host "  WAV export will work without ffmpeg." -ForegroundColor Yellow
    }
}

# Install PyInstaller for standalone exe
Write-Host "[5/6] Installing PyInstaller (to build .exe)..." -ForegroundColor Yellow
python -m pip install pyinstaller --quiet
Write-Host "  Done." -ForegroundColor Green

# Build EXE
Write-Host "[6/6] Building nel_audio_capture.exe..." -ForegroundColor Yellow
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

pyinstaller `
    --onefile `
    --windowed `
    --name "NelAudioCapture" `
    --icon "assets\icon.ico" `
    --add-data "assets;assets" `
    nel_audio_capture.py

if ($LASTEXITCODE -eq 0) {
    $exePath = Join-Path $scriptDir "dist\NelAudioCapture.exe"
    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host "  BUILD SUCCESSFUL!" -ForegroundColor Green
    Write-Host "  Executable: $exePath" -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host ""
    
    # Create Desktop shortcut
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut("$desktop\Nel Audio Capture.lnk")
    $shortcut.TargetPath = $exePath
    $shortcut.Description = "Nel Audio Capture 1.0 beta"
    $shortcut.Save()
    Write-Host "  Desktop shortcut created!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  Build failed. Run directly with:" -ForegroundColor Yellow
    Write-Host "  python nel_audio_capture.py" -ForegroundColor White
}

Write-Host ""
Read-Host "Press Enter to exit"
