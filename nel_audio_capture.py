"""
Nel Audio Capture Version 1.0 beta
Windows 11 64-bit Audio Capture Application
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import sys
import wave
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

try:
    import ctypes
    HAS_CTYPES = True
except Exception:
    HAS_CTYPES = False

try:
    import pyaudio
    PYAUDIO_OK = True
except ImportError:
    PYAUDIO_OK = False

try:
    import pyaudiowpatch
    PYAUDIOWPATCH_OK = True
except ImportError:
    PYAUDIOWPATCH_OK = False

try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False

try:
    from pydub import AudioSegment
    PYDUB_OK = True
except ImportError:
    PYDUB_OK = False

try:
    import logging
    import sys as _sys
    LOGGING_OK = True
except ImportError:
    LOGGING_OK = False

DEBUG_MODE = os.environ.get("NEL_DEBUG", "0") == "1"

def _log(msg, level="info"):
    if not LOGGING_OK or not DEBUG_MODE:
        return
    logger = logging.getLogger("NelAudioCapture")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(h)
    getattr(logger, level)(msg)

# ── Verificar ffmpeg ─────────────────────────────────────────────────────────
def check_ffmpeg():
    """Retorna (bool, str) — disponible, ruta o mensaje"""
    path = shutil.which("ffmpeg")
    if path:
        return True, path
    # Buscar en rutas comunes de Windows
    common = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in common:
        if os.path.isfile(p):
            return True, p
    return False, ""

FFMPEG_OK, FFMPEG_PATH = check_ffmpeg()

APP_NAME    = "Nel Audio Capture"
APP_VERSION = "Version 1.0 beta"
SAMPLE_RATE = 44100
CHANNELS    = 2
CHUNK       = 1024
SAMPLE_WIDTH = 2

C = {
    "bg":       "#0D0F14",
    "surface":  "#141720",
    "panel":    "#1A1D28",
    "border":   "#252A3A",
    "accent":   "#00D4FF",
    "accent2":  "#7C3AED",
    "red":      "#FF3B5C",
    "green":    "#00E676",
    "yellow":   "#FFD600",
    "orange":   "#FF8C00",
    "text":     "#E8EAF0",
    "muted":    "#6B7280",
    "white":    "#FFFFFF",
}


# ── Device Scanner ────────────────────────────────────────────────────────────
def scan_audio_devices():
    """
    Escanea todos los dispositivos de audio y retorna listas clasificadas.
    Retorna: (wasapi_host_idx, loopback_devices, input_devices)
      - loopback_devices: lista de (idx, name) — dispositivos WASAPI de SALIDA
        (usados como loopback para capturar audio del sistema)
      - input_devices: lista de (idx, name) — dispositivos WASAPI de ENTRADA
        (micrófonos reales)
    """
    # Try to use pyaudiowpatch for better WASAPI support and index consistency
    if PYAUDIOWPATCH_OK:
        try:
            pa = pyaudiowpatch.PyAudio()
            wasapi_host = None
            wasapi_hosts = []
            for i in range(pa.get_host_api_count()):
                info = pa.get_host_api_info_by_index(i)
                name = info.get("name", "")
                _log(f"Host API {i}: {name}, devices={info.get('deviceCount', '?')}, default_in={info.get('defaultInputDevice')}, default_out={info.get('defaultOutputDevice')}")
                if "WASAPI" in name:
                    wasapi_host = i
                    wasapi_hosts.append(i)
            
            if not wasapi_hosts:
                pa.terminate()
                # Fall back to PyAudio below
            else:
                loopback_devs = []
                input_devs = []
                
                for host_idx in wasapi_hosts:
                    for i in range(pa.get_device_count()):
                        dev = pa.get_device_info_by_index(i)
                        if dev.get("hostApi") != host_idx:
                            continue
                        name = dev.get("name", "")
                        out_ch = dev.get("maxOutputChannels", 0)
                        in_ch = dev.get("maxInputChannels", 0)
                        _log(f"Device [{i}] {name}: in_ch={in_ch}, out_ch={out_ch}")
                        if out_ch > 0:
                            loopback_devs.append((i, name, out_ch))
                        if in_ch > 0:
                            input_devs.append((i, name, in_ch))

                pa.terminate()
                _log(f"Found {len(loopback_devs)} loopback, {len(input_devs)} input devices (via pyaudiowpatch)")
                return wasapi_host, loopback_devs, input_devs
        except Exception as e:
            _log(f"pyaudiowpatch device scan failed: {e}, falling back to PyAudio")
            # Fall through to PyAudio implementation below
    
    # PyAudio fallback
    if not PYAUDIO_OK:
        return None, [], []
    pa = pyaudio.PyAudio()
    wasapi_host = None
    wasapi_hosts = []
    for i in range(pa.get_host_api_count()):
        info = pa.get_host_api_info_by_index(i)
        name = info.get("name", "")
        _log(f"Host API {i}: {name}, devices={info.get('deviceCount', '?')}, default_in={info.get('defaultInputDevice')}, default_out={info.get('defaultOutputDevice')}")
        if "WASAPI" in name:
            wasapi_host = i
            wasapi_hosts.append(i)
    
    if not wasapi_hosts:
        pa.terminate()
        return None, [], []

    loopback_devs = []
    input_devs = []
    
    for host_idx in wasapi_hosts:
        for i in range(pa.get_device_count()):
            dev = pa.get_device_info_by_index(i)
            if dev.get("hostApi") != host_idx:
                continue
            name = dev.get("name", "")
            out_ch = dev.get("maxOutputChannels", 0)
            in_ch = dev.get("maxInputChannels", 0)
            _log(f"Device [{i}] {name}: in_ch={in_ch}, out_ch={out_ch}")
            if out_ch > 0:
                loopback_devs.append((i, name, out_ch))
            if in_ch > 0:
                input_devs.append((i, name, in_ch))

    pa.terminate()
    _log(f"Found {len(loopback_devs)} loopback, {len(input_devs)} input devices (via PyAudio)")
    return wasapi_host, loopback_devs, input_devs


def get_default_wasapi_loopback(pa, wasapi_host):
    """
    Encuentra el mejor dispositivo WASAPI de salida para loopback.
    Prioriza el dispositivo de salida por defecto del host WASAPI.
    """
    if wasapi_host is None:
        return None

    try:
        host_info = pa.get_host_api_info_by_index(wasapi_host)
        default_out = host_info.get("defaultOutputDevice")
        if default_out is not None:
            dev = pa.get_device_info_by_index(default_out)
            if dev.get("hostApi") == wasapi_host and dev.get("maxOutputChannels", 0) > 0:
                return default_out
    except Exception:
        pass

    # Fallback: primer dispositivo WASAPI de salida disponible
    for i in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(i)
        if (dev.get("hostApi") == wasapi_host and
                dev.get("maxOutputChannels", 0) > 0):
            return i
    return None


def get_default_wasapi_input(pa, wasapi_host):
    """
    Encuentra el mejor micrófono WASAPI (entrada física real).
    Excluye dispositivos que sean solo de salida o loopback.
    """
    if wasapi_host is None:
        return None

    try:
        host_info = pa.get_host_api_info_by_index(wasapi_host)
        default_in = host_info.get("defaultInputDevice")
        if default_in is not None:
            dev = pa.get_device_info_by_index(default_in)
            if (dev.get("hostApi") == wasapi_host and
                    dev.get("maxInputChannels", 0) > 0 and
                    dev.get("maxOutputChannels", 0) == 0):
                return default_in
    except Exception:
        pass

    # Fallback: primer dispositivo WASAPI de entrada pura (sin salida)
    for i in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(i)
        if (dev.get("hostApi") == wasapi_host and
                dev.get("maxInputChannels", 0) > 0 and
                dev.get("maxOutputChannels", 0) == 0):
            return i

    # Último recurso: cualquier entrada WASAPI
    for i in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(i)
        if (dev.get("hostApi") == wasapi_host and
                dev.get("maxInputChannels", 0) > 0):
            return i
    return None


# ── Audio Engine ─────────────────────────────────────────────────────────────
class AudioEngine:
    """
    Motor de grabación dual:
      - Stream SISTEMA: WASAPI Loopback sobre el dispositivo de SALIDA por defecto
        → captura todo el audio interno (navegador, Zoom, Meet, WhatsApp, Spotify…)
        → completamente independiente del volumen físico de los parlantes
      - Stream MIC: WASAPI sobre el dispositivo de ENTRADA por defecto
        → captura el micrófono físico real
    Ambos streams se mezclan al guardar.
    """

    def __init__(self, on_level_cb=None, on_status_cb=None, sys_gain=0.7, mic_gain=0.5):
        self.on_level   = on_level_cb  or (lambda l, r: None)
        self.on_status  = on_status_cb or (lambda s: None)
        self.pa         = None
        self.recording  = False
        self.frames_sys = []
        self.frames_mic = []
        self._thread_sys = None
        self._thread_mic = None
        self._lock       = threading.Lock()
        self._wasapi_host = None
        self.sys_device_name = ""
        self.mic_device_name = ""
        self.sys_gain = max(0.0, min(1.0, sys_gain))
        self.mic_gain = max(0.0, min(1.0, mic_gain))
        # Inicializar pyaudiowpatch si está disponible para WASAPI loopback
        self._pa_wp = pyaudiowpatch.PyAudio() if PYAUDIOWPATCH_OK else None

    def update_gains(self, sys_gain=None, mic_gain=None):
        """
        Actualiza las ganancias de mezcla dinámicamente durante la grabación
        """
        if sys_gain is not None:
            self.sys_gain = max(0.0, min(1.0, sys_gain))
        if mic_gain is not None:
            self.mic_gain = max(0.0, min(1.0, mic_gain))

    def start(self, capture_system=True, capture_mic=True,
              sys_device=None, mic_device=None):
        if not PYAUDIO_OK:
            self.on_status("ERROR: PyAudio no instalado")
            return False

        # Re-initialize pyaudiowpatch instance if it was terminated
        if PYAUDIOWPATCH_OK and self._pa_wp is None:
            try:
                self._pa_wp = pyaudiowpatch.PyAudio()
                _log("Re-initialized pyaudiowpatch PyAudio instance")
            except Exception as e:
                _log(f"Failed to re-initialize pyaudiowpatch: {e}", "debug")
                self._pa_wp = None

        self.pa = pyaudio.PyAudio()
        self.recording = True
        self.frames_sys.clear()
        self.frames_mic.clear()

        # Detectar host WASAPI
        self._wasapi_host = None
        for i in range(self.pa.get_host_api_count()):
            info = self.pa.get_host_api_info_by_index(i)
            if "WASAPI" in info.get("name", ""):
                self._wasapi_host = i
                _log(f"Using WASAPI host {i}: {info.get('name')}")
                break

        if self._wasapi_host is None:
            self.on_status("sys_err: No WASAPI host encontrado")
            self.pa.terminate()
            self.pa = None
            return False

        if capture_system:
            if sys_device is None:
                if PYAUDIOWPATCH_OK and self._pa_wp is not None:
                    try:
                        # Get the default OUTPUT device (not loopback), then pyaudiowpatch
                        # will find the corresponding loopback analogue
                        output_dev = self._pa_wp.get_default_wasapi_device(d_out=True)
                        sys_device = output_dev['index']
                        self.sys_device_name = output_dev.get('name', '')
                        _log(f"Using pyaudiowpatch default output [{sys_device}]: {self.sys_device_name}")
                    except Exception as e:
                        _log(f"pyaudiowpatch get_default_wasapi_device failed: {e}", "debug")
                        sys_device = get_default_wasapi_loopback(self.pa, self._wasapi_host)
                else:
                    sys_device = get_default_wasapi_loopback(self.pa, self._wasapi_host)
            if sys_device is None:
                self.on_status("sys_err: No se encontró dispositivo WASAPI de salida para loopback")
                self.pa.terminate()
                self.pa = None
                return False
            if not self.sys_device_name:
                try:
                    dev_info = self.pa.get_device_info_by_index(sys_device)
                    self.sys_device_name = dev_info.get("name", "")
                    _log(f"System device: [{sys_device}] {self.sys_device_name}")
                except Exception as e:
                    self.on_status(f"sys_err: Cannot get device info: {e}")
                    self.pa.terminate()
                    self.pa = None
                    return False
            self._thread_sys = threading.Thread(
                target=self._record_loopback, args=(sys_device,), daemon=True)
            self._thread_sys.start()

        if capture_mic:
            if mic_device is None:
                if PYAUDIOWPATCH_OK and self._pa_wp is not None:
                    try:
                        # Get the default INPUT device, then pyaudiowpatch
                        # will use it directly (input devices don't need loopback conversion)
                        input_dev = self._pa_wp.get_default_wasapi_device(d_in=True)
                        mic_device = input_dev['index']
                        self.mic_device_name = input_dev.get('name', '')
                        _log(f"Using pyaudiowpatch default input [{mic_device}]: {self.mic_device_name}")
                    except Exception as e:
                        _log(f"pyaudiowpatch get_default_wasapi_device failed: {e}", "debug")
                        mic_device = get_default_wasapi_input(self.pa, self._wasapi_host)
                else:
                    mic_device = get_default_wasapi_input(self.pa, self._wasapi_host)
            if mic_device is not None:
                if not self.mic_device_name:
                    try:
                        dev_info = self.pa.get_device_info_by_index(mic_device)
                        self.mic_device_name = dev_info.get("name", "")
                        _log(f"Mic device: [{mic_device}] {self.mic_device_name}")
                    except Exception:
                        pass
            self._thread_mic = threading.Thread(
                target=self._record_mic, args=(mic_device,), daemon=True)
            self._thread_mic.start()

        self.on_status("recording")
        return True

    def stop(self):
        self.recording = False
        for t in [self._thread_sys, self._thread_mic]:
            if t:
                t.join(timeout=3)
        if self.pa:
            self.pa.terminate()
        if self._pa_wp:
            self._pa_wp.terminate()
        self.pa = None
        self._pa_wp = None
        self.on_status("stopped")

    def _open_loopback_pyaudiowpatch(self, device_index):
        """
        Abre stream de loopback usando pyaudiowpatch (mejor soporte WASAPI).
        Usa get_wasapi_loopback_analogue_by_index para obtener el dispositivo loopback
        correspondiente al dispositivo de salida WASAPI.
        """
        if not self._pa_wp:
            _log("pyaudiowpatch not available", "error")
            return None, SAMPLE_RATE, 2
        
        # Usar pyaudiowpatch para obtener el dispositivo loopback de forma directa
        try:
            loopback_info = self._pa_wp.get_wasapi_loopback_analogue_by_index(device_index)
            loopback_idx = loopback_info['index']
            dev_rate = int(loopback_info.get('defaultSampleRate', SAMPLE_RATE))
            dev_ch = 2
            _log(f"Loopback device [{loopback_idx}]: {loopback_info.get('name')}, rate={dev_rate}")
        except Exception as e:
            _log(f"get_wasapi_loopback_analogue_by_index failed: {e}", "debug")
            # Fallback: intentar con el dispositivo loopback por defecto
            try:
                loopback_info = self._pa_wp.get_default_wasapi_loopback()
                loopback_idx = loopback_info['index']
                dev_rate = int(loopback_info.get('defaultSampleRate', SAMPLE_RATE))
                dev_ch = 2
                _log(f"Default loopback device [{loopback_idx}]: {loopback_info.get('name')}, rate={dev_rate}")
            except Exception as e2:
                _log(f"get_default_wasapi_loopback failed: {e2}", "error")
                return None, SAMPLE_RATE, 2

        # Abrir el dispositivo loopback como stream de entrada usando pyaudiowpatch PyAudio
        try:
            stream = self._pa_wp.open(
                format=pyaudio.paInt16,
                channels=2,
                rate=dev_rate,
                input=True,
                input_device_index=loopback_idx,
                frames_per_buffer=CHUNK,
            )
            self.on_status(f"loopback: OK ({dev_ch}ch, {dev_rate}Hz) via pyaudiowpatch")
            _log(f"Loopback stream opened: {dev_ch}ch, {dev_rate}Hz")
            return stream, dev_rate, dev_ch
        except Exception as e:
            _log(f"Failed to open pyaudiowpatch loopback stream: {e}", "error")
            return None, SAMPLE_RATE, 2

    def _open_loopback_stream(self, device_index):
        """
        Intenta abrir el stream de loopback con distintas configuraciones
        para máxima compatibilidad con diferentes placas de audio.
        Usa pyaudiowpatch cuando está disponible (soporta WASAPI loopback).
        """
        if device_index is None:
            _log("No device index provided for loopback stream")
            return None, SAMPLE_RATE, 2

        # Usar pyaudiowpatch cuando esté disponible (soporta WASAPI loopback)
        if PYAUDIOWPATCH_OK and self._pa_wp is not None:
            try:
                return self._open_loopback_pyaudiowpatch(device_index)
            except Exception as e:
                _log(f"pyaudiowpatch loopback failed: {e}", "debug")
                self.on_status(f"loopback_err: pyaudiowpatch failed: {e}")

        # Fallback a PyAudio estándar (puede no funcionar en algunos sistemas)
        try:
            dev_info = self.pa.get_device_info_by_index(device_index)
        except Exception as e:
            _log(f"Cannot get device info for index {device_index}: {e}", "error")
            self.on_status(f"loopback_err: Cannot get device info: {e}")
            return None, SAMPLE_RATE, 2

        ch = min(2, dev_info.get("maxOutputChannels", 2))
        dev_rate = int(dev_info.get("defaultSampleRate", SAMPLE_RATE))
        _log(f"Device [{device_index}] info: {dev_info.get('name')}, maxOut={dev_info.get('maxOutputChannels')}, defaultRate={dev_rate}")

        # Intentar con sample rate nativo primero
        rates_to_try = [dev_rate] + [r for r in [44100, 48000, 96000, 22050] if r != dev_rate]
        channels_to_try = [ch, 2, 1] if ch > 1 else [1, 2]

        for rate in rates_to_try:
            for attempt_ch in channels_to_try:
                try:
                    stream = self.pa.open(
                        format=pyaudio.paInt16,
                        channels=attempt_ch,
                        rate=int(rate),
                        input=True,
                        input_device_index=device_index,
                        as_loopback=True,
                        frames_per_buffer=CHUNK,
                    )
                    self.on_status(f"loopback: OK ({attempt_ch}ch, {int(rate)}Hz)")
                    _log(f"Loopback stream opened: {attempt_ch}ch, {int(rate)}Hz")
                    return stream, int(rate), attempt_ch
                except Exception as err:
                    _log(f"Failed to open stream {attempt_ch}ch @ {rate}Hz: {err}", "debug")
                    continue

        _log(f"Could not open loopback stream for device {device_index}", "error")
        self.on_status(f"loopback_err: Could not open device {device_index}")
        return None, SAMPLE_RATE, 2

    def _record_loopback(self, device_index):
        """
        Captura el audio INTERNO del sistema via WASAPI Loopback.
        Opera sobre el stream digital — independiente del volumen de parlantes.
        """
        if device_index is None:
            _log("No device index provided for loopback recording")
            self.on_status("sys_err: No se encontró dispositivo de salida WASAPI")
            return
        try:
            stream, actual_rate, actual_ch = self._open_loopback_stream(device_index)
            if stream is None:
                _log("No se pudo abrir loopback stream")
                self.on_status("sys_err: No se pudo abrir loopback")
                return

            iteration = 0
            while self.recording:
                iteration += 1
                if iteration % 100 == 0:
                    _log(f"Loopback recording iteration {iteration}")
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    # Convertir a estéreo 44100 si difiere
                    if actual_ch != CHANNELS or actual_rate != SAMPLE_RATE:
                        data = self._resample(data, actual_ch, actual_rate)
                    with self._lock:
                        self.frames_sys.append(data)
                    self._push_level(data, "sys")
                except Exception as e:
                    _log(f"Error reading loopback stream (iter {iteration}): {e}", "error")
                    self.on_status(f"sys_err: Loopback read error: {e}")
                    break

            stream.stop_stream()
            stream.close()
            _log("Loopback recording stream closed")
        except Exception as e:
            _log(f"Critical error in loopback recording: {e}", "error")
            self.on_status(f"sys_err:{e}")

    def _record_mic(self, device_index):
        """
        Captura el micrófono físico (entrada real del sistema).
        """
        if device_index is None:
            _log("No device index provided for mic recording")
            self.on_status("mic_err: No se encontró dispositivo de entrada WASAPI")
            return
        try:
            dev_info = self.pa.get_device_info_by_index(device_index)
            ch = min(2, dev_info.get("maxInputChannels", 2))
            _log(f"Mic device [{device_index}]: {dev_info.get('name')}, input_channels={dev_info.get('maxInputChannels')}")

            selected_rate = None
            for rate in [44100, 48000, 96000, 22050]:
                try:
                    stream = self.pa.open(
                        format=pyaudio.paInt16,
                        channels=ch,
                        rate=rate,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=CHUNK,
                    )
                    actual_rate = rate
                    actual_ch = ch
                    _log(f"Mic stream opened at {rate}Hz")
                    break
                except Exception as err:
                    _log(f"Failed to open mic at {rate}Hz: {err}", "debug")
                    continue
            else:
                _log("Could not open any mic sample rate", "error")
                self.on_status("mic_err: No se pudo abrir el micrófono")
                return

            iteration = 0
            while self.recording:
                iteration += 1
                if iteration % 100 == 0:
                    _log(f"Mic recording iteration {iteration}")
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    if actual_ch != CHANNELS or actual_rate != SAMPLE_RATE:
                        data = self._resample(data, actual_ch, actual_rate)
                    with self._lock:
                        self.frames_mic.append(data)
                    self._push_level(data, "mic")
                except Exception as e:
                    _log(f"Error reading mic stream (iter {iteration}): {e}", "error")
                    self.on_status(f"mic_err: Mic read error: {e}")
                    break

            stream.stop_stream()
            stream.close()
            _log("Mic recording stream closed")
        except Exception as e:
            _log(f"Critical error in mic recording: {e}", "error")
            self.on_status(f"mic_err:{e}")

    def _resample(self, data, src_ch, src_rate):
        """Convierte audio a estéreo 44100 Hz para normalizar."""
        if not NUMPY_OK:
            return data
        try:
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            # Mono → estéreo
            if src_ch == 1:
                samples = np.column_stack([samples, samples]).flatten()
            # Recortar a pares si es multichannel
            elif src_ch > 2:
                samples = samples.reshape(-1, src_ch)[:, :2].flatten()
            # Resamplear si es necesario
            if src_rate != SAMPLE_RATE:
                ratio = SAMPLE_RATE / src_rate
                n_out = int(len(samples) * ratio)
                if NUMPY_OK and n_out > 0:
                    indices = np.linspace(0, len(samples) - 1, n_out)
                    samples = np.interp(indices, np.arange(len(samples)), samples)
            return np.clip(samples, -32768, 32767).astype(np.int16).tobytes()
        except Exception:
            return data

    def _push_level(self, data, channel):
        if not NUMPY_OK:
            return
        try:
            s = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            rms = np.sqrt(np.mean(s ** 2))
            lvl = min(1.0, rms / 32768.0 * 8)
            if channel == "sys":
                self.on_level(lvl, 0)
            else:
                self.on_level(0, lvl)
        except Exception:
            pass

    def _mix(self):
        if not NUMPY_OK:
            return b"".join(self.frames_sys) or b"".join(self.frames_mic)

        def to_np(frames):
            if not frames:
                return None
            return np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32)

        s = to_np(self.frames_sys)
        m = to_np(self.frames_mic)

        if s is None and m is None:
            return b""
        if s is None:
            mixed = m * self.mic_gain
        elif m is None:
            mixed = s * self.sys_gain
        else:
            n = min(len(s), len(m))
            mixed = s[:n] * self.sys_gain + m[:n] * self.mic_gain

        return np.clip(mixed, -32768, 32767).astype(np.int16).tobytes()

    def save_wav(self, path):
        data = self._mix()
        if not data:
            return False
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(data)
        return True

    def save_mp3(self, path, bitrate="192k"):
        if not PYDUB_OK:
            return False, "pydub no instalado"
        if not FFMPEG_OK:
            return False, "ffmpeg_missing"
        tmp = str(path).replace(".mp3", "_tmp.wav")
        if not self.save_wav(tmp):
            return False, "Sin datos de audio"
        try:
            if FFMPEG_PATH:
                AudioSegment.converter = FFMPEG_PATH
            AudioSegment.from_wav(tmp).export(str(path), format="mp3", bitrate=bitrate)
            os.remove(tmp)
            return True, ""
        except Exception as e:
            try:
                os.remove(tmp)
            except Exception:
                pass
            return False, str(e)


# ── VU Meter ─────────────────────────────────────────────────────────────────
class VUMeter(tk.Canvas):
    def __init__(self, parent, label="", **kw):
        super().__init__(parent, bg=C["panel"], highlightthickness=0, height=22, **kw)
        self._label = label
        self._level = 0.0
        self._peak  = 0.0
        self._ptimer = 0
        self.bind("<Configure>", lambda e: self._draw())

    def set_level(self, v):
        self._level = max(0.0, min(1.0, v))
        if self._level >= self._peak:
            self._peak = self._level
            self._ptimer = 30
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 300
        h = self.winfo_height() or 22
        p = 2
        self.create_rectangle(p, p, w-p, h-p, fill=C["border"], outline="")
        bw = int((w - 2*p) * self._level)
        if bw > 0:
            for i in range(bw):
                frac = i / (w - 2*p)
                c = C["green"] if frac < 0.6 else (C["yellow"] if frac < 0.85 else C["red"])
                self.create_rectangle(p+i, p, p+i+1, h-p, fill=c, outline="")
        if self._peak > 0:
            px = p + int((w-2*p) * self._peak)
            self.create_rectangle(px-2, p, px+2, h-p, fill=C["white"], outline="")
            if self._ptimer > 0:
                self._ptimer -= 1
            else:
                self._peak = max(0, self._peak - 0.01)
        self.create_text(p+4, h//2, text=self._label, anchor="w", fill=C["muted"], font=("Consolas", 8))


# ── Waveform ──────────────────────────────────────────────────────────────────
class Waveform(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["panel"], highlightthickness=0, height=80, **kw)
        self._samples = [0.0]*200
        self._active  = False
        self._aid = None
        self.bind("<Configure>", lambda e: self._draw())

    def start(self):
        self._active = True
        self._anim()

    def stop(self):
        self._active = False
        if self._aid:
            self.after_cancel(self._aid)

    def push(self, v):
        self._samples.append(v)
        if len(self._samples) > 600:
            self._samples.pop(0)

    def _anim(self):
        self._draw()
        if self._active:
            self._aid = self.after(40, self._anim)

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or 500
        h = self.winfo_height() or 80
        mid = h // 2
        pts = self._samples[-w:]
        if not pts:
            return
        step = w / max(len(pts), 1)
        for i, v in enumerate(pts):
            x = int(i * step)
            amp = int(v * (mid - 4))
            self.create_line(x, mid-amp, x, mid+amp, fill=C["accent"], width=1)
        self.create_line(0, mid, w, mid, fill=C["border"], dash=(4,4))


# ── Timer ─────────────────────────────────────────────────────────────────────
class RecordTimer:
    def __init__(self, var):
        self._var   = var
        self._start = None
        self._run   = False
        self._root  = None
        self._aid   = None

    def attach(self, root):
        self._root = root

    def start(self):
        self._start = time.time()
        self._run = True
        self._tick()

    def stop(self):
        self._run = False
        if self._aid and self._root:
            self._root.after_cancel(self._aid)

    def reset(self):
        self._var.set("00:00:00")

    def _tick(self):
        if not self._run:
            return
        e = int(time.time() - self._start)
        h, r = divmod(e, 3600)
        m, s = divmod(r, 60)
        self._var.set(f"{h:02d}:{m:02d}:{s:02d}")
        if self._root:
            self._aid = self._root.after(1000, self._tick)


# ── Ventana instalador ffmpeg ─────────────────────────────────────────────────
class FFmpegWarningDialog(tk.Toplevel):
    """
    Ventana interactiva para instalar ffmpeg paso a paso.
    Pasos: 1) Confirmar instalación  2) Abrir PowerShell Admin  3) Ejecutar winget
           4) Verificar instalación  5) Resultado
    """

    STEPS = [
        "inicio",
        "confirmar",
        "powershell",
        "instalar",
        "verificar",
        "listo",
        "manual",
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        self.title("Instalar ffmpeg — MP3 para Nel Audio Capture")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()

        W, H = 560, 480
        self.geometry(f"{W}x{H}")
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - W) // 2
        y = (self.winfo_screenheight() - H) // 2
        self.geometry(f"{W}x{H}+{x}+{y}")

        self._step = 0
        self._proc = None

        # Contenedor principal
        self._content = tk.Frame(self, bg=C["bg"])
        self._content.pack(fill="both", expand=True, padx=0, pady=0)

        # Footer fijo con botones
        self._footer = tk.Frame(self, bg=C["surface"], height=64)
        self._footer.pack(fill="x", side="bottom")
        self._footer.pack_propagate(False)

        self._btn_left  = tk.Button(self._footer, text="", command=self._action_left,
            relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"),
            padx=20, pady=10)
        self._btn_left.pack(side="left", padx=(16,8), pady=12)

        self._btn_right = tk.Button(self._footer, text="", command=self._action_right,
            relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"),
            padx=20, pady=10)
        self._btn_right.pack(side="right", padx=(8,16), pady=12)

        self._progress_lbl = tk.Label(self._footer, text="", fg=C["muted"],
            bg=C["surface"], font=("Segoe UI", 8))
        self._progress_lbl.pack(side="left", padx=8)

        self._show_step_inicio()

    # ── Helpers UI ────────────────────────────────────────────────────────────
    def _clear(self):
        for w in self._content.winfo_children():
            w.destroy()

    def _header(self, icon, title, subtitle="", icon_color=None):
        icon_color = icon_color or C["yellow"]
        tk.Label(self._content, text=icon, fg=icon_color, bg=C["bg"],
                 font=("Segoe UI", 40)).pack(pady=(24, 0))
        tk.Label(self._content, text=title, fg=C["white"], bg=C["bg"],
                 font=("Segoe UI", 14, "bold")).pack(pady=(4, 0))
        if subtitle:
            tk.Label(self._content, text=subtitle, fg=C["muted"], bg=C["bg"],
                     font=("Segoe UI", 9), wraplength=500, justify="center").pack(pady=(4, 12))

    def _panel(self, rows):
        """rows = list of (label, value, value_color)"""
        p = tk.Frame(self._content, bg=C["panel"],
                     highlightbackground=C["border"], highlightthickness=1)
        p.pack(fill="x", padx=28, pady=6)
        for label, value, color in rows:
            row = tk.Frame(p, bg=C["panel"])
            row.pack(fill="x", padx=14, pady=5)
            tk.Label(row, text=label, fg=C["muted"], bg=C["panel"],
                     font=("Segoe UI", 8), anchor="w", width=20).pack(side="left")
            tk.Label(row, text=value, fg=color, bg=C["panel"],
                     font=("Consolas", 9), anchor="w").pack(side="left")
        return p

    def _cmd_box(self, command):
        """Caja con el comando a ejecutar y botón copiar."""
        frame = tk.Frame(self._content, bg=C["border"],
                         highlightbackground=C["accent"], highlightthickness=1)
        frame.pack(fill="x", padx=28, pady=8)
        inner = tk.Frame(frame, bg=C["border"])
        inner.pack(fill="x", padx=2, pady=2)
        tk.Label(inner, text=command, fg=C["accent"], bg=C["border"],
                 font=("Consolas", 11, "bold"), anchor="w").pack(side="left", padx=12, pady=8)
        tk.Button(inner, text="📋 Copiar", command=lambda: self._copy(command),
                  bg=C["accent2"], fg=C["white"], relief="flat",
                  font=("Segoe UI", 8), cursor="hand2", padx=8).pack(side="right", padx=8)

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copiado", f"Copiado al portapapeles:\n{text}", parent=self)

    def _set_buttons(self, left_text, left_bg, left_fg, right_text, right_bg, right_fg,
                     left_enabled=True, right_enabled=True):
        self._btn_left.config(text=left_text, bg=left_bg, fg=left_fg,
            state="normal" if left_enabled else "disabled",
            activebackground=left_bg, activeforeground=left_fg)
        self._btn_right.config(text=right_text, bg=right_bg, fg=right_fg,
            state="normal" if right_enabled else "disabled",
            activebackground=right_bg, activeforeground=right_fg)

    def _set_progress(self, text):
        self._progress_lbl.config(text=text)

    # ── Pasos ─────────────────────────────────────────────────────────────────
    def _show_step_inicio(self):
        self._step = 0
        self._clear()
        self._header("⚠", "ffmpeg no está instalado",
                     "El formato MP3 requiere ffmpeg.\nPodés instalarlo ahora en menos de 2 minutos, o usar WAV sin necesidad de nada.")

        self._panel([
            ("¿Qué es ffmpeg?",   "Herramienta gratuita para audio/video", C["text"]),
            ("¿Es seguro?",       "Sí — es software de código abierto",    C["green"]),
            ("¿Cuánto pesa?",     "~100 MB",                               C["text"]),
            ("Método de install", "winget (incluido en Windows 11)",        C["text"]),
            ("Requiere admin?",   "Sí — PowerShell como Administrador",     C["yellow"]),
        ])

        tk.Label(self._content,
                 text="¿Querés instalar ffmpeg ahora para habilitar MP3?",
                 fg=C["white"], bg=C["bg"],
                 font=("Segoe UI", 10, "bold")).pack(pady=(12, 0))

        self._set_buttons(
            "✖  No, usar WAV",   C["border"], C["muted"],
            "✔  Sí, instalar",   C["green"],  C["bg"],
        )
        self._set_progress("Paso 1 de 4")

    def _action_left(self):
        if self._step == 0:
            self.destroy()
        elif self._step in (1, 2, 3):
            self._show_step_inicio()
        elif self._step == 4:
            self._show_step_inicio()
        elif self._step in (5, 6):
            self.destroy()

    def _action_right(self):
        if self._step == 0:
            self._show_step_powershell()
        elif self._step == 1:
            self._show_step_instalar()
        elif self._step == 2:
            self._show_step_verificar()
        elif self._step == 3:
            self._show_step_verificar()
        elif self._step == 4:
            self._recheck()
        elif self._step == 5:
            self.destroy()
        elif self._step == 6:
            self._show_step_manual()

    def _show_step_powershell(self):
        self._step = 1
        self._clear()
        self._header("💻", "Abrí PowerShell como Administrador",
                     "Necesitamos permisos de administrador para instalar ffmpeg.")

        p = tk.Frame(self._content, bg=C["panel"],
                     highlightbackground=C["border"], highlightthickness=1)
        p.pack(fill="x", padx=28, pady=8)

        steps_ui = [
            ("①", "Presioná  Windows + X"),
            ("②", 'Hacé clic en  "Terminal (Administrador)"'),
            ("③", "Si aparece un aviso de UAC, hacé clic en  Sí"),
            ("④", "Volvé acá y presioná  Continuar →"),
        ]
        for icon, text in steps_ui:
            row = tk.Frame(p, bg=C["panel"])
            row.pack(fill="x", padx=14, pady=6)
            tk.Label(row, text=icon, fg=C["accent"], bg=C["panel"],
                     font=("Segoe UI", 14, "bold"), width=3).pack(side="left")
            tk.Label(row, text=text, fg=C["text"], bg=C["panel"],
                     font=("Segoe UI", 10), anchor="w").pack(side="left", padx=8)

        tk.Label(self._content,
                 text="¿Ya tenés PowerShell abierto como Administrador?",
                 fg=C["yellow"], bg=C["bg"],
                 font=("Segoe UI", 9, "bold")).pack(pady=(10, 0))

        self._set_buttons(
            "← Volver",       C["border"],  C["muted"],
            "Continuar →",    C["accent"],  C["bg"],
        )
        self._set_progress("Paso 2 de 4")

    def _show_step_instalar(self):
        self._step = 2
        self._clear()
        self._header("⚙", "Ejecutá este comando en PowerShell",
                     "Copiá el comando y pegalo en PowerShell (Ctrl+V o clic derecho → Pegar).")

        self._cmd_box("winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements")

        p = tk.Frame(self._content, bg=C["panel"],
                     highlightbackground=C["border"], highlightthickness=1)
        p.pack(fill="x", padx=28, pady=8)

        notas = [
            ("⏱", "Tarda entre 1 y 3 minutos según tu conexión"),
            ("📦", "Descarga ~100 MB desde el servidor oficial"),
            ("✅", "Al terminar verás 'Successfully installed'"),
            ("🔄", "NO cierres PowerShell hasta que termine"),
        ]
        for icon, text in notas:
            row = tk.Frame(p, bg=C["panel"])
            row.pack(fill="x", padx=14, pady=5)
            tk.Label(row, text=icon, fg=C["accent"], bg=C["panel"],
                     font=("Segoe UI", 11), width=3).pack(side="left")
            tk.Label(row, text=text, fg=C["text"], bg=C["panel"],
                     font=("Segoe UI", 9), anchor="w").pack(side="left", padx=8)

        tk.Label(self._content,
                 text="¿El comando terminó con éxito ('Successfully installed')?",
                 fg=C["yellow"], bg=C["bg"],
                 font=("Segoe UI", 9, "bold")).pack(pady=(10, 0))

        self._set_buttons(
            "← Volver",          C["border"], C["muted"],
            "Sí, terminó →",     C["green"],  C["bg"],
        )
        self._set_progress("Paso 3 de 4")

    def _show_step_verificar(self):
        self._step = 3
        self._clear()
        self._header("🔍", "Verificando instalación…",
                     "Buscando ffmpeg en el sistema…")
        self._set_buttons("← Volver", C["border"], C["muted"],
                          "Verificando…", C["border"], C["muted"],
                          right_enabled=False)
        self._set_progress("Verificando…")
        self.update()
        self.after(1200, self._do_verify)

    def _do_verify(self):
        ok, path = check_ffmpeg()
        if ok:
            self._show_step_listo(path)
        else:
            self._show_step_no_encontrado()

    def _recheck(self):
        self._show_step_verificar()

    def _show_step_listo(self, path):
        self._step = 5
        global FFMPEG_OK, FFMPEG_PATH
        FFMPEG_OK   = True
        FFMPEG_PATH = path
        self._clear()
        self._header("✅", "¡ffmpeg instalado correctamente!",
                     "El formato MP3 ya está disponible en Nel Audio Capture.", C["green"])

        self._panel([
            ("Estado",   "Instalado y funcionando",  C["green"]),
            ("Ruta",     path,                        C["accent"]),
            ("MP3",      "Habilitado ✅",              C["green"]),
        ])

        tk.Label(self._content,
                 text="Cerrá esta ventana y seleccioná MP3 en las opciones de guardado.",
                 fg=C["text"], bg=C["bg"],
                 font=("Segoe UI", 9), wraplength=480, justify="center").pack(pady=(12, 0))

        self._set_buttons(
            "",              C["bg"],      C["bg"],
            "🎉  ¡Listo!",   C["green"],  C["bg"],
        )
        self._btn_left.config(state="disabled")
        self._set_progress("✅ Instalación completada")

        # Actualizar la UI principal
        try:
            self._parent._refresh_ffmpeg_status()
        except Exception:
            pass

    def _show_step_no_encontrado(self):
        self._step = 4
        self._clear()
        self._header("❌", "ffmpeg no encontrado",
                     "El sistema no detectó ffmpeg. Puede que necesites reiniciar la app\no que la instalación no haya terminado correctamente.")

        self._panel([
            ("Estado",    "No encontrado en PATH",          C["red"]),
            ("Solución A","Cerrá y volvé a abrir esta app", C["yellow"]),
            ("Solución B","Reiniciá Windows y volvé",        C["yellow"]),
            ("Solución C","Instalá manualmente (ver abajo)", C["muted"]),
        ])

        tk.Label(self._content,
                 text="¿Querés reintentar la verificación?",
                 fg=C["white"], bg=C["bg"],
                 font=("Segoe UI", 9, "bold")).pack(pady=(10, 0))

        self._set_buttons(
            "← Empezar de nuevo",   C["border"],  C["muted"],
            "🔄 Reverificar",        C["accent"],  C["bg"],
        )
        self._set_progress("ffmpeg no detectado")

    def _show_step_manual(self):
        self._step = 6
        self._clear()
        self._header("📥", "Instalación manual de ffmpeg",
                     "Si winget no funciona, podés instalar ffmpeg manualmente.")

        p = tk.Frame(self._content, bg=C["panel"],
                     highlightbackground=C["border"], highlightthickness=1)
        p.pack(fill="x", padx=28, pady=8)

        pasos = [
            ("①", "Ir a:  https://ffmpeg.org/download.html"),
            ("②", "Descargar la versión Windows 64-bit"),
            ("③", "Descomprimir en  C:\\ffmpeg\\"),
            ("④", "Agregar  C:\\ffmpeg\\bin  al PATH del sistema"),
            ("⑤", "Reiniciar Nel Audio Capture"),
        ]
        for icon, text in pasos:
            row = tk.Frame(p, bg=C["panel"])
            row.pack(fill="x", padx=14, pady=5)
            tk.Label(row, text=icon, fg=C["accent"], bg=C["panel"],
                     font=("Segoe UI", 12, "bold"), width=3).pack(side="left")
            tk.Label(row, text=text, fg=C["text"], bg=C["panel"],
                     font=("Segoe UI", 9), anchor="w").pack(side="left", padx=8)

        self._set_buttons(
            "Cerrar",   C["border"], C["muted"],
            "",         C["bg"],     C["bg"],
        )
        self._btn_right.config(state="disabled")
        self._set_progress("Instalación manual")


# ── App Principal ─────────────────────────────────────────────────────────────
class NelAudioCaptureApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — {APP_VERSION}")
        self.geometry("1200x850")
        self.minsize(900, 700)
        self.configure(bg=C["bg"])
        self.resizable(True, True)

        if HAS_CTYPES and sys.platform == "win32":
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass

        self._recording   = False
        self._engine      = None
        self._timer_var   = tk.StringVar(value="00:00:00")
        self._timer       = RecordTimer(self._timer_var)
        self._timer.attach(self)
        self._status_var      = tk.StringVar(value="Listo — seleccioná las fuentes y presioná START")
        self._sys_audio       = tk.BooleanVar(value=True)
        self._mic_audio       = tk.BooleanVar(value=True)
        self._sys_device_sel  = tk.StringVar()
        self._mic_device_sel  = tk.StringVar()
        self._fmt_var         = tk.StringVar(value="wav" if not FFMPEG_OK else "mp3")
        self._bitrate_var     = tk.StringVar(value="192k")
        self._save_path       = tk.StringVar(value=str(Path.home() / "Music"))
        self._sys_level       = 0.0
        self._mic_level       = 0.0
        self._blink_state     = False
        self._blink_after     = None
        self._loopback_devices = []
        self._input_devices    = []
        self._sys_device_map   = {}
        self._mic_device_map   = {}

        self._build_ui()
        self._check_deps()
        self._level_poll()

        # Mostrar aviso ffmpeg al inicio si no está instalado
        if not FFMPEG_OK:
            self.after(800, self._refresh_ffmpeg_status)

        # ── Checks ───────────────────────────────────────────────────────────────
    def _check_deps(self):
        missing = []
        if not PYAUDIO_OK: missing.append("pyaudio")
        if not NUMPY_OK:   missing.append("numpy")
        if not PYDUB_OK:   missing.append("pydub")
        if missing:
            self._set_status(f"⚠  Paquetes faltantes: {', '.join(missing)}")

    def _refresh_ffmpeg_status(self):
        """Re-verifica ffmpeg y actualiza la UI de acuerdo al resultado."""
        global FFMPEG_OK, FFMPEG_PATH
        ok, path = check_ffmpeg()
        FFMPEG_OK = ok
        FFMPEG_PATH = path
        # Actualizar etiqueta de estado en la sección Audio Spec
        try:
            self._update_ffmpeg_label(self, ok, path)
        except Exception:
            pass

    def _update_ffmpeg_label(self, widget, ok, path):
        """Recorre widgets buscando la etiqueta de ffmpeg para actualizarla."""
        try:
            for child in widget.winfo_children():
                # Look for label containing "ffmpeg" (the key label)
                if isinstance(child, tk.Label):
                    txt = child.cget("text")
                    if isinstance(txt, str) and "ffmpeg" in txt.lower():
                        # Found the key label, now update its sibling value label
                        parent = child.master
                        if parent:
                            # Get all labels in the parent frame
                            labels = [w for w in parent.winfo_children() if isinstance(w, tk.Label)]
                            if len(labels) >= 2:
                                # Update the value label (second label in the row)
                                value_label = labels[1]
                                value_label.config(
                                    text="✅ OK" if ok else "❌ No instalado",
                                    fg=C["green"] if ok else C["orange"]
                                )
                # Recursively check all children
                self._update_ffmpeg_label(child, ok, path)
        except Exception:
            pass

    def _format_device_label(self, idx, name):
        label = name.strip()
        if len(label) > 40:
            label = label[:37] + "..."
        return f"{label} [{idx}]"

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=C["surface"], height=72)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⬤", fg=C["red"], bg=C["surface"],
                 font=("Segoe UI", 22)).pack(side="left", padx=(20,8), pady=16)
        ttl = tk.Frame(hdr, bg=C["surface"])
        ttl.pack(side="left")
        tk.Label(ttl, text=APP_NAME, fg=C["white"], bg=C["surface"],
                 font=("Segoe UI", 17, "bold")).pack(anchor="w")
        tk.Label(ttl, text=APP_VERSION, fg=C["muted"], bg=C["surface"],
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(hdr, textvariable=self._timer_var, fg=C["accent"],
                 bg=C["surface"], font=("Consolas", 28, "bold")).pack(side="right", padx=24)

        # Banner ffmpeg (visible solo si no está instalado)
        if not FFMPEG_OK:
            banner = tk.Frame(self, bg=C["orange"])
            banner.pack(fill="x")
            banner_inner = tk.Frame(banner, bg=C["orange"])
            banner_inner.pack(fill="x", padx=12, pady=6)
            tk.Label(banner_inner,
                     text="⚠  ffmpeg no encontrado — MP3 deshabilitado. WAV disponible.",
                     fg=C["bg"], bg=C["orange"],
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Button(banner_inner, text="¿Cómo instalar ffmpeg?",
                      command=lambda: FFmpegWarningDialog(self),
                      bg="#CC6600", fg=C["white"],
                      font=("Segoe UI", 8, "bold"),
                      relief="flat", cursor="hand2", padx=8, pady=2).pack(side="right")

        # Status bar
        tk.Label(self, textvariable=self._status_var, fg=C["muted"],
                 bg=C["surface"], font=("Consolas", 9), anchor="w",
                 padx=12).pack(fill="x")

        # Body
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=10)

        left = tk.Frame(body, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(body, bg=C["bg"], width=320)
        right.pack(side="right", fill="y", expand=True, padx=(12,0))
        right.pack_propagate(False)

        # Waveform
        wf = self._card(left, "Live Waveform")
        self._waveform = Waveform(wf)
        self._waveform.pack(fill="x", padx=8, pady=(0,8))
        self._waveform.start()

        # VU Meters
        vu = self._card(left, "Level Meters")
        tk.Label(vu, text="System Audio  (Loopback — Browser, Meet, Zoom, Spotify…)",
                 fg=C["muted"], bg=C["panel"], font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        self._vu_sys = VUMeter(vu, label="SYS")
        self._vu_sys.pack(fill="x", padx=8, pady=(2,8))
        tk.Label(vu, text="Microphone Input",
                 fg=C["muted"], bg=C["panel"], font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        self._vu_mic = VUMeter(vu, label="MIC")
        self._vu_mic.pack(fill="x", padx=8, pady=(2,8))

        # Sources
        src = self._card(left, "Capture Sources")
        r = tk.Frame(src, bg=C["panel"])
        r.pack(fill="x", padx=8, pady=6)
        self._cb_sys = tk.Checkbutton(r, text="🖥  System Audio  (WASAPI Loopback)",
            variable=self._sys_audio, fg=C["text"], bg=C["panel"],
            selectcolor=C["border"], activebackground=C["panel"], font=("Segoe UI", 9))
        self._cb_sys.pack(anchor="w")
        self._cb_mic = tk.Checkbutton(r, text="🎤  Microphone  (Default input device)",
            variable=self._mic_audio, fg=C["text"], bg=C["panel"],
            selectcolor=C["border"], activebackground=C["panel"], font=("Segoe UI", 9))
        self._cb_mic.pack(anchor="w", pady=(4,0))

        # Device selection with refresh button
        self._sys_device_map = {}
        self._mic_device_map = {}
        self._sys_device_sel = tk.StringVar()
        self._mic_device_sel = tk.StringVar()

        tk.Label(r, text="Dispositivo System Audio:", fg=C["muted"], bg=C["panel"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(8,0))
        self._sys_combo = ttk.Combobox(r, textvariable=self._sys_device_sel,
                         values=["Cargando..."], state="readonly")
        self._sys_combo.pack(fill="x", padx=4, pady=(2,4))
        tk.Label(r, text="Dispositivo Mic:", fg=C["muted"], bg=C["panel"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4,0))
        self._mic_combo = ttk.Combobox(r, textvariable=self._mic_device_sel,
                         values=["Cargando..."], state="readonly")
        self._mic_combo.pack(fill="x", padx=4, pady=(2,4))

        tk.Button(r, text="🔄  Escanear dispositivos", command=self._rescan_devices,
                  bg=C["border"], fg=C["text"], relief="flat",
                  font=("Segoe UI", 8), cursor="hand2", pady=2).pack(pady=(8,0))

# Gain controls for mixing
        tk.Label(r, text="Ecualización de Mezcla:", fg=C["muted"], bg=C["panel"],
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(12,0))
        self._gain_sys = tk.DoubleVar(value=0.7)
        self._gain_mic = tk.DoubleVar(value=0.5)
        tk.Label(r, text="🔊 Sistema 70%", fg=C["text"], bg=C["panel"],
                 font=("Consolas", 8)).pack(anchor="w", padx=8, pady=(4,0))
        self._scale_sys = tk.Scale(r, from_=0.0, to=1.0, resolution=0.05, orient="horizontal",
                  variable=self._gain_sys, bg=C["panel"],
                  fg=C["text"], troughcolor=C["border"], length=180,
                  showvalue=0).pack(anchor="w", padx=8)
        tk.Label(r, text="🎤 Micrófono 50%", fg=C["text"], bg=C["panel"],
                 font=("Consolas", 8)).pack(anchor="w", padx=8, pady=(4,0))
        self._scale_mic = tk.Scale(r, from_=0.0, to=1.0, resolution=0.05, orient="horizontal",
                  variable=self._gain_mic, bg=C["panel"],
                  fg=C["text"], troughcolor=C["border"], length=180,
                  showvalue=0).pack(anchor="w", padx=8)
        
        # Configurar trazas para actualización dinámica de ganancias durante grabación
        self._gain_sys.trace_add("write", self._on_gain_change)
        self._gain_mic.trace_add("write", self._on_gain_change)

        # Controls (right)
        ctrl = self._card(right, "Recording")
        self._btn_start = tk.Button(ctrl, text="⏺  START", command=self._start_recording,
            bg=C["red"], fg=C["white"], activebackground="#CC2040", activeforeground=C["white"],
            font=("Segoe UI", 13, "bold"), relief="flat", cursor="hand2", pady=12)
        self._btn_start.pack(fill="x", padx=8, pady=(4,6))
        self._btn_stop = tk.Button(ctrl, text="⏹  STOP", command=self._stop_recording,
            bg=C["border"], fg=C["muted"], activebackground=C["border"], activeforeground=C["text"],
            font=("Segoe UI", 13, "bold"), relief="flat", cursor="hand2", pady=12, state="disabled")
        self._btn_stop.pack(fill="x", padx=8, pady=(0,8))
        self._rec_dot = tk.Label(ctrl, text="●  NOT RECORDING", fg=C["muted"],
            bg=C["panel"], font=("Consolas", 9))
        self._rec_dot.pack(pady=(0,8))

        # Save
        sv = self._card(right, "Save Options")
        tk.Label(sv, text="Format", fg=C["muted"], bg=C["panel"],
                 font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=(4,0))
        fr = tk.Frame(sv, bg=C["panel"])
        fr.pack(fill="x", padx=8, pady=2)

        # Radio MP3 — deshabilitado si no hay ffmpeg
        mp3_state = "normal" if FFMPEG_OK else "disabled"
        mp3_fg = C["text"] if FFMPEG_OK else C["muted"]
        mp3_label = "MP3" if FFMPEG_OK else "MP3 ⚠"
        tk.Radiobutton(fr, text=mp3_label, variable=self._fmt_var, value="mp3",
            fg=mp3_fg, bg=C["panel"], selectcolor=C["border"],
            activebackground=C["panel"], font=("Segoe UI", 10, "bold"),
            state=mp3_state, command=self._on_format_change).pack(side="left", padx=6)
        tk.Radiobutton(fr, text="WAV", variable=self._fmt_var, value="wav",
            fg=C["text"], bg=C["panel"], selectcolor=C["border"],
            activebackground=C["panel"], font=("Segoe UI", 10, "bold"),
            command=self._on_format_change).pack(side="left", padx=6)

        # Bitrate (solo visible para MP3)
        self._bitrate_label = tk.Label(sv, text="MP3 Bitrate", fg=C["muted"], bg=C["panel"],
                 font=("Segoe UI", 8))
        self._bitrate_label.pack(anchor="w", padx=8, pady=(6,0))
        self._bitrate_cb = ttk.Combobox(sv, textvariable=self._bitrate_var,
                     values=["128k","192k","256k","320k"],
                     width=10, state="readonly")
        self._bitrate_cb.pack(anchor="w", padx=8, pady=2)

        tk.Label(sv, text="Output folder", fg=C["muted"], bg=C["panel"],
                 font=("Segoe UI", 8)).pack(anchor="w", padx=8, pady=(6,0))
        pr = tk.Frame(sv, bg=C["panel"])
        pr.pack(fill="x", padx=8, pady=2)
        tk.Entry(pr, textvariable=self._save_path, bg=C["border"], fg=C["text"],
                 insertbackground=C["accent"], relief="flat",
                 font=("Segoe UI", 8)).pack(side="left", fill="x", expand=True)
        tk.Button(pr, text="…", command=self._browse,
                  bg=C["accent2"], fg=C["white"], relief="flat",
                  font=("Segoe UI", 9), cursor="hand2", padx=4).pack(side="left", padx=(4,0))

        self._btn_save = tk.Button(sv, text="💾  SAVE RECORDING", command=self._save,
            bg=C["accent"], fg=C["bg"], activebackground="#00AACC", activeforeground=C["bg"],
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2", pady=8, state="disabled")
        self._btn_save.pack(fill="x", padx=8, pady=(10,8))

        # Info — dispositivos detectados
        inf = self._card(right, "Audio Spec")
        ffmpeg_status = "✅ OK" if FFMPEG_OK else "❌ No instalado"
        self._sys_dev_var = tk.StringVar(value="Cargando...")
        self._mic_dev_var = tk.StringVar(value="Cargando...")

        static_rows = [
            ("Sample Rate", "44100 Hz",       C["text"]),
            ("Channels",    "Stereo (2ch)",    C["text"]),
            ("Bit Depth",   "16-bit PCM",      C["text"]),
            ("Engine",      "WASAPI Loopback", C["text"]),
            ("ffmpeg",      ffmpeg_status,     C["green"] if FFMPEG_OK else C["orange"]),
        ]
        for k, v, color in static_rows:
            row = tk.Frame(inf, bg=C["panel"])
            row.pack(fill="x", padx=8, pady=1)
            tk.Label(row, text=k, fg=C["muted"], bg=C["panel"],
                     font=("Segoe UI", 8), width=13, anchor="w").pack(side="left")
            tk.Label(row, text=v, fg=color, bg=C["panel"],
                     font=("Consolas", 7), wraplength=120, anchor="w").pack(side="left")
        tk.Frame(inf, bg=C["border"], height=1).pack(fill="x", padx=8, pady=4)
        for label, var in [("🖥 Sistema", self._sys_dev_var), ("🎤 Mic", self._mic_dev_var)]:
            row = tk.Frame(inf, bg=C["panel"])
            row.pack(fill="x", padx=8, pady=1)
            tk.Label(row, text=label, fg=C["muted"], bg=C["panel"],
                     font=("Segoe UI", 8), width=10, anchor="w").pack(side="left")
            tk.Label(row, textvariable=var, fg=C["accent"], bg=C["panel"],
                     font=("Consolas", 7), wraplength=130, anchor="w").pack(side="left")
        tk.Label(inf, text="", bg=C["panel"]).pack()

        # Botón info ffmpeg
        if not FFMPEG_OK:
            tk.Button(inf, text="ℹ  Instalar ffmpeg (MP3)",
                      command=lambda: FFmpegWarningDialog(self),
                      bg=C["orange"], fg=C["bg"],
                      font=("Segoe UI", 8, "bold"),
                      relief="flat", cursor="hand2", pady=4).pack(fill="x", padx=8, pady=(0,8))

        # Botón de diagnóstico
        tk.Button(inf, text="🔍  Ver diagnóstico de audio",
                  command=self._show_audio_diagnostic,
                  bg=C["border"], fg=C["text"],
                  font=("Segoe UI", 8, "bold"),
                  relief="flat", cursor="hand2", pady=4).pack(fill="x", padx=8, pady=(0,8))

        # Cargar dispositivos al inicio
        self.after(100, self._rescan_devices)

        self._on_format_change()

    def _rescan_devices(self):
        """Reescanea dispositivos de audio y actualiza la UI."""
        _, lb_devs, in_devs = scan_audio_devices()
        self._loopback_devices = lb_devs
        self._input_devices = in_devs
        self._sys_device_map = {
            self._format_device_label(idx, name): idx
            for idx, name, _ in lb_devs
        }
        self._mic_device_map = {
            self._format_device_label(idx, name): idx
            for idx, name, _ in in_devs
        }

        sys_opts = list(self._sys_device_map.keys()) or ["No WASAPI loopback disponible"]
        mic_opts = list(self._mic_device_map.keys()) or ["No WASAPI input disponible"]
        self._sys_combo.config(values=sys_opts)
        self._mic_combo.config(values=mic_opts)

        # Auto-seleccionar el driver de Windows por defecto usando pyaudiowpatch
        default_sys_label = None
        default_mic_label = None
        if PYAUDIOWPATCH_OK:
            try:
                import pyaudiowpatch as _pwp
                _pa = _pwp.PyAudio()
                # Obtener el dispositivo de salida por defecto (no el loopback)
                try:
                    output_dev = _pa.get_default_wasapi_device(d_out=True)
                    default_sys_idx = output_dev['index']
                    # Buscar en el map el label correspondiente
                    for label, idx in self._sys_device_map.items():
                        if idx == default_sys_idx:
                            default_sys_label = label
                            break
                except Exception:
                    pass
                # Obtener input default de Windows
                try:
                    md = _pa.get_default_wasapi_device(d_in=True)
                    default_mic_idx = md['index']
                    for label, idx in self._mic_device_map.items():
                        if idx == default_mic_idx:
                            default_mic_label = label
                            break
                except Exception:
                    pass
                _pa.terminate()
            except Exception:
                pass

        # Fallback: usar el primer dispositivo si no se encontró el default
        if default_sys_label is None and self._sys_device_map:
            default_sys_label = next(iter(self._sys_device_map))
        if default_mic_label is None and self._mic_device_map:
            default_mic_label = next(iter(self._mic_device_map))

        if default_sys_label:
            self._sys_device_sel.set(default_sys_label)
            self._sys_dev_var.set(self._format_device_label(
                self._sys_device_map[default_sys_label],
                self._get_device_name(self._sys_device_map[default_sys_label], lb_devs)
            ))
        else:
            self._sys_device_sel.set(sys_opts[0])
            self._sys_dev_var.set("No detectado")

        if default_mic_label:
            self._mic_device_sel.set(default_mic_label)
            self._mic_dev_var.set(self._format_device_label(
                self._mic_device_map[default_mic_label],
                self._get_device_name(self._mic_device_map[default_mic_label], in_devs)
            ))
        else:
            self._mic_device_sel.set(mic_opts[0])
            self._mic_dev_var.set("No detectado")

        status = f"🔍 Dispositivos escaneados — Sistema: {len(lb_devs)}, Micrófono: {len(in_devs)}"
        self._set_status(status)
        self._update_device_status()

    def _get_device_name(self, idx, devices):
        for dev_idx, name, _ in devices:
            if dev_idx == idx:
                return name
        return "Desconocido"

    def _update_device_status(self):
        """Actualiza el estado visual de los dispositivos."""
        sys_count = len(self._loopback_devices)
        mic_count = len(self._input_devices)
        self._set_status(f"🔍 Sistema: {sys_count} dispositivos · Micrófono: {mic_count} dispositivos")

    def _on_format_change(self):
        """Llamado cuando cambia el formato de archivo."""
        fmt = self._fmt_var.get()
        # Mostrar/ocultar bitrate según formato
        if fmt == "mp3":
            self._bitrate_label.pack(anchor="w", padx=8, pady=(6,0))
            self._bitrate_cb.pack(anchor="w", padx=8, pady=2)
        else:
            self._bitrate_label.pack_forget()
            self._bitrate_cb.pack_forget()
        if fmt == "mp3" and not FFMPEG_OK:
            FFmpegWarningDialog(self)

    def _show_audio_diagnostic(self):
        """Muestra diagnóstico detallado de dispositivos de audio."""
        from tkinter import messagebox as mb
        
        # Ejecutar diagnóstico
        _, lb_devs, in_devs = scan_audio_devices()
        
        diag_text = "=== DIAGNÓSTICO DE AUDIO ===\n\n"
        diag_text += "--- Dispositivos Loopback (Sistema) ---\n"
        if lb_devs:
            for idx, name, ch in lb_devs:
                diag_text += f"[{idx}] {name} - {ch} canales\n"
        else:
            diag_text += "Ningún dispositivo loopback encontrado\n"
        
        diag_text += "\n--- Dispositivos de Entrada (Micrófono) ---\n"
        if in_devs:
            for idx, name, ch in in_devs:
                diag_text += f"[{idx}] {name} - {ch} canales\n"
        else:
            diag_text += "Ningún dispositivo de entrada encontrado\n"
        
        diag_text += "\n--- Configuración ---\n"
        diag_text += f"Sample Rate: {SAMPLE_RATE} Hz\n"
        diag_text += f"Channels: {CHANNELS}\n"
        diag_text += f"Chunk: {CHUNK}\n"
        
        mb.showinfo("Diagnóstico de Audio", diag_text)


    def _card(self, parent, title):
        outer = tk.Frame(parent, bg=C["bg"])
        outer.pack(fill="x", pady=(0,10))
        tk.Label(outer, text=title.upper(), fg=C["accent"],
                 bg=C["bg"], font=("Segoe UI", 7, "bold")).pack(anchor="w", pady=(0,3))
        inner = tk.Frame(outer, bg=C["panel"],
                         highlightbackground=C["border"], highlightthickness=1)
        inner.pack(fill="x")
        return inner

    def _level_poll(self):
        if self._recording:
            self._vu_sys.set_level(self._sys_level)
            self._vu_mic.set_level(self._mic_level)
            self._waveform.push(max(self._sys_level, self._mic_level))
        else:
            self._vu_sys.set_level(0)
            self._vu_mic.set_level(0)
            self._waveform.push(0)
        self.after(50, self._level_poll)

    def _on_level(self, sl, ml):
        self._sys_level = sl
        self._mic_level = ml

    def _on_gain_change(self, *args):
        """Callback cuando los sliders de ganancia cambian durante la grabación."""
        if self._engine is not None:
            self._engine.update_gains(
                sys_gain=self._gain_sys.get(),
                mic_gain=self._gain_mic.get(),
            )

    def _on_status(self, s):
        mapping = {"recording": "🔴  Grabando… WASAPI loopback activo",
                   "stopped":   "⏹  Grabación detenida — lista para guardar"}
        self._set_status(mapping.get(s, f"⚠  {s}"))

    def _set_status(self, msg):
        self._status_var.set(msg)

    def _start_recording(self):
        if self._recording: return
        if not self._sys_audio.get() and not self._mic_audio.get():
            messagebox.showwarning(APP_NAME, "Seleccioná al menos una fuente de captura.")
            return
        self._sys_level = 0.0
        self._mic_level = 0.0
        self._waveform._samples = [0.0]*200
        self._engine = AudioEngine(
            on_level_cb=self._on_level,
            on_status_cb=lambda s: self.after(0, self._on_status, s),
            sys_gain=self._gain_sys.get(),
            mic_gain=self._gain_mic.get(),
        )
        sys_device = None
        mic_device = None
        if self._sys_audio.get() and self._sys_device_sel.get() in self._sys_device_map:
            sys_device = self._sys_device_map[self._sys_device_sel.get()]
        if self._mic_audio.get() and self._mic_device_sel.get() in self._mic_device_map:
            mic_device = self._mic_device_map[self._mic_device_sel.get()]
        if not self._engine.start(capture_system=self._sys_audio.get(),
                                   capture_mic=self._mic_audio.get(),
                                   sys_device=sys_device,
                                   mic_device=mic_device):
            return
        self._recording = True
        self._timer.start()
        self._btn_start.config(state="disabled", bg=C["border"], fg=C["muted"])
        self._btn_stop.config(state="normal", bg=C["red"], fg=C["white"])
        self._btn_save.config(state="disabled")
        self._cb_sys.config(state="disabled")
        self._cb_mic.config(state="disabled")
        self._blink()

    def _stop_recording(self):
        if not self._recording: return
        self._recording = False
        self._sys_level = 0.0
        self._mic_level = 0.0
        self._timer.stop()
        if self._engine: self._engine.stop()
        self._btn_start.config(state="normal", bg=C["red"], fg=C["white"])
        self._btn_stop.config(state="disabled", bg=C["border"], fg=C["muted"])
        self._btn_save.config(state="normal")
        self._cb_sys.config(state="normal")
        self._cb_mic.config(state="normal")
        self._rec_dot.config(text="●  NOT RECORDING", fg=C["muted"])
        if self._blink_after:
            self.after_cancel(self._blink_after)

    def _blink(self):
        if not self._recording: return
        self._blink_state = not self._blink_state
        self._rec_dot.config(
            text="🔴  GRABANDO" if self._blink_state else "⬤  GRABANDO",
            fg=C["red"] if self._blink_state else "#7A0000")
        self._blink_after = self.after(600, self._blink)

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self._save_path.get())
        if d: self._save_path.set(d)

    def _save(self):
        if not self._engine:
            messagebox.showinfo(APP_NAME, "Nada para guardar todavía.")
            return

        fmt = self._fmt_var.get()

        # Verificar ffmpeg antes de intentar MP3
        if fmt == "mp3" and not FFMPEG_OK:
            FFmpegWarningDialog(self)
            return

        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder = Path(self._save_path.get())
        folder.mkdir(parents=True, exist_ok=True)
        out = folder / f"nel_capture_{ts}.{fmt}"
        self._set_status("💾  Guardando…")
        self.update()

        if fmt == "wav":
            ok = self._engine.save_wav(out)
            if ok:
                self._set_status(f"✅  Guardado → {out.name}")
                messagebox.showinfo("¡Guardado!", f"Archivo guardado en:\n{out}")
            else:
                self._set_status("❌  Sin datos de audio")
                messagebox.showerror("Error", "No hay datos de audio capturados.")
        else:
            ok, err = self._engine.save_mp3(out, self._bitrate_var.get())
            if ok:
                self._set_status(f"✅  Guardado → {out.name}")
                messagebox.showinfo("¡Guardado!", f"Archivo guardado en:\n{out}")
            elif err == "ffmpeg_missing":
                FFmpegWarningDialog(self)
            else:
                self._set_status(f"❌  Error MP3: {err}")
                messagebox.showerror("Error", f"Error al guardar MP3:\n{err}")

    def run(self):
        self.mainloop()


if __name__ == "__main__":
    app = NelAudioCaptureApp()
    app.run()