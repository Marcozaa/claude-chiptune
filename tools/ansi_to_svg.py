#!/usr/bin/env python3
"""Turn claude-chiptune's ANSI output (stdin) into an SVG screenshot (stdout).

  python3 chiptune.py block | python3 tools/ansi_to_svg.py > docs/preview.svg

Understands exactly what the block emits: 256-colour fg/bg, bold, dim,
italic, reset, OSC 8 links (dropped) and the upper-half-block pixels.
"""
from __future__ import annotations

import html
import re
import sys

CELL_W, CELL_H, PAD = 9.6, 20, 16
FONT = "JetBrains Mono, Menlo, monospace"
BG, FG = "#1e1e2e", "#cdd6f4"  # Catppuccin Mocha base / text
TOKEN = re.compile(r"\033\[([0-9;]*)m|\033\]8;;[^\033]*\033\\|(.)", re.S)
BASE16 = ["#000000", "#cd0000", "#00cd00", "#cdcd00", "#0000ee", "#cd00cd", "#00cdcd", "#e5e5e5",
          "#7f7f7f", "#ff0000", "#00ff00", "#ffff00", "#5c5cff", "#ff00ff", "#00ffff", "#ffffff"]
CUBE = (0, 95, 135, 175, 215, 255)


def xterm(n: int) -> str:
    if n < 16:
        return BASE16[n]
    if n < 232:
        n -= 16
        return "#%02x%02x%02x" % (CUBE[n // 36], CUBE[n // 6 % 6], CUBE[n % 6])
    grey = 8 + (n - 232) * 10
    return "#%02x%02x%02x" % (grey, grey, grey)


def apply_sgr(params: str, style: dict) -> dict:
    codes = [int(c) for c in params.split(";") if c] or [0]
    style = dict(style)
    i = 0
    while i < len(codes):
        c = codes[i]
        if c == 0:
            style = {}
        elif c in (1, 2, 3):
            style[{1: "bold", 2: "dim", 3: "italic"}[c]] = True
        elif c in (38, 48) and i + 2 < len(codes) and codes[i + 1] == 5:
            style["fg" if c == 38 else "bg"] = xterm(codes[i + 2])
            i += 2
        i += 1
    return style


def cell_svg(x: float, y: float, ch: str, style: dict) -> str:
    if ch == "▀":
        half = CELL_H / 2
        return (f'<rect x="{x:.1f}" y="{y}" width="{CELL_W + 0.2:.1f}" height="{half + 0.2}" '
                f'fill="{style.get("fg", FG)}"/><rect x="{x:.1f}" y="{y + half}" '
                f'width="{CELL_W + 0.2:.1f}" height="{half + 0.2}" fill="{style.get("bg", BG)}"/>')
    if ch == " ":
        return ""
    attrs = [f'x="{x:.1f}"', f'y="{y + CELL_H * 0.75}"', f'fill="{style.get("fg", FG)}"']
    if style.get("bold"):
        attrs.append('font-weight="bold"')
    if style.get("dim"):
        attrs.append('opacity="0.6"')
    if style.get("italic"):
        attrs.append('font-style="italic"')
    return f'<text {" ".join(attrs)}>{html.escape(ch)}</text>'


def convert(ansi: str) -> str:
    parts, style, row, col, max_col = [], {}, 0, 0, 0
    for sgr, ch in ((m[1], m[2]) for m in TOKEN.finditer(ansi)):
        if sgr is not None:
            style = apply_sgr(sgr, style)
        elif ch == "\n":
            row, col = row + 1, 0
        elif ch:
            parts.append(cell_svg(PAD + col * CELL_W, PAD + row * CELL_H, ch, style))
            col += 1
            max_col = max(max_col, col)
    width, height = PAD * 2 + max_col * CELL_W, PAD * 2 + (row + 1) * CELL_H
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
            f'font-family="{FONT}" font-size="15">'
            f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>{"".join(parts)}</svg>\n')


if __name__ == "__main__":
    sys.stdout.write(convert(sys.stdin.read()))
