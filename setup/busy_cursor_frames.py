"""Drop the leading flat transparent/black/white frames from Xcursor busy animations."""
import struct
import sys

IMAGE_TYPE = 0xFFFD0002
FLAT_PIXELS = {0xFF000000, 0xFFFFFFFF}


def is_flat(pixels):
    return all(pixel >> 24 == 0 or pixel in FLAT_PIXELS for pixel in pixels)


def drop_leading_flat_frames(data):
    count = struct.unpack_from("<I", data, 12)[0]
    chunks = []
    for index in range(count):
        kind, size, offset = struct.unpack_from("<III", data, 16 + 12 * index)
        length = 36 + 4 * struct.unpack_from("<I", data, offset + 16)[0] * struct.unpack_from("<I", data, offset + 20)[0]
        chunks.append((kind, size, data[offset : offset + length]))
    started, kept = set(), []
    for kind, size, chunk in chunks:
        pixels = struct.unpack_from(f"<{(len(chunk) - 36) // 4}I", chunk, 36)
        if kind == IMAGE_TYPE and size not in started and is_flat(pixels):
            continue
        started.add(size)
        kept.append((kind, size, chunk))
    offset = 16 + 12 * len(kept)
    toc = b""
    for kind, size, chunk in kept:
        toc += struct.pack("<III", kind, size, offset)
        offset += len(chunk)
    return struct.pack("<4sIII", b"Xcur", 16, 0x10000, len(kept)) + toc + b"".join(chunk for _, _, chunk in kept)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        with open(path, "rb") as source:
            rewritten = drop_leading_flat_frames(source.read())
        with open(path, "wb") as target:
            target.write(rewritten)
