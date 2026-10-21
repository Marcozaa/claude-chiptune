import unittest

import helpers  # noqa: F401  (puts the package on sys.path)
from chiptune.block import statusline_header


class HeaderTest(unittest.TestCase):
    def test_model_and_folder(self):
        data = {"model": {"display_name": "Opus"}, "workspace": {"current_dir": "/home/me/project"}}
        self.assertIn("Opus", statusline_header(data))
        self.assertIn("project", statusline_header(data))

    def test_missing_fields(self):
        self.assertEqual(statusline_header({}), "")
        self.assertEqual(statusline_header({"model": "not a dict"}), "")

    def test_sanitized(self):
        data = {"model": {"display_name": "\x1b]52;c;x\x07Opus"}}
        self.assertNotIn("\x1b]", statusline_header(data))


if __name__ == "__main__":
    unittest.main()
