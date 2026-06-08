"""生成番茄时钟应用图标 (icns)，无需 PIL"""
import struct
import zlib
import os
import subprocess as sp


def _create_png_raw(width, height):
    """Create a simple tomato icon PNG as bytes."""
    pixels = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            # Normalized coords, centered
            nx = (x + 0.5) / width * 2 - 1
            ny = (y + 0.5) / height * 2 - 1

            # Tomato body (ellipse)
            dx, dy = nx * 0.72, ny * 0.88
            in_body = dx * dx + dy * dy < 1.0

            # Stem leaves (green top)
            lx, ly = nx * 0.5, (ny + 0.58) * 3.0
            in_leaf = lx * lx + ly * ly < 1.0 and ny < -0.15

            # Highlight (top-left shine)
            hx, hy = (nx - 0.25) * 1.6, (ny - 0.18) * 1.6
            in_highlight = hx * hx + hy * hy < 0.45 and in_body

            if in_leaf:
                r, g, b, a = 60, 190, 70, 255
            elif in_highlight:
                r, g, b, a = 255, 180, 180, 255
            elif in_body:
                r, g, b, a = 230, 55, 55, 255
            else:
                r, g, b, a = 0, 0, 0, 0

            row.extend([r, g, b, a])
        pixels.append(b'\x00' + bytes(row))

    raw = b''.join(pixels)

    def chunk(c_type, data):
        c = c_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', ihdr)
        + chunk(b'IDAT', zlib.compress(raw))
        + chunk(b'IEND', b'')
    )


iconset = '/Volumes/Jokker/Code/番茄时钟/tomato.iconset'
os.makedirs(iconset, exist_ok=True)

sizes = [16, 32, 64, 128, 256, 512]
for s in sizes:
    data = _create_png_raw(s, s)
    path = os.path.join(iconset, f'icon_{s}x{s}.png')
    with open(path, 'wb') as f:
        f.write(data)
    # @2x variant (resize needed — skip for simplicity, macOS can scale)
    if s * 2 <= 512:
        path2 = os.path.join(iconset, f'icon_{s}x{s}@2x.png')
        # macOS can fall back to normal size; just copy for small sizes
        if s <= 128:
            with open(path2, 'wb') as f:
                f.write(_create_png_raw(s * 2, s * 2))

# Convert to .icns using iconutil
icns_path = '/Volumes/Jokker/Code/番茄时钟/icon.icns'
sp.run(['iconutil', '-c', 'icns', iconset, '-o', icns_path], check=True)
print(f'✅ 图标已生成: {icns_path}')
