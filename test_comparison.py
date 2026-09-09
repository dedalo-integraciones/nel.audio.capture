import pyaudiowpatch as pa
import pyaudio

print('PyAudio version:', pyaudio.__version__)
print('PyAudioWPatch version:', pa.__version__)

pa_pyaudio = pyaudio.PyAudio()
pa_patch = pa.PyAudio()

print('\nPyAudio Host APIs:')
for i in range(pa_pyaudio.get_host_api_count()):
    info = pa_pyaudio.get_host_api_info_by_index(i)
    print(f'  {i}: {info["name"]}')

print('\nPyAudioWPatch Host APIs:')
for i in range(pa_patch.get_host_api_count()):
    info = pa_patch.get_host_api_info_by_index(i)
    print(f'  {i}: {info["name"]}')

pa_pyaudio.terminate()
pa_patch.terminate()
