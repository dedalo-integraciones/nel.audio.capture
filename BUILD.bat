@echo off
title Nel Audio Capture - Build Script
color 0B

echo.
echo  ==========================================
echo   Nel Audio Capture - Build Script
echo  ==========================================
echo.

:: Activar entorno virtual
echo [1/4] Activando entorno virtual...
call venv\Scripts\activate
if errorlevel 1 (
    echo  ERROR: No se pudo activar el venv.
    echo  Asegurate de estar en la carpeta del proyecto.
    pause
    exit /b 1
)

:: Actualizar dependencias
echo [2/4] Instalando/actualizando dependencias...
pip install pyinstaller pyaudio "numpy<2.0" pydub --quiet
if errorlevel 1 (
    echo  ERROR instalando dependencias.
    pause
    exit /b 1
)

:: Limpiar builds anteriores
echo [3/4] Limpiando builds anteriores...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist NelAudioCapture.spec del NelAudioCapture.spec

:: Compilar
   echo [4/4] Compilando NelAudioCapture.exe...
   pyinstaller --onefile --windowed --name "NelAudioCapture" --icon "assets\icon.ico" --add-data "assets;assets" --collect-all numpy --collect-all pyaudio nel_audio_capture.py

if errorlevel 1 (
    echo.
    echo  ERROR: La compilacion fallo. Revisa los mensajes de arriba.
    pause
    exit /b 1
)

echo.
echo  ==========================================
echo   BUILD EXITOSO!
echo   Ejecutable: dist\NelAudioCapture.exe
echo  ==========================================
echo.

:: Abrir carpeta dist automaticamente
explorer dist

pause
