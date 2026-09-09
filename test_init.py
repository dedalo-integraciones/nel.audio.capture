import tkinter as tk
from nel_audio_capture import NelAudioCaptureApp, scan_audio_devices
import threading
import time

root = tk.Tk()
app = NelAudioCaptureApp()

# Check if _pa_wpatch is initialized
print('Has _pa_wpatch:', hasattr(app._engine, '_pa_wpatch'))
if hasattr(app._engine, '_pa_wpatch'):
    print('_pa_wpatch:', app._engine._pa_wpatch)

# After delay
def check():
    time.sleep(0.5)
    print('After 500ms - sys devices:', len(app._sys_device_map))
    print('Mic devices:', len(app._mic_device_map))
    root.quit()

t = threading.Thread(target=check)
t.daemon = True
t.start()

root.mainloop()