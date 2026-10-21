---
name: setup
description: Set up the chiptune status line (Spotify pixel-art cover, lyrics, controls) in ~/.claude/settings.json.
disable-model-invocation: true
allowed-tools: Bash(python3:*), Read, Edit
---

# Set up chiptune

Set up the chiptune status line for the user. Explain each step briefly in plain language. Ask before changing anything the user already has.

1. **Check requirements.** Stop and explain if either of these fails:
   - The machine runs macOS: `uname` prints `Darwin`.
   - `python3 --version` is 3.9 or newer.

2. **Copy the app to its stable location.** Run:
   `python3 -I "${CLAUDE_PLUGIN_ROOT}/chiptune.py" sync "${CLAUDE_PLUGIN_DATA}"`
   The status line will run `${CLAUDE_PLUGIN_DATA}/app/chiptune.py`. That path stays the same across plugin updates, and a SessionStart hook keeps the copy current.

3. **Click-to-control buttons (optional).** Ask the user whether they want the ⏮ ⏯ ⏭ buttons. Explain what they would install:
   - A tiny AppleScript app at `~/Applications/Claude Chiptune Controls.app`, built locally with macOS's `osacompile`.
   - It only accepts previous, play/pause and next.

   If the user says yes, run:
   `python3 -I "${CLAUDE_PLUGIN_DATA}/app/chiptune.py" install-controls`

4. **Status line.** Read `~/.claude/settings.json`, then:
   - **No `statusLine` yet:** back up the file to `~/.claude/settings.json.bak-chiptune`, then add the following. Use the real absolute path of `${CLAUDE_PLUGIN_DATA}`, not the variable.
     ```json
     "statusLine": {
       "type": "command",
       "command": "python3 -I <CLAUDE_PLUGIN_DATA>/app/chiptune.py statusline",
       "refreshInterval": 2
     }
     ```
   - **A `statusLine` already exists:** do not replace it. Show the user these lines to add at the end of their status line script, which must have Claude's JSON in `$input`. Offer to add them yourself, and only do so if the user agrees.
     ```sh
     session_id=$(printf '%s' "$input" | jq -r '.session_id // ""')
     block=$(python3 -I <CLAUDE_PLUGIN_DATA>/app/chiptune.py block "$session_id" 2>/dev/null)
     [ -n "$block" ] && printf '\n%s' "$block"
     ```
     Also suggest setting `"refreshInterval": 2` on their `statusLine`.

5. **Finish.** Tell the user:
   - Restart Claude Code and play something on Spotify.
   - macOS will ask once whether the terminal may control Spotify. Click **Allow**.
   - Features can be turned off with the `CHIPTUNE_LYRICS=0`, `CHIPTUNE_CONTROLS=0` and `CHIPTUNE_COMPACT_WHILE_BUSY=0` environment variables in the `env` section of settings.
   - The hooks that shrink the block while Claude works are already active through the plugin.
