import colorsys
import os
import tempfile
import unittest

from helpers import write_bmp

import chiptune.cover as cover


class ReadBmpTest(unittest.TestCase):
    PIXELS = [[(255, 0, 0), (0, 255, 0), (0, 0, 255)],
              [(10, 20, 30), (40, 50, 60), (70, 80, 90)]]

    def _roundtrip(self, top_down: bool) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.bmp")
            write_bmp(path, self.PIXELS, top_down=top_down)
            self.assertEqual(cover.read_bmp(path), self.PIXELS)

    def test_top_down(self):
        self._roundtrip(top_down=True)

    def test_bottom_up_with_row_padding(self):
        self._roundtrip(top_down=False)

    def test_rejects_non_bmp(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.bmp")
            with open(path, "wb") as f:
                f.write(b"not an image at all, definitely not, nope, no way")
            with self.assertRaises(ValueError):
                cover.read_bmp(path)


class ColorTest(unittest.TestCase):
    def test_cube_corners(self):
        self.assertEqual(cover.to_cube((0, 0, 0)), 16)
        self.assertEqual(cover.to_cube((255, 255, 255)), 231)
        self.assertEqual(cover.to_cube((255, 0, 0)), 196)

    def test_boost_keeps_grey(self):
        r, g, b = cover.boost((128, 128, 128))
        self.assertTrue(r == g == b)

    def test_boost_increases_saturation(self):
        sat = lambda rgb: colorsys.rgb_to_hsv(*(c / 255 for c in rgb))[1]
        self.assertGreater(sat(cover.boost((180, 120, 120))), sat((180, 120, 120)))

    def test_accent_picks_vivid_pixel(self):
        pixels = [[(200, 200, 200), (30, 30, 30)], [(220, 30, 30), (90, 90, 90)]]
        self.assertEqual(cover.accent_color(pixels), cover.to_cube((220, 30, 30)))

    def test_accent_none_for_greyscale(self):
        pixels = [[(200, 200, 200), (30, 30, 30)], [(120, 120, 120), (90, 90, 90)]]
        self.assertIsNone(cover.accent_color(pixels))


class RenderArtTest(unittest.TestCase):
    def test_two_pixel_rows_per_line(self):
        pixels = [[(255, 0, 0)] * 2, [(0, 0, 255)] * 2,
                  [(0, 0, 0)] * 2, [(255, 255, 255)] * 2]
        lines = cover.render_art(pixels)
        self.assertEqual(len(lines), 2)
        self.assertIn("\033[38;5;196m\033[48;5;21m▀", lines[0])
        self.assertTrue(lines[0].endswith("\033[0m"))


class ArtworkUrlTest(unittest.TestCase):
    def test_only_spotify_cdn_allowed(self):
        self.assertTrue(cover.is_allowed_artwork("https://i.scdn.co/image/abc123"))
        self.assertFalse(cover.is_allowed_artwork("http://i.scdn.co/image/abc"))
        self.assertFalse(cover.is_allowed_artwork("https://evil.example/i.scdn.co/"))
        self.assertFalse(cover.is_allowed_artwork("https://i.scdn.co/image/../x"))
        self.assertFalse(cover.is_allowed_artwork(""))


if __name__ == "__main__":
    unittest.main()
