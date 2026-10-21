#!/bin/sh
# claude-chiptune installer: checks requirements, builds the click-to-control
# helper app, and prints the settings to add to ~/.claude/settings.json.
set -eu

DIR=$(cd "$(dirname "$0")" && pwd)

if [ "$(uname)" != "Darwin" ]; then
  echo "claude-chiptune needs macOS (it talks to the Spotify app via AppleScript)." >&2
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
  echo "claude-chiptune needs Python 3.9 or newer as python3." >&2
  exit 1
fi

python3 -I "$DIR/chiptune.py" install-controls

cat <<SNIPPET

Done. Add this to ~/.claude/settings.json (or see the README to add the block
to an existing status line):

  "statusLine": {
    "type": "command",
    "command": "python3 -I $DIR/chiptune.py statusline",
    "refreshInterval": 2
  },
  "hooks": {
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python3 -I $DIR/chiptune.py hook busy" }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "python3 -I $DIR/chiptune.py hook idle" }] }],
    "SessionEnd":       [{ "hooks": [{ "type": "command", "command": "python3 -I $DIR/chiptune.py hook idle" }] }]
  }

Then restart Claude Code and play something on Spotify.
SNIPPET
