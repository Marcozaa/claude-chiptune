"""Lay out the now-playing block: pixel cover on the left, text on the right."""
from __future__ import annotations

import math

from .config import URL_SCHEME
from .cover import ART_PX
from .sanitize import truncate
from .spotify import NowPlaying

ART_WIDTH = ART_PX
LEFT_PAD = " "
GAP = "   "
BAR_CELLS = 18
EQ_BARS = 6
MAX_TEXT = 42
COMPACT_BAR_CELLS = 8

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
FALLBACK_ACCENT = 77  # Spotify-ish green
EQ_LEVELS = "▁▂▃▄▅▆▇█"


def fmt_time(ms: int) -> str:
    seconds = max(ms, 0) // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"


def progress_bar(position_ms: int, duration_ms: int, cells: int) -> str:
    ratio = min(max(position_ms / duration_ms, 0.0), 1.0) if duration_ms > 0 else 0.0
    filled = round(ratio * cells)
    return "▰" * filled + "▱" * (cells - filled)


def equalizer(now: float, playing: bool) -> str:
    if not playing:
        return EQ_LEVELS[0] * EQ_BARS
    tick, top = int(now), len(EQ_LEVELS) - 1
    return "".join(
        EQ_LEVELS[int((math.sin(tick * 1.7 + i * 2.3) + 1) / 2 * top)] for i in range(EQ_BARS)
    )


def hyperlink(url: str, text: str) -> str:
    """OSC 8 link: cmd+click in Ghostty / iTerm2; plain text elsewhere."""
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def _accent(accent: int | None) -> str:
    return f"\033[38;5;{FALLBACK_ACCENT if accent is None else accent}m"


def _controls(color: str) -> str:
    buttons = (("previous", "⏮"), ("playpause", "⏯"), ("next", "⏭"))
    return "  ".join(hyperlink(f"{URL_SCHEME}://{action}", f"{color}{icon}{RESET}")
                     for action, icon in buttons)


def _title(info: NowPlaying, color: str) -> str:
    icon = "▶" if info.playing else "⏸"
    title = f"{BOLD}{truncate(info.title, MAX_TEXT)}{RESET}"
    if info.track_id:
        title = hyperlink(info.track_id, title)
    return f"{color}{icon} {title}"


def full_block(info: NowPlaying, art: list[str], accent: int | None,
               lyric: str | None, now: float, controls: bool = True) -> str:
    color = _accent(accent)
    bottom = f"{color}{equalizer(now, info.playing)}{RESET}"
    if controls:
        bottom += f"   {_controls(color)}"
    text = [
        _title(info, color),
        f"  {truncate(info.artist, MAX_TEXT)}",
        f"  {DIM}{truncate(info.album, MAX_TEXT)}{RESET}",
        f"  {color}{DIM}{ITALIC}♪ {truncate(lyric, MAX_TEXT)}{RESET}" if lyric else "",
        f"  {color}{progress_bar(info.position_ms, info.duration_ms, BAR_CELLS)}{RESET} "
        f"{DIM}{fmt_time(info.position_ms)} / {fmt_time(info.duration_ms)}{RESET}",
        f"  {bottom}",
    ]
    blank = " " * ART_WIDTH
    rows = max(len(text), len(art))
    body = [
        f"{LEFT_PAD}{art[i] if i < len(art) else blank}{GAP}{text[i] if i < len(text) else ''}".rstrip()
        for i in range(rows)
    ]
    return "\n".join([LEFT_PAD] + body)


def compact_line(info: NowPlaying, accent: int | None) -> str:
    """One line for while Claude is working."""
    color = _accent(accent)
    icon = "▶" if info.playing else "⏸"
    return (f"{LEFT_PAD}{color}{icon}{RESET} {truncate(info.title, MAX_TEXT)} "
            f"{DIM}— {truncate(info.artist, MAX_TEXT // 2)}{RESET}  "
            f"{color}{progress_bar(info.position_ms, info.duration_ms, COMPACT_BAR_CELLS)}{RESET}")
