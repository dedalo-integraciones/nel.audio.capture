import pyaudio
pa = pyaudio.PyAudio()
print("PyAudio version:", pyaudio.__version__)
print("Host APIs:")
for i in range(pa.get_host_api_count()):
    info = pa.get_host_api_info_by_index(i)
    print(f"  {i}: {info['name']}")
pa.terminate()
