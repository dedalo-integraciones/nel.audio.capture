# Nel Audio Capture — Version 1.0 beta
### Windows 11 64-bit | Sistema de Captura de Audio

---

## ¿Qué hace esta app?

**Nel Audio Capture** graba simultáneamente:

| Fuente | Qué captura |
|--------|-------------|
| 🖥 **System Audio (WASAPI Loopback)** | Todo lo que suena por tus parlantes/auriculares: navegador, Google Meet, Zoom, Teams, Spotify, YouTube, cualquier app |
| 🎤 **Microphone Input** | Tu micrófono (entrada de audio por defecto del sistema) |

Las dos fuentes se mezclan automáticamente en un solo archivo de salida.

---

## Requisitos del Sistema

- **Windows 11** 64-bit (también funciona en Windows 10)
- **Python 3.10+** — https://python.org (marcar "Add to PATH")
- **ffmpeg** (solo para exportar MP3) — `winget install Gyan.FFmpeg`

---

## Instalación Rápida

### Opción A — Script automático (recomendado)
```
1. Clic derecho en INSTALL_WINDOWS.ps1
2. "Ejecutar con PowerShell" (como Administrador)
3. El script instala todo y genera NelAudioCapture.exe
```

### Opción B — Manual
```powershell
pip install -r requirements.txt
python nel_audio_capture.py
```

### Opción C — Solo ejecutar (sin instalar)
```
Doble clic en Run_NelAudioCapture.bat
```

---

## Cómo usar

1. **Seleccionar fuentes**: activar System Audio y/o Microphone
2. **Presionar ⏺ START** → comienza la grabación
3. **Ver los medidores VU** y la forma de onda en tiempo real
4. **Presionar ⏹ STOP** cuando termines
5. **Elegir formato** (MP3 o WAV) y carpeta de destino
6. **Presionar 💾 SAVE RECORDING**

Los archivos se guardan como `nel_capture_YYYYMMDD_HHMMSS.mp3/.wav`

---

## Formatos de salida

| Formato | Calidad | Tamaño | Requiere |
|---------|---------|--------|----------|
| **WAV** | Sin pérdida (PCM 16-bit, 44.1kHz, Stereo) | ~10 MB/min | Solo Python |
| **MP3** | 128k / 192k / 256k / 320k kbps | ~1-4 MB/min | ffmpeg en PATH |

---

## Compilar como .exe independiente

```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name NelAudioCapture nel_audio_capture.py
# Ejecutable en: dist/NelAudioCapture.exe
```

---

## Cómo funciona WASAPI Loopback

Windows permite abrir dispositivos de salida de audio (parlantes) como entradas de captura. Esto captura **todo el audio del sistema** independientemente de qué app lo produzca — sin necesidad de drivers virtuales de terceros como VB-Cable o Voicemeeter.

El motor de audio usa **PyAudio** con el flag `as_loopback=True` en el host WASAPI, que es exclusivo de Windows.

---

## Problemas comunes

| Problema | Solución |
|----------|----------|
| No se captura audio del sistema | Verificar que WASAPI esté disponible en el sistema (Control Panel → Sound) |
| MP3 falla | Instalar ffmpeg: `winget install Gyan.FFmpeg`, luego reiniciar |
| pyaudio no instala | Usar `pipwin install pyaudio` o el script INSTALL_WINDOWS.ps1 |
| Sin audio en la grabación | Verificar que el volumen del sistema no esté en 0 durante la grabación |

---

## Especificaciones Técnicas

- Sample Rate: 44100 Hz
- Channels: Stereo (2 canales)
- Bit Depth: 16-bit PCM
- Engine: WASAPI Loopback (Windows Audio Session API)
- Mezcla: Weighted mix (Sistema 70% + Micrófono 50%)
- GUI: tkinter (incluido en Python)

---

*Nel Audio Capture Version 1.0 beta — Developed for Windows 11 64-bit*
