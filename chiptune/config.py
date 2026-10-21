"""Paths and on/off switches (set via environment variables, default on)."""
from __future__ import annotations

import os

CACHE_DIR = os.path.expanduser("~/.cache/claude-chiptune")
LOG_FILE = os.path.join(CACHE_DIR, "chiptune.log")
URL_SCHEME = "claude-chiptune"
# Click-to-control handler app; the buttons are only drawn once it exists.
CONTROLS_APP = os.path.expanduser("~/Applications/Claude Chiptune Controls.app")
PRIVATE_DIR_MODE = 0o700  # listening history is nobody else's business


def enabled(name: str) -> bool:
    """CHIPTUNE_<NAME>=0 turns a feature off."""
    return os.environ.get(f"CHIPTUNE_{name}", "1") != "0"


def ensure_private_dir(path: str) -> None:
    """Create `path` (under CACHE_DIR) readable only by the current user."""
    for directory in (CACHE_DIR, path):
        os.makedirs(directory, mode=PRIVATE_DIR_MODE, exist_ok=True)
        os.chmod(directory, PRIVATE_DIR_MODE)  # also tighten dirs from older versions
