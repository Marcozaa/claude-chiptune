"""Click-to-control: a tiny AppleScript app that handles claude-chiptune:// links.

Built locally with macOS's own osacompile (no third-party code) and accepts
exactly three actions — previous, playpause, next — anything else is ignored.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

from .config import CONTROLS_APP, URL_SCHEME

BUNDLE_ID = "com.claude-chiptune.controls"
LSREGISTER = ("/System/Library/Frameworks/CoreServices.framework/Frameworks/"
              "LaunchServices.framework/Support/lsregister")

HANDLER_SOURCE = f"""
on open location theURL
  set prefix to "{URL_SCHEME}://"
  if theURL does not start with prefix then return
  if (length of theURL) is (length of prefix) then return
  set action to text ((length of prefix) + 1) thru -1 of theURL
  if action ends with "/" then set action to text 1 thru -2 of action
  if application "Spotify" is not running then return
  if action is "playpause" then
    tell application "Spotify" to playpause
  else if action is "next" then
    tell application "Spotify" to next track
  else if action is "previous" then
    tell application "Spotify" to previous track
  end if
end open location
"""


def _run(*cmd: str) -> None:
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def install() -> str:
    """(Re)build and register the handler app. Returns its path."""
    os.makedirs(os.path.dirname(CONTROLS_APP), exist_ok=True)
    if os.path.isdir(CONTROLS_APP):
        shutil.rmtree(CONTROLS_APP)
    with tempfile.NamedTemporaryFile("w", suffix=".applescript", delete=False) as src:
        src.write(HANDLER_SOURCE)
    try:
        _run("osacompile", "-o", CONTROLS_APP, src.name)
    finally:
        os.remove(src.name)
    plist = os.path.join(CONTROLS_APP, "Contents", "Info.plist")
    url_types = [{"CFBundleURLName": "Claude Chiptune controls", "CFBundleURLSchemes": [URL_SCHEME]}]
    _run("plutil", "-replace", "CFBundleIdentifier", "-string", BUNDLE_ID, plist)
    _run("plutil", "-replace", "LSUIElement", "-bool", "YES", plist)
    _run("plutil", "-replace", "CFBundleURLTypes", "-json", json.dumps(url_types), plist)
    _run("codesign", "--force", "--sign", "-", CONTROLS_APP)
    _run(LSREGISTER, "-f", CONTROLS_APP)
    return CONTROLS_APP
