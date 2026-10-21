import json
import os
import tempfile
import unittest
from unittest import mock

import helpers  # noqa: F401  (puts the package on sys.path)
import chiptune.cover as cover

URL = "https://i.scdn.co/image/abc123"


class CoverCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(cover, "COVER_DIR", self.tmp.name)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def _cache_file(self):
        (name,) = os.listdir(self.tmp.name)
        return os.path.join(self.tmp.name, name)

    def test_failure_is_cached_and_not_retried_immediately(self):
        with mock.patch.object(cover, "download", side_effect=OSError("offline")) as dl:
            self.assertEqual(cover.cover_art(URL, now=1000), ([], None))
            self.assertEqual(cover.cover_art(URL, now=1010), ([], None))
            self.assertEqual(dl.call_count, 1)
            cover.cover_art(URL, now=1000 + cover.FAILURE_RETRY_S + 1)
            self.assertEqual(dl.call_count, 2)

    def test_corrupt_cache_is_regenerated(self):
        with mock.patch.object(cover, "download", side_effect=OSError("offline")):
            cover.cover_art(URL, now=0)
        with open(self._cache_file(), "w") as f:
            f.write("{truncated")
        with mock.patch.object(cover, "download", side_effect=OSError("offline")) as dl:
            cover.cover_art(URL, now=0)
            self.assertEqual(dl.call_count, 1)

    def test_tampered_cache_lines_rejected(self):
        with mock.patch.object(cover, "download", side_effect=OSError("offline")):
            cover.cover_art(URL, now=0)
        with open(self._cache_file(), "w") as f:
            json.dump({"lines": ["\x1b]52;c;evil\x07"], "accent": 1, "failed": False, "checked": 0}, f)
        with mock.patch.object(cover, "download", side_effect=OSError("offline")):
            self.assertEqual(cover.cover_art(URL, now=0), ([], None))


if __name__ == "__main__":
    unittest.main()
