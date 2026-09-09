@echo off
title Nel Audio Capture 1.0 beta
color 0B

echo.
echo  ==========================================
echo   Nel Audio Capture - Version 1.0 beta
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found.
    echo  Install from https://python.org ^(check "Add to PATH"^)
    pause
    exit /b 1
)

:: Install dependencies silently if missing
echo  Checking dependencies...
python -m pip install numpy pyaudio pydub --quiet --exists-action i 2>nul
if errorlevel 1 (
    echo  Note: Some packages could not be installed. 
    echo  Run INSTALL_WINDOWS.ps1 as Administrator for full setup.
)

echo  Launching Nel Audio Capture...
echo.
python "%~dp0nel_audio_capture.py"

if errorlevel 1 (
    echo.
    echo  An error occurred. See above for details.
    pause
)
