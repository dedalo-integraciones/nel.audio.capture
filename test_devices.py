import pyaudio
import time

pa = pyaudio.PyAudio()

# Check device 9 (DirectSound)
print('Device 9 info:')
info = pa.get_device_info_by_index(9)
print(f"  Name: {info['name']}")
print(f"  Max input channels: {info['maxInputChannels']}")
print(f"  Max output channels: {info['maxOutputChannels']}")
print(f"  Default sample rate: {info['defaultSampleRate']}")

print('\nDevice 13 info (WASAPI):')
info = pa.get_device_info_by_index(13)
print(f"  Name: {info['name']}")
print(f"  Max input channels: {info['maxInputChannels']}")
print(f"  Max output channels: {info['maxOutputChannels']}")
print(f"  Default sample rate: {info['defaultSampleRate']}")

print('\nDevice 4 info (MME):')
info = pa.get_device_info_by_index(4)
print(f"  Name: {info['name']}")
print(f"  Max input channels: {info['maxInputChannels']}")
print(f"  Max output channels: {info['maxOutputChannels']}")
print(f"  Default sample rate: {info['defaultSampleRate']}")

# Try to open with the correct parameters
print('\nTesting WASAPI device 13 with as_loopback=True...')
try:
    # Need to get info first
    info = pa.get_device_info_by_index(13)
    print(f"  Output channels: {info['maxOutputChannels']}")
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=min(2, info['maxOutputChannels']),
        rate=int(info['defaultSampleRate']),
        input=True,
        input_device_index=13,
        as_loopback=True,
        frames_per_buffer=1024,
    )
    print('SUCCESS')
    stream.stop_stream()
    stream.close()
except Exception as e:
    print(f'Failed: {e}')
    # Try with 1 channel
    try:
        info = pa.get_device_info_by_index(13)
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=min(1, info['maxOutputChannels']),
            rate=int(info['defaultSampleRate']),
            input=True,
            input_device_index=13,
            as_loopback=True,
            frames_per_buffer=1024,
        )
        print('SUCCESS with 1 channel')
        stream.stop_stream()
        stream.close()
    except Exception as e2:
        print(f'Failed with 1 channel too: {e2}')

pa.terminate()
