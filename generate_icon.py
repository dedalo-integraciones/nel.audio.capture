import os
import zlib
import struct

os.makedirs('assets', exist_ok=True)

font = {
    'N': [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
    'A': [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'C': [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
}

w = h = 64
img = [[(0, 0, 0, 255) for _ in range(w)] for __ in range(h)]
for y in range(h):
    t = y / (h - 1)
    r = int(45 + (255 - 45) * t)
    g = int(30 + (215 - 30) * t)
    b = int(12 + (40 - 12) * t)
    for x in range(w):
        img[y][x] = (r, g, b, 255)

letter_w = 5
letter_h = 7
scale = 6
spacing = 4
text = 'NAC'
start_x = (w - (letter_w * scale * len(text) + spacing * (len(text) - 1)) ) // 2
start_y = (h - letter_h * scale) // 2

for idx, ch in enumerate(text):
    glyph = font[ch]
    x0 = start_x + idx * (letter_w * scale + spacing)
    for gy, row in enumerate(glyph):
        for gx in range(letter_w):
            if (row >> (letter_w - 1 - gx)) & 1:
                for sy in range(scale):
                    for sx in range(scale):
                        px = x0 + gx * scale + sx
                        py = start_y + gy * scale + sy
                        if 0 <= px < w and 0 <= py < h:
                            img[py][px] = (240, 190, 50, 255)

# highlight
text_width = letter_w * scale * len(text) + spacing * (len(text) - 1)
x0 = max(0, start_x)
x1 = min(w, start_x + text_width)
y0 = max(0, start_y)
y1 = min(h, start_y + letter_h * scale)
for y in range(y0, y1):
    for x in range(x0, x1):
        r, g, b, a = img[y][x]
        if a and r > 200 and g > 150:
            img[y][x] = (min(255, r + 10), min(255, g + 20), b, 255)

# Create PNG data
png = bytearray(b'\x89PNG\r\n\x1a\n')

ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
png += struct.pack('>I4s', len(ihdr), b'IHDR') + ihdr
png += struct.pack('>I', zlib.crc32(b'IHDR' + ihdr) & 0xFFFFFFFF)

raw = bytearray()
for row in img:
    raw.append(0)
    for pix in row:
        raw.extend(pix)
comp = zlib.compress(bytes(raw), level=9)
png += struct.pack('>I4s', len(comp), b'IDAT') + comp
png += struct.pack('>I', zlib.crc32(b'IDAT' + comp) & 0xFFFFFFFF)
png += struct.pack('>I4s', 0, b'IEND')
png += struct.pack('>I', zlib.crc32(b'IEND') & 0xFFFFFFFF)

with open('assets/icon.png', 'wb') as f:
    f.write(png)

png_data = bytes(png)
icon = bytearray()
icon += struct.pack('<HHH', 0, 1, 1)
icon += struct.pack('<BBBBHHII', w if w < 256 else 0, h if h < 256 else 0, 0, 0, 0, 0, len(png_data), 6 + 16)
icon += png_data
with open('assets/icon.ico', 'wb') as f:
    f.write(icon)

print('Created assets/icon.ico and assets/icon.png')