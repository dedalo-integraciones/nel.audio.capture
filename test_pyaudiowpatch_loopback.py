import pyaudiowpatch as pa
import time

paudio = pa.PyAudio()

# Get WASAPI host API info
wasapi_info = paudio.get_host_api_info_by_type(pa.paWASAPI)
print("WASAPI Host API info:")
print(f"  defaultOutputDevice: {wasapi_info.get('defaultOutputDevice')}")
print(f"  defaultInputDevice: {wasapi_info.get('defaultInputDevice')}")
print(f"  deviceCount: {wasapi_info.get('deviceCount')}")

# Get default output device
default_out = paudio.get_device_info_by_index(wasapi_info['defaultOutputDevice'])
print(f"\nDefault output device: {default_out['name']}")
print(f"  maxOutputChannels: {default_out['maxOutputChannels']}")
print(f"  maxInputChannels: {default_out['maxInputChannels']}")
print(f"  isLoopbackDevice: {default_out.get('isLoopbackDevice', False)}")

# Get loopback analogue for the default output device
try:
    loopback_info = paudio.get_wasapi_loopback_analogue_by_index(wasapi_info['defaultOutputDevice'])
    print(f"\nLoopback analogue for default output:")
    print(f"  Index: {loopback_info['index']}")
    print(f"  Name: {loopback_info['name']}")
    print(f"  isLoopbackDevice: {loopback_info['isLoopbackDevice']}")
    print(f"  maxOutputChannels: {loopback_info['maxOutputChannels']}")
    print(f"  maxInputChannels: {loopback_info['maxInputChannels']}")
    
    # Try to open the loopback device as an input stream
    print(f"\nTrying to open loopback stream...")
    stream = paudio.open(
        format=pa.paInt16,
        channels=2,
        rate=44100,
        input=True,
        input_device_index=loopback_info['index'],
        frames_per_buffer=1024,
    )
    print(f"SUCCESS: Loopback stream opened!")
    
    # Try reading some data
    data = stream.read(1024, exception_on_overflow=False)
    print(f"  Read {len(data)} bytes after 0.1s")
    
    time.sleep(0.5)
    data2 = stream.read(1024, exception_on_overflow=False)
    print(f"  Read {len(data2)} bytes after 0.5s")
    
    stream.stop_stream()
    stream.close()
    print(f"  Stream closed successfully")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

paudio.terminate()