"""Synced lyrics from LRCLIB (https://lrclib.net), cached per track.

The status line never waits on the network: a missing entry starts a
detached background fetch and the lyric appears on a later refresh. Every
fetch outcome is cached (errors only briefly), so a bad response can't make
it retry on every refresh.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from . import __version__
from .config import CACHE_DIR, ensure_private_dir
from .sanitize import clean

log = logging.getLogger(__name__)

LRCLIB_URL = "https://lrclib.net/api/get"
USER_AGENT = f"claude-chiptune/{__version__}"
FETCH_TIMEOUT_S = 5
MAX_BODY_BYTES = 1_000_000
MAX_LINES = 2000
RETRY_AFTER_S = 120     # after a network error / LRCLIB overload (503)
PENDING_TIMEOUT_S = 30  # a fetch still "pending" after this is retried
LYRICS_DIR = os.path.join(CACHE_DIR, "lyrics")
TAG = re.compile(r"\[(\d{1,3}):(\d{1,2}(?:\.\d{1,3})?)\]")

Lines = tuple[tuple[int, str], ...]


def parse_lrc(text: str) -> Lines:
    """'[mm:ss.xx]lyric' lines -> ((ms, lyric), ...) sorted; a line may carry several tags."""
    entries = []
    for raw in text.splitlines()[:MAX_LINES]:
        stamps, rest = [], raw
        while (m := TAG.match(rest)):
            stamps.append(int(m[1]) * 60_000 + round(float(m[2]) * 1000))
            rest = rest[m.end():]
        entries.extend((ms, clean(rest)) for ms in stamps)
    return tuple(sorted(entries))


def current_line(lines: Lines, position_ms: int) -> str | None:
    i = bisect.bisect_right([ms for ms, _ in lines], position_ms)
    return lines[i - 1][1] if i else None


def track_key(title: str, artist: str) -> str:
    return hashlib.sha1(f"{artist}\0{title}".encode()).hexdigest()


def _path(key: str, suffix: str = ".json") -> str:
    return os.path.join(LYRICS_DIR, key + suffix)


def load_cached(key: str, now: float) -> tuple[str, Lines]:
    """('ready', lines) | ('missing', ()) | ('absent', ()) — absent means fetch it."""
    try:
        with open(_path(key), encoding="utf-8") as f:
            entry = json.load(f)
        lines = tuple((int(ms), clean(str(text))) for ms, text in entry["lines"])
        error, checked = bool(entry["error"]), float(entry["checked"])
    except (OSError, ValueError, KeyError, TypeError):
        return "absent", ()
    if lines:
        return "ready", lines
    if error and now - checked > RETRY_AFTER_S:
        return "absent", ()
    return "missing", ()


def _save(key: str, lines: Lines, error: bool) -> None:
    ensure_private_dir(LYRICS_DIR)
    fd, tmp = tempfile.mkstemp(dir=LYRICS_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"lines": lines, "checked": time.time(), "error": error}, f)
    os.replace(tmp, _path(key))


def _request(title: str, artist: str, album: str, duration_s: int) -> Lines:
    query = urllib.parse.urlencode({
        "track_name": title, "artist_name": artist,
        "album_name": album, "duration": duration_s,
    })
    request = urllib.request.Request(f"{LRCLIB_URL}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_S) as resp:
        raw = resp.read(MAX_BODY_BYTES + 1)
    if len(raw) > MAX_BODY_BYTES:
        raise ValueError("lyrics response too large")
    body = json.loads(raw)
    synced = body.get("syncedLyrics") if isinstance(body, dict) else None
    return parse_lrc(synced) if isinstance(synced, str) else ()


def fetch(key: str, title: str, artist: str, album: str, duration_s: int) -> None:
    """Look the track up and cache the outcome, whatever happens."""
    try:
        _save(key, _request(title, artist, album, duration_s), error=False)
    except urllib.error.HTTPError as exc:
        _save(key, (), error=exc.code != 404)  # 404: LRCLIB has no lyrics for it
    except Exception as exc:  # noqa: BLE001 — any failure must still be cached
        log.warning("lyrics fetch failed for %s — %s: %s", artist, title, exc)
        _save(key, (), error=True)
    finally:
        try:
            os.remove(_path(key, ".pending"))
        except FileNotFoundError:
            pass


def _claim_pending(key: str, now: float) -> bool:
    """Atomically mark a fetch as started; False if one is already running."""
    ensure_private_dir(LYRICS_DIR)
    pending = _path(key, ".pending")
    try:
        if now - os.path.getmtime(pending) >= PENDING_TIMEOUT_S:
            os.remove(pending)
    except FileNotFoundError:
        pass
    try:
        os.close(os.open(pending, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    except FileExistsError:
        return False
    return True


def _start_background_fetch(key: str, title: str, artist: str, album: str,
                            duration_s: int, now: float) -> None:
    if not _claim_pending(key, now):
        return
    package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        subprocess.Popen(
            [sys.executable, "-I", "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); from chiptune.lyrics import fetch; "
             "fetch(*sys.argv[2:6], int(sys.argv[6]))",
             package_root, key, title, artist, album, str(duration_s)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        os.remove(_path(key, ".pending"))
        raise


def lyric_for(title: str, artist: str, album: str, duration_ms: int,
              position_ms: int, now: float) -> str | None:
    if not title or not artist or duration_ms <= 0:  # ads, podcasts, local files
        return None
    key = track_key(title, artist)
    state, lines = load_cached(key, now)
    if state == "absent":
        _start_background_fetch(key, title, artist, album, duration_ms // 1000, now)
    return current_line(lines, position_ms) if state == "ready" else None
