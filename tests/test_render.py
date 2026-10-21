import re
import unittest

from helpers import raw_track

import chiptune.render as render
from chiptune.spotify import parse_now_playing

ANSI = re.compile(r"\033\[[0-9;]*m|\033\]8;;[^\033]*\033\\")


def plain(text: str) -> str:
    return ANSI.sub("", text)


class TextHelpersTest(unittest.TestCase):
    def test_fmt_time(self):
        self.assertEqual(render.fmt_time(0), "0:00")
        self.assertEqual(render.fmt_time(113624), "1:53")
        self.assertEqual(render.fmt_time(3_725_000), "62:05")

    def test_progress_bar_bounds(self):
        self.assertEqual(render.progress_bar(0, 1000, 4), "▱▱▱▱")
        self.assertEqual(render.progress_bar(500, 1000, 4), "▰▰▱▱")
        self.assertEqual(render.progress_bar(5000, 1000, 4), "▰▰▰▰")
        self.assertEqual(render.progress_bar(10, 0, 4), "▱▱▱▱")
        self.assertEqual(render.progress_bar(-500, 1000, 4), "▱▱▱▱")

    def test_truncate(self):
        self.assertEqual(render.truncate("short", 10), "short")
        self.assertEqual(render.truncate("abcdefghijk", 6), "abcde…")

    def test_equalizer(self):
        self.assertEqual(render.equalizer(123, playing=False), "▁" * render.EQ_BARS)
        self.assertEqual(len(render.equalizer(123, playing=True)), render.EQ_BARS)

    def test_hyperlink(self):
        self.assertEqual(render.hyperlink("x://y", "go"), "\033]8;;x://y\033\\go\033]8;;\033\\")


class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.info = parse_now_playing(raw_track(state="paused", pos="1000", dur="2000"))

    def test_full_block_layout(self):
        art = [f"ART{i}" for i in range(6)]
        lines = render.full_block(self.info, art, accent=None, lyric="La la", now=0).split("\n")
        self.assertEqual(lines[0], render.BLANK)  # top padding survives whitespace trimming
        self.assertNotEqual(render.BLANK.strip(), "")
        self.assertIn(render.NORMAL + "Maroon 5", lines[2])  # artist undoes any dimming
        body = [plain(l) for l in lines[1:]]
        self.assertEqual(len(body), 6)
        self.assertTrue(body[0].startswith(render.LEFT_PAD + "ART0" + render.GAP))
        self.assertIn("⏸ Cold", body[0])
        self.assertIn("Maroon 5", body[1])
        self.assertIn("Red Pill Blues", body[2])
        self.assertIn("La la", body[3])
        self.assertIn("0:01 / 0:02", body[4])

    def test_no_art_keeps_alignment(self):
        lines = render.full_block(self.info, [], accent=None, lyric=None, now=0).split("\n")
        body = [plain(l) for l in lines[1:]]
        self.assertEqual(len(body), 6)
        self.assertTrue(body[1].startswith(render.LEFT_PAD + " " * render.ART_WIDTH + render.GAP))

    def test_accent_colours_title(self):
        out = render.full_block(self.info, [], accent=196, lyric=None, now=0)
        self.assertIn("\033[38;5;196m", out.split("\n")[1])

    def test_title_links_to_spotify(self):
        out = render.full_block(self.info, [], accent=None, lyric=None, now=0)
        self.assertIn("\033]8;;spotify:track:4s6LhHAV5SEsOV0lC2tjvJ\033\\", out)

    def test_controls_optional(self):
        with_controls = render.full_block(self.info, [], None, None, 0, controls=True)
        without = render.full_block(self.info, [], None, None, 0, controls=False)
        self.assertIn("claude-chiptune://next", with_controls)
        self.assertNotIn("claude-chiptune://", without)

    def test_compact_line(self):
        out = render.compact_line(self.info, accent=None)
        self.assertNotIn("\n", out)
        self.assertIn("Cold", plain(out))
        self.assertIn("Maroon 5", plain(out))


if __name__ == "__main__":
    unittest.main()
