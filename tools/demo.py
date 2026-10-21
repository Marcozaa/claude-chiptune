#!/usr/bin/env python3
"""Print a demo block with a made-up track and a synthwave-sunset cover.

  python3 tools/demo.py | python3 tools/ansi_to_svg.py > docs/preview.svg

Used for the README so it shows no real (copyrighted) cover art or lyrics.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chiptune.cover import ART_PX, accent_color, render_art  # noqa: E402
from chiptune.render import full_block  # noqa: E402
from chiptune.spotify import NowPlaying  # noqa: E402

SKY_TOP, SKY_BOTTOM = (10, 0, 40), (120, 20, 120)
SUN_TOP, SUN_BOTTOM = (255, 230, 90), (255, 70, 130)
GRID, FLOOR = (220, 0, 255), (30, 0, 60)


def _mix(a: tuple, b: tuple, t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def sunset(size: int) -> list[list[tuple[int, int, int]]]:
    """Gradient sky, a half sun with a stripe sitting on the horizon, neon grid floor."""
    horizon, cx, radius = size * 2 // 3, (size - 1) / 2, size * 0.36
    pixels = []
    for y in range(size):
        row = []
        for x in range(size):
            if y >= horizon:
                row.append(GRID if y == horizon or (x - cx + 0.5) % 4 == 0 else FLOOR)
            elif (x - cx) ** 2 + (y - horizon + 0.5) ** 2 <= radius ** 2 and y != horizon - 2:
                row.append(_mix(SUN_TOP, SUN_BOTTOM, (y - (horizon - radius)) / radius))
            else:
                row.append(_mix(SKY_TOP, SKY_BOTTOM, y / horizon))
        pixels.append(row)
    return pixels


def main() -> int:
    info = NowPlaying(True, "Neon Overdrive", "The Bit Crushers", "Sixteen Colours (1989)",
                      132_000, 214_000, "", "")
    pixels = sunset(ART_PX)
    lyric = "We ride the grid until the morning light"
    sys.stdout.write(full_block(info, render_art(pixels), accent_color(pixels), lyric,
                                now=7, controls=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
