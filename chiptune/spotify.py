"""Read what Spotify is playing via AppleScript (macOS)."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

from .sanitize import clean

OSASCRIPT_TIMEOUT_S = 2
FIELD_SEP = "\x1f"  # ASCII unit separator: never appears in real titles, unlike tab
TRACK_URI = re.compile(r"spotify:track:[A-Za-z0-9]+")

NOW_PLAYING_SCRIPT = """
tell application "Spotify"
  if player state is stopped then return ""
  set t to current track
  set sep to character id 31
  return (player state as string) & sep & (name of t) & sep & (artist of t) & sep & ¬
    (album of t) & sep & ((player position * 1000) as integer) & sep & ¬
    (duration of t) & sep & (artwork url of t) & sep & (id of t)
end tell
"""


@dataclass(frozen=True)
class NowPlaying:
    playing: bool
    title: str
    artist: str
    album: str
    position_ms: int
    duration_ms: int
    artwork_url: str
    track_id: str  # "spotify:track:…", or "" if Spotify returned something odd


def parse_now_playing(raw: str) -> NowPlaying | None:
    fields = raw.rstrip("\n").split(FIELD_SEP)
    if len(fields) != 8:
        return None
    state, title, artist, album, pos, dur, url, track_id = fields
    try:
        position_ms, duration_ms = int(pos), int(dur)
    except ValueError:
        return None
    track_id = track_id if TRACK_URI.fullmatch(track_id) else ""
    return NowPlaying(state == "playing", clean(title), clean(artist), clean(album),
                      position_ms, duration_ms, url, track_id)


def spotify_running() -> bool:
    return subprocess.run(["pgrep", "-xq", "Spotify"], check=False).returncode == 0


def fetch_now_playing() -> NowPlaying | None:
    """Ask Spotify what's playing. Never launches Spotify (checked first)."""
    if not spotify_running():
        return None
    try:
        result = subprocess.run(
            ["osascript", "-e", NOW_PLAYING_SCRIPT], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=OSASCRIPT_TIMEOUT_S, check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    return parse_now_playing(result.stdout)
