import json
import os
import tempfile
import unittest
from unittest import mock

import chiptune.lyrics as lyrics

LRC = """[ti:Cold]
[00:01.50]First line
[00:05.00][00:20.00]Chorus line
[00:10.25]
[00:12.00]Third line
"""


class ParseLrcTest(unittest.TestCase):
    def test_parses_and_sorts_timestamps(self):
        self.assertEqual(lyrics.parse_lrc(LRC), (
            (1500, "First line"), (5000, "Chorus line"), (10250, ""),
            (12000, "Third line"), (20000, "Chorus line"),
        ))

    def test_ignores_garbage(self):
        self.assertEqual(lyrics.parse_lrc("no tags here\n[xx:yy]nope"), ())

    def test_huge_timestamp_ignored(self):
        self.assertEqual(lyrics.parse_lrc("[0:" + "9" * 400 + "]boom"), ())

    def test_lyric_text_sanitized(self):
        ((_, text),) = lyrics.parse_lrc("[00:01.00]hi\x1b]0;pwned\x07 there")
        self.assertNotIn("\x1b", text)
        self.assertNotIn("\x07", text)


class CurrentLineTest(unittest.TestCase):
    LINES = ((1500, "First"), (5000, "Second"), (12000, "Third"))

    def test_before_first_line(self):
        self.assertIsNone(lyrics.current_line(self.LINES, 1000))

    def test_picks_latest_started_line(self):
        self.assertEqual(lyrics.current_line(self.LINES, 5000), "Second")
        self.assertEqual(lyrics.current_line(self.LINES, 11999), "Second")
        self.assertEqual(lyrics.current_line(self.LINES, 99999), "Third")

    def test_empty(self):
        self.assertIsNone(lyrics.current_line((), 5000))


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(lyrics, "LYRICS_DIR", self.tmp.name)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def _write(self, key, entry):
        with open(os.path.join(self.tmp.name, key + ".json"), "w") as f:
            json.dump(entry, f)

    def test_ready_entry(self):
        self._write("k", {"lines": [[1000, "Hello"]], "checked": 0, "error": False})
        state, lines = lyrics.load_cached("k", now=10)
        self.assertEqual(state, "ready")
        self.assertEqual(lines, ((1000, "Hello"),))

    def test_missing_is_permanent(self):
        self._write("k", {"lines": [], "checked": 0, "error": False})
        self.assertEqual(lyrics.load_cached("k", now=10**9)[0], "missing")

    def test_error_retries_later(self):
        self._write("k", {"lines": [], "checked": 0, "error": True})
        self.assertEqual(lyrics.load_cached("k", now=10)[0], "missing")
        self.assertEqual(lyrics.load_cached("k", now=lyrics.RETRY_AFTER_S + 1)[0], "absent")

    def test_absent(self):
        self.assertEqual(lyrics.load_cached("nope", now=0)[0], "absent")

    def test_cached_text_sanitized(self):
        self._write("k", {"lines": [[1000, "a\x1b[2Jb"]], "checked": 0, "error": False})
        _, lines = lyrics.load_cached("k", now=10)
        self.assertNotIn("\x1b", lines[0][1])

    def test_fetch_failure_is_cached_as_error(self):
        for exc in (ValueError("bad"), AttributeError("x"), OverflowError("inf")):
            with mock.patch.object(lyrics.urllib.request, "urlopen", side_effect=exc):
                lyrics.fetch("k", "t", "a", "al", 100)
            with open(os.path.join(self.tmp.name, "k.json")) as f:
                self.assertTrue(json.load(f)["error"])

    def test_fetch_non_dict_body(self):
        resp = mock.MagicMock()
        resp.__enter__.return_value.read.return_value = b"[1, 2]"
        with mock.patch.object(lyrics.urllib.request, "urlopen", return_value=resp):
            lyrics.fetch("k", "t", "a", "al", 100)
        self.assertEqual(lyrics.load_cached("k", now=0)[0], "missing")

    def test_fetch_success(self):
        resp = mock.MagicMock()
        resp.__enter__.return_value.read.return_value = json.dumps(
            {"syncedLyrics": "[00:02.00]Hello"}).encode()
        with mock.patch.object(lyrics.urllib.request, "urlopen", return_value=resp):
            lyrics.fetch("k", "t", "a", "al", 100)
        self.assertEqual(lyrics.load_cached("k", now=0), ("ready", ((2000, "Hello"),)))

    def test_no_lookup_without_metadata(self):
        with mock.patch.object(lyrics, "_start_background_fetch") as start:
            self.assertIsNone(lyrics.lyric_for("", "Artist", "Album", 1000, 0, now=0))
            self.assertIsNone(lyrics.lyric_for("Song", "Artist", "Album", 0, 0, now=0))
            start.assert_not_called()

    def test_pending_prevents_duplicate_spawn(self):
        with mock.patch.object(lyrics.subprocess, "Popen") as popen:
            lyrics._start_background_fetch("k", "t", "a", "al", 100, now=0)
            lyrics._start_background_fetch("k", "t", "a", "al", 100, now=0)
            self.assertEqual(popen.call_count, 1)

    def test_corrupt_cache_is_absent(self):
        with open(os.path.join(self.tmp.name, "bad.json"), "w") as f:
            f.write("{not json")
        self.assertEqual(lyrics.load_cached("bad", now=0)[0], "absent")


if __name__ == "__main__":
    unittest.main()
