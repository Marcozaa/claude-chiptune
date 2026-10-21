import os
import tempfile
import unittest

import helpers  # noqa: F401  (puts the package on sys.path)
import chiptune
from chiptune.install import APP_DIRNAME, sync_app

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SyncAppTest(unittest.TestCase):
    def test_copies_runnable_app(self):
        with tempfile.TemporaryDirectory() as data:
            app = sync_app(REPO, data)
            self.assertEqual(app, os.path.join(data, APP_DIRNAME))
            self.assertTrue(os.path.isfile(os.path.join(app, "chiptune.py")))
            self.assertTrue(os.path.isfile(os.path.join(app, "chiptune", "render.py")))
            self.assertFalse(os.path.exists(os.path.join(app, "tests")))

    def test_skips_when_version_matches_and_replaces_when_not(self):
        with tempfile.TemporaryDirectory() as data:
            app = sync_app(REPO, data)
            marker = os.path.join(app, "chiptune", "marker")
            open(marker, "w").close()
            sync_app(REPO, data)
            self.assertTrue(os.path.exists(marker))  # same version: left alone
            with open(os.path.join(app, "VERSION"), "w") as f:
                f.write("0.0.0")
            sync_app(REPO, data)
            self.assertFalse(os.path.exists(marker))  # different version: replaced
            with open(os.path.join(app, "VERSION")) as f:
                self.assertEqual(f.read(), chiptune.__version__)

    def test_rejects_relative_or_unsubstituted_paths(self):
        for bad in ("relative/dir", "${CLAUDE_PLUGIN_DATA}", ""):
            with self.assertRaises(ValueError):
                sync_app(REPO, bad)


if __name__ == "__main__":
    unittest.main()
