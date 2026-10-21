#!/usr/bin/env python3
"""claude-chiptune command line.

  chiptune.py statusline           a complete status line (Claude's JSON on stdin)
  chiptune.py block [SESSION_ID]   only the now-playing block, to add to your own
  chiptune.py hook busy|idle       mark the session from a hook (JSON on stdin)
  chiptune.py install-controls     build the click-to-control handler app
  chiptune.py sync DATA_DIR        (plugin) copy the app into DATA_DIR/app if outdated
"""
import json
import logging
import logging.handlers
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chiptune.config import CACHE_DIR, LOG_FILE, ensure_private_dir  # noqa: E402

USAGE = __doc__
LOG_MAX_BYTES = 100_000


def setup_logging() -> None:
    """Warnings go to a small rotating file; the status line discards stderr."""
    try:
        ensure_private_dir(CACHE_DIR)
        handler = logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=1)
    except OSError:
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.WARNING, handlers=[handler])


def run_block(session_id: str) -> int:
    from chiptune.block import build
    try:
        sys.stdout.write(build(session_id))
    except Exception:  # noqa: BLE001 — never put a traceback in the status line
        logging.getLogger("chiptune").exception("building the block failed")
    return 0


def run_statusline() -> int:
    """Read Claude Code's status line JSON, print a header line plus the block."""
    from chiptune.block import build, statusline_header
    try:
        data = json.load(sys.stdin)
        data = data if isinstance(data, dict) else {}
        header = statusline_header(data)
        block = build(str(data.get("session_id", "")))
        sys.stdout.write("\n".join(part for part in (header, block) if part))
    except Exception:  # noqa: BLE001 — never put a traceback in the status line
        logging.getLogger("chiptune").exception("status line failed")
    return 0


def run_install_controls() -> int:
    from chiptune.controls import install
    try:
        print(f"Installed {install()}")
    except subprocess.CalledProcessError as exc:
        print(f"Install failed running {' '.join(exc.cmd)}:\n{exc.stderr}", file=sys.stderr)
        return 1
    return 0


def run_sync(data_dir: str) -> int:
    """SessionStart hook for the plugin; must never block a session from starting."""
    from chiptune.install import sync_app
    try:
        sync_app(os.path.dirname(os.path.abspath(__file__)), data_dir)
    except (OSError, ValueError) as exc:
        logging.getLogger("chiptune").warning("sync failed: %s", exc)
    return 0


def main(argv: list) -> int:
    setup_logging()
    command = argv[1] if len(argv) > 1 else ""
    if command == "statusline":
        return run_statusline()
    if command == "block":
        return run_block(argv[2] if len(argv) > 2 else "")
    if command == "hook" and len(argv) > 2 and argv[2] in ("busy", "idle"):
        from chiptune.activity import hook_main
        return hook_main(argv[2])
    if command == "install-controls":
        return run_install_controls()
    if command == "sync" and len(argv) > 2:
        return run_sync(argv[2])
    sys.stderr.write(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
