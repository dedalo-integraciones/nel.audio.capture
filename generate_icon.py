from PIL import Image
import os

os.makedirs('assets', exist_ok=True)

img = Image.open('assets/icon.png').convert('RGBA')
img.save(
    'assets/icon.ico',
    format='ICO',
    sizes=[
        (16, 16),
        (32, 32),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256),
    ],
)

print('Created assets/icon.ico with 16, 32, 48, 64, 128 and 256 px entries')
