import tempfile
import unittest
from unittest import mock

import helpers  # noqa: F401  (puts the package on sys.path)
import chiptune.activity as activity


class ActivityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(activity, "BUSY_DIR", self.tmp.name)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_busy_then_idle(self):
        activity.mark("abc-123", busy=True)
        self.assertTrue(activity.is_busy("abc-123"))
        activity.mark("abc-123", busy=False)
        self.assertFalse(activity.is_busy("abc-123"))

    def test_idle_when_never_marked(self):
        self.assertFalse(activity.is_busy("abc-123"))
        activity.mark("abc-123", busy=False)  # removing a missing flag is fine

    def test_stale_flag_ignored(self):
        activity.mark("abc", busy=True)
        self.assertFalse(activity.is_busy("abc", now=10**12))

    def test_marking_busy_prunes_stale_flags(self):
        import os
        activity.mark("old", busy=True)
        os.utime(os.path.join(self.tmp.name, "old"), (0, 0))
        activity.mark("new", busy=True)
        self.assertEqual(sorted(os.listdir(self.tmp.name)), ["new"])

    def test_rejects_path_traversal(self):
        self.assertFalse(activity.valid_session_id("../../etc/passwd"))
        self.assertFalse(activity.valid_session_id(""))
        self.assertTrue(activity.valid_session_id("1f0e7c2a-9b1d-4c3e-8f00-0123456789ab"))
        with self.assertRaises(ValueError):
            activity.mark("../x", busy=True)
        self.assertFalse(activity.is_busy("../x"))


if __name__ == "__main__":
    unittest.main()
