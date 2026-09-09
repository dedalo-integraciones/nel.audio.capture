import pyaudiowpatch as pyaudio_wp
import pyaudio

# Create PyAudio instance from pyaudiowpatch
pa = pyaudio_wp.PyAudio()

print("Trying WASAPI loopback with pyaudiowpatch...")

# Get WASAPI host API
wasapi_host = None
for i in range(pa.get_host_api_count()):
    info = pa.get_host_api_info_by_index(i)
    if "WASAPI" in info.get("name", ""):
        wasapi_host = i
        break

print(f"WASAPI host API index: {wasapi_host}")

if wasapi_host is not None:
    # List loopback devices
    loopback_devs = []
    for i in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(i)
        if dev.get("hostApi") == wasapi_host and dev.get("maxOutputChannels", 0) > 0:
            loopback_devs.append((i, dev.get("name", "Unknown"), dev.get("maxOutputChannels", 0)))
    
    print(f"\nFound {len(loopback_devs)} loopback devices:")
    for idx, name, ch in loopback_devs:
        print(f"  [{idx}] {name} - {ch} output channels")
    
    # Try to open first loopback device
    if loopback_devs:
        dev_idx = loopback_devs[0][0]
        print(f"\nTrying to open device {dev_idx} ({loopback_devs[0][1]})")
        
        try:
            # Try with as_loopback=True (pyaudiowpatch style)
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=2,
                rate=44100,
                input=True,
                input_device_index=dev_idx,
                as_loopback=True,
                frames_per_buffer=1024,
            )
            print("SUCCESS: Stream opened with as_loopback=True")
            
            # Read some data
            data = stream.read(1024, exception_on_overflow=False)
            print(f"Read {len(data)} bytes of audio data")
            
            # Try reading more to see if it's actually capturing
            import time
            time.sleep(0.5)
            data2 = stream.read(1024, exception_on_overflow=False)
            print(f"Read {len(data2)} bytes more after 0.5s")
            
            stream.stop_stream()
            stream.close()
            print("Stream closed successfully")
            
        except Exception as e:
            print(f"Failed to open stream: {e}")
            import traceback
            traceback.print_exc()

pa.terminate()