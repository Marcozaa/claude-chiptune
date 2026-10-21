"""Shared test helpers."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SEP = "\x1f"  # chiptune.spotify.FIELD_SEP
RAW_TRACK = SEP.join([
    "playing", "Cold", "Maroon 5", "Red Pill Blues", "113624", "222308",
    "https://i.scdn.co/image/abc123", "spotify:track:4s6LhHAV5SEsOV0lC2tjvJ",
])


def raw_track(**overrides: str) -> str:
    keys = ["state", "title", "artist", "album", "pos", "dur", "url", "id"]
    fields = dict(zip(keys, RAW_TRACK.split(SEP)))
    fields.update(overrides)
    return SEP.join(fields[k] for k in keys)


def write_bmp(path: str, pixels: list, top_down: bool = True) -> None:
    """Write a 24-bit uncompressed BMP from rows of (r, g, b)."""
    height, width = len(pixels), len(pixels[0])
    row_size = (width * 3 + 3) & ~3
    rows = pixels if top_down else list(reversed(pixels))
    body = b"".join(
        b"".join(bytes((b, g, r)) for r, g, b in row).ljust(row_size, b"\0")
        for row in rows
    )
    header = struct.pack("<2sIHHI", b"BM", 54 + len(body), 0, 0, 54)
    dib = struct.pack(
        "<IiiHHIIiiII", 40, width, -height if top_down else height,
        1, 24, 0, len(body), 0, 0, 0, 0,
    )
    with open(path, "wb") as f:
        f.write(header + dib + body)
