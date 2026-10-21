import unittest

import helpers  # noqa: F401  (puts the package on sys.path)
from chiptune.sanitize import cell_width, clean, truncate


class CleanTest(unittest.TestCase):
    def test_removes_control_and_format_chars(self):
        self.assertEqual(clean("a\x1b[31mb\x07c\x9bd‮e f"), "a [31mb c d e f")

    def test_collapses_whitespace_and_newlines(self):
        self.assertEqual(clean("  one\n\ttwo\r\n three  "), "one two three")

    def test_keeps_normal_unicode(self):
        self.assertEqual(clean("Beyoncé — 夜に駆ける ♪"), "Beyoncé — 夜に駆ける ♪")


class WidthTest(unittest.TestCase):
    def test_cell_width(self):
        self.assertEqual(cell_width("abc"), 3)
        self.assertEqual(cell_width("夜に"), 4)
        self.assertEqual(cell_width("é"), 1)  # combining accent

    def test_truncate_by_cells(self):
        self.assertEqual(truncate("short", 10), "short")
        self.assertEqual(truncate("abcdefghijk", 6), "abcde…")
        self.assertEqual(truncate("夜に駆ける", 6), "夜に…")
        self.assertLessEqual(cell_width(truncate("夜に駆ける夜に駆ける", 7)), 7)


if __name__ == "__main__":
    unittest.main()
