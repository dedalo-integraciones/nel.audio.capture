import sys
print('Trying pyaudiowpatch...')
try:
    import pyaudiowpatch as pa
    print('SUCCESS: pyaudiowpatch imported')
    print('Version:', getattr(pa, '__version__', 'unknown'))
    p = pa.PyAudio()
    print('Host APIs:')
    for i in range(p.get_host_api_count()):
        info = p.get_host_api_info_by_index(i)
        print(f'  {i}: {info["name"]}')
    p.terminate()
except Exception as e:
    print(f'FAILED: {e}')
    import traceback
    traceback.print_exc()
