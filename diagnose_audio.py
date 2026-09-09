import pyaudio
import sys

pa = pyaudio.PyAudio()

print("=" * 80)
print("PyAudio Device Diagnostics")
print("=" * 80)

print(f"\nTotal Host APIs: {pa.get_host_api_count()}")
for i in range(pa.get_host_api_count()):
    info = pa.get_host_api_info_by_index(i)
    print(f"\nHost API {i}:")
    print(f"  Name: {info['name']}")
    print(f"  Default Input Device: {info.get('defaultInputDevice')}")
    print(f"  Default Output Device: {info.get('defaultOutputDevice')}")
    print(f"  Device Count: {info.get('deviceCount')}")

print(f"\n\nTotal Devices: {pa.get_device_count()}")
print("-" * 80)
for i in range(pa.get_device_count()):
    dev = pa.get_device_info_by_index(i)
    print(f"\nDevice {i}: {dev['name']}")
    print(f"  Host API: {dev['hostApi']}")
    print(f"  Input Channels: {dev['maxInputChannels']}")
    print(f"  Output Channels: {dev['maxOutputChannels']}")
    print(f"  Sample Rate: {dev['defaultSampleRate']}")

pa.terminate()

print("\n" + "=" * 80)
print("WASAPI Loopback Check:")
print("=" * 80)
print("\nLooking for devices with:")
print("  - maxOutputChannels > 0 (can be used as loopback)")
print("  - maxInputChannels > 0 (can be opened as input)")
pa = pyaudio.PyAudio()
wasapi_host = None
for i in range(pa.get_host_api_count()):
    info = pa.get_host_api_info_by_index(i)
    if "WASAPI" in info.get("name", ""):
        wasapi_host = i
        break

if wasapi_host is not None:
    print(f"\nWASAPI Host found at index {wasapi_host}")
    loopback = []
    for i in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(i)
        if (dev.get("hostApi") == wasapi_host and 
            dev.get("maxOutputChannels", 0) > 0):
            loopback.append((i, dev.get("name", "Unknown")))
    
    if loopback:
        print(f"\nFound {len(loopback)} potential loopback device(s):")
        for idx, name in loopback:
            print(f"  [{idx}] {name}")
    else:
        print("\nNo WASAPI loopback devices found!")
else:
    print("\nWASAPI Host not found!")

pa.terminate()
