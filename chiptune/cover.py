"""Album cover -> 8-bit pixel art (xterm 256-colour cube, two pixels per cell)."""
from __future__ import annotations

import colorsys
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from http.client import HTTPException

from .config import CACHE_DIR, ensure_private_dir

log = logging.getLogger(__name__)

ART_PX = 12  # cover is ART_PX x ART_PX pixels -> ART_PX/2 terminal rows
DOWNLOAD_TIMEOUT_S = 3
MAX_COVER_BYTES = 2_000_000
ARTWORK_URL = re.compile(r"https://i\.scdn\.co/image/[A-Za-z0-9]+")
SATURATION_BOOST = 1.3
ACCENT_MIN_SAT = 0.35
ACCENT_MIN_VAL = 0.35
CACHE_VERSION = 3  # bump when the rendering or cache format changes
FAILURE_RETRY_S = 60
COVER_DIR = os.path.join(CACHE_DIR, "covers")
CUBE_STEPS = (0, 95, 135, 175, 215, 255)
RESET = "\033[0m"
# What render_art produces: colour codes and half blocks only (cache is re-validated).
ART_LINE = re.compile(r"(?:\033\[[0-9;]*m|▀)*")

Pixel = tuple[int, int, int]


def is_allowed_artwork(url: str) -> bool:
    return ARTWORK_URL.fullmatch(url) is not None


def read_bmp(path: str) -> list[list[Pixel]]:
    """Read an uncompressed 24/32-bit BMP (what `sips -s format bmp` writes)."""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 54 or data[:2] != b"BM":
        raise ValueError("not a BMP file")
    offset = int.from_bytes(data[10:14], "little")
    width = int.from_bytes(data[18:22], "little", signed=True)
    height = int.from_bytes(data[22:26], "little", signed=True)
    bpp = int.from_bytes(data[28:30], "little")
    compression = int.from_bytes(data[30:34], "little")
    if bpp not in (24, 32) or compression not in (0, 3) or width <= 0:
        raise ValueError(f"unsupported BMP ({bpp} bpp, compression {compression})")
    step = bpp // 8
    row_size = (width * step + 3) & ~3
    rows = []
    for y in range(abs(height)):
        start = offset + y * row_size
        row = data[start:start + width * step]
        if len(row) < width * step:
            raise ValueError("truncated BMP")
        rows.append([(row[x + 2], row[x + 1], row[x]) for x in range(0, len(row), step)])
    return rows if height < 0 else rows[::-1]


def to_cube(rgb: Pixel) -> int:
    """Nearest colour in the xterm 6x6x6 cube (indices 16-231)."""
    r, g, b = (min(range(6), key=lambda i: abs(CUBE_STEPS[i] - c)) for c in rgb)
    return 16 + 36 * r + 6 * g + b


def boost(rgb: Pixel) -> Pixel:
    """Raise saturation a little so pale covers stay punchy after quantizing."""
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    r, g, b = colorsys.hsv_to_rgb(h, min(s * SATURATION_BOOST, 1.0), v)
    return round(r * 255), round(g * 255), round(b * 255)


def accent_color(pixels: list[list[Pixel]]) -> int | None:
    """Cube index of the cover's most vivid pixel, or None if it is greyscale."""
    best, best_score = None, 0.0
    for rgb in (p for row in pixels for p in row):
        _, sat, val = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
        if sat >= ACCENT_MIN_SAT and val >= ACCENT_MIN_VAL and sat * val > best_score:
            best, best_score = rgb, sat * val
    return to_cube(best) if best else None


def render_art(pixels: list[list[Pixel]]) -> list[str]:
    lines = []
    for y in range(0, len(pixels) - 1, 2):
        cells = "".join(
            f"\033[38;5;{to_cube(boost(top))}m\033[48;5;{to_cube(boost(bottom))}m▀"
            for top, bottom in zip(pixels[y], pixels[y + 1])
        )
        lines.append(cells + RESET)
    return lines


def download(url: str, dest: str) -> None:
    with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as resp:
        if not is_allowed_artwork(resp.geturl()):
            raise ValueError("cover download was redirected off the Spotify CDN")
        data = resp.read(MAX_COVER_BYTES + 1)
    if len(data) > MAX_COVER_BYTES:
        raise ValueError("cover image too large")
    with open(dest, "wb") as f:
        f.write(data)


def _render_cover(url: str) -> tuple[list[str], int | None]:
    with tempfile.TemporaryDirectory() as tmp:
        jpg, bmp = os.path.join(tmp, "cover.jpg"), os.path.join(tmp, "cover.bmp")
        download(url, jpg)
        subprocess.run(
            ["sips", "-z", str(ART_PX), str(ART_PX), "-s", "format", "bmp", jpg, "--out", bmp],
            capture_output=True, timeout=DOWNLOAD_TIMEOUT_S, check=True,
        )
        pixels = read_bmp(bmp)
    return render_art(pixels), accent_color(pixels)


def _load(path: str) -> dict | None:
    """A validated cache entry, or None if missing, corrupt or tampered with."""
    try:
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
        lines, accent = entry["lines"], entry["accent"]
        valid = (
            isinstance(lines, list)
            and all(isinstance(line, str) and ART_LINE.fullmatch(line) for line in lines)
            and (accent is None or (isinstance(accent, int) and 16 <= accent <= 231))
            and isinstance(entry["failed"], bool)
            and isinstance(entry["checked"], (int, float))
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return entry if valid else None


def _save(path: str, entry: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=COVER_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(entry, f)
    os.replace(tmp, path)


def cover_art(url: str, now: float | None = None) -> tuple[list[str], int | None]:
    """Pixel-art lines and accent colour for a cover, cached on disk per URL.

    Failures (offline, odd image) are cached too and retried after
    FAILURE_RETRY_S, so a bad cover never slows every refresh down.
    """
    if not is_allowed_artwork(url):
        return [], None
    now = time.time() if now is None else now
    ensure_private_dir(COVER_DIR)
    key = hashlib.sha1(f"{CACHE_VERSION}:{ART_PX}:{url}".encode()).hexdigest()
    path = os.path.join(COVER_DIR, key + ".json")
    entry = _load(path)
    if entry and not (entry["failed"] and now - entry["checked"] > FAILURE_RETRY_S):
        return entry["lines"], entry["accent"]
    try:
        lines, accent = _render_cover(url)
        failed = False
    except (OSError, ValueError, HTTPException, subprocess.SubprocessError) as exc:
        log.warning("cover art failed for %s: %s", url, exc)
        lines, accent, failed = [], None, True
    _save(path, {"lines": lines, "accent": accent, "failed": failed, "checked": now})
    return lines, accent
