"""Build the status line block for the current Spotify track."""
from __future__ import annotations

import logging
import os
import time

from . import activity, lyrics, render
from .config import CONTROLS_APP, enabled
from .cover import cover_art
from .sanitize import clean
from .spotify import fetch_now_playing

log = logging.getLogger(__name__)

DIM, RESET = "\033[2m", "\033[0m"


def statusline_header(data: dict) -> str:
    """'model · folder' for people using chiptune as their whole status line."""
    model = data.get("model") if isinstance(data.get("model"), dict) else {}
    workspace = data.get("workspace") if isinstance(data.get("workspace"), dict) else {}
    parts = [clean(str(model.get("display_name", ""))),
             clean(os.path.basename(str(workspace.get("current_dir", "")).rstrip("/")))]
    parts = [p for p in parts if p]
    return f"{DIM}{' · '.join(parts)}{RESET}" if parts else ""


def build(session_id: str) -> str:
    """Status line text, or "" when nothing is playing."""
    info = fetch_now_playing()
    if info is None:
        return ""
    art, accent = cover_art(info.artwork_url)
    if enabled("COMPACT_WHILE_BUSY") and activity.is_busy(session_id):
        return render.compact_line(info, accent)
    now = time.time()
    lyric = None
    if enabled("LYRICS"):
        try:
            lyric = lyrics.lyric_for(info.title, info.artist, info.album,
                                     info.duration_ms, info.position_ms, now)
        except OSError as exc:
            log.warning("lyrics lookup failed: %s", exc)
    controls = enabled("CONTROLS") and os.path.isdir(CONTROLS_APP)
    return render.full_block(info, art, accent, lyric, now, controls=controls)
