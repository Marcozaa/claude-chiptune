"""Is Claude busy in this session? Set by hooks, read by the status line.

Hooks: UserPromptSubmit -> `busy`, Stop / SessionEnd -> `idle`
(each reads the hook JSON on stdin for session_id).
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time

from .config import CACHE_DIR, ensure_private_dir

log = logging.getLogger(__name__)

BUSY_DIR = os.path.join(CACHE_DIR, "busy")
STALE_AFTER_S = 1800  # a flag this old (e.g. after an interrupt) is ignored
SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")


def valid_session_id(session_id: str) -> bool:
    return SESSION_ID.fullmatch(session_id) is not None


def mark(session_id: str, busy: bool) -> None:
    if not valid_session_id(session_id):
        raise ValueError(f"invalid session id: {session_id!r}")
    flag = os.path.join(BUSY_DIR, session_id)
    if busy:
        ensure_private_dir(BUSY_DIR)
        _prune_stale(time.time())
        open(flag, "w").close()
    else:
        try:
            os.remove(flag)
        except FileNotFoundError:
            pass


def _prune_stale(now: float) -> None:
    """Drop flags left behind by interrupted or crashed sessions."""
    for name in os.listdir(BUSY_DIR):
        path = os.path.join(BUSY_DIR, name)
        try:
            if now - os.path.getmtime(path) >= STALE_AFTER_S:
                os.remove(path)
        except FileNotFoundError:
            pass


def is_busy(session_id: str, now: float | None = None) -> bool:
    if not valid_session_id(session_id):
        return False
    try:
        mtime = os.path.getmtime(os.path.join(BUSY_DIR, session_id))
        age = (time.time() if now is None else now) - mtime
    except FileNotFoundError:
        return False
    return age < STALE_AFTER_S


def hook_main(state: str) -> int:
    """Entry point for hooks; never blocks Claude, even on bad input."""
    try:
        session_id = str(json.load(sys.stdin).get("session_id", ""))
        mark(session_id, busy=(state == "busy"))
    except (OSError, ValueError, AttributeError) as exc:
        log.warning("activity hook failed: %s", exc)
    return 0
