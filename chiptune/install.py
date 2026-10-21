"""Keep a stable copy of chiptune in the plugin's data folder.

The plugin's own folder changes path on every update, so the status line
setting points at ${CLAUDE_PLUGIN_DATA}/app instead. A SessionStart hook
calls sync_app(), which refreshes that copy whenever the version changes.
"""
from __future__ import annotations

import os
import shutil
import tempfile

from . import __version__

APP_DIRNAME = "app"
VERSION_FILE = "VERSION"
COPIED = ("chiptune.py", "chiptune")


def _installed_version(app: str) -> str:
    try:
        with open(os.path.join(app, VERSION_FILE), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def sync_app(plugin_root: str, data_dir: str) -> str:
    """Copy the runnable files into data_dir/app if missing or outdated; return that path."""
    if not data_dir or not os.path.isabs(data_dir) or "${" in data_dir:
        raise ValueError(f"plugin data dir must be an absolute path, got {data_dir!r}")
    app = os.path.join(data_dir, APP_DIRNAME)
    if _installed_version(app) == __version__:
        return app
    os.makedirs(data_dir, exist_ok=True)
    staging = tempfile.mkdtemp(dir=data_dir, prefix=".app-")
    try:
        for name in COPIED:
            src, dst = os.path.join(plugin_root, name), os.path.join(staging, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(src, dst)
        with open(os.path.join(staging, VERSION_FILE), "w", encoding="utf-8") as f:
            f.write(__version__)
        if os.path.isdir(app):
            shutil.rmtree(app)
        os.replace(staging, app)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return app
