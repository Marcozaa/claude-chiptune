import unittest

from helpers import raw_track

import chiptune.spotify as spotify


class ParseNowPlayingTest(unittest.TestCase):
    def test_parses_fields(self):
        info = spotify.parse_now_playing(raw_track())
        self.assertEqual(info.title, "Cold")
        self.assertTrue(info.playing)
        self.assertEqual(info.position_ms, 113624)
        self.assertEqual(info.track_id, "spotify:track:4s6LhHAV5SEsOV0lC2tjvJ")

    def test_paused(self):
        self.assertFalse(spotify.parse_now_playing(raw_track(state="paused")).playing)

    def test_rejects_garbage(self):
        self.assertIsNone(spotify.parse_now_playing(""))
        self.assertIsNone(spotify.parse_now_playing("playing\x1fonly\x1fthree"))
        self.assertIsNone(spotify.parse_now_playing(raw_track(pos="NaN")))

    def test_title_with_tab_still_parses(self):
        self.assertEqual(spotify.parse_now_playing(raw_track(title="A\tB")).title, "A B")

    def test_escape_sequences_stripped(self):
        info = spotify.parse_now_playing(raw_track(
            title="Hi\x1b]52;c;Y3VybCB4fHNo\x07", artist="\x1b[2JEvil", album="X\u202eY"))
        for text in (info.title, info.artist, info.album):
            self.assertNotIn("\x1b", text)
            self.assertNotIn("\x07", text)
            self.assertNotIn("\u202e", text)

    def test_track_uri_validated(self):
        self.assertEqual(spotify.parse_now_playing(raw_track(id="javascript:x")).track_id, "")


if __name__ == "__main__":
    unittest.main()
